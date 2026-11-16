"""Opt-in fresh-install/model-overlap/restart acceptance. All accounts are disposable."""

import argparse
import base64
import hashlib
import json
import platform
import secrets
import socket
import subprocess
import sys
import threading
import time
from contextlib import closing
from pathlib import Path

from semaphore_core.embeddings import OllamaConfig, OllamaEmbedder, PinnedEmbedder, fingerprint_hash
from semaphore_core.verification import parse_manifest, verify_pack
from semaphore_hub.durable_host import DurableHost
from semaphore_hub.operations import ExternalLedger
from semaphore_hub.policy import TransportPolicy
from semaphore_hub.storage import connect

from .http_load import Client, run


def append(path, value):
    with Path(path).open("a", encoding="utf8") as stream:
        stream.write(json.dumps(value) + "\n")
        stream.flush()


class ObservedEmbedder:
    def __init__(self, inner, path, role):
        self.inner, self.path, self.role = inner, path, role

    def identity(self):
        return self.inner.identity()

    def measure(self, method, texts):
        started = time.time_ns()
        success = False
        append(
            self.path,
            {
                "event": "start",
                "role": self.role,
                "phase": method,
                "started_ns": started,
                "batch_size": len(texts),
            },
        )
        try:
            result = getattr(self.inner, method)(texts)
            success = True
            return result
        finally:
            append(
                self.path,
                {
                    "event": "end",
                    "role": self.role,
                    "phase": method,
                    "started_ns": started,
                    "finished_ns": time.time_ns(),
                    "batch_size": len(texts),
                    "success": success,
                },
            )

    def batches(self, method, texts):
        # Match the configured provider batch size while retaining actual call intervals.
        size = self.inner.provider.config.batch_size
        return [
            row
            for offset in range(0, len(texts), size)
            for row in self.measure(method, texts[offset : offset + size])
        ]

    def embed_entries(self, texts):
        return self.batches("embed_entries", texts)

    def embed_queries(self, texts):
        return self.batches("embed_queries", texts)


def model(path, role):
    return ObservedEmbedder(PinnedEmbedder(OllamaEmbedder(OllamaConfig.from_env())), path, role)


def make_host(root, port, embedder=None):
    return DurableHost(
        root / "hub.db",
        root / "assets",
        TransportPolicy(f"http://127.0.0.1:{port}"),
        root / "csrf",
        root / "commands",
        root / "ledger",
        root / "ledger-key",
        root / "backups",
        root / "backup-key",
        embedder=embedder,
    )


def provision(root, port, manifest, configuration, rights, embedder):
    root.mkdir(parents=True, exist_ok=False)
    for name in ("csrf", "ledger-key", "backup-key"):
        (root / name).write_bytes(secrets.token_bytes(32))
    (root / "commands").write_text(
        json.dumps(
            {"active": "v1", "keys": {"v1": base64.b64encode(secrets.token_bytes(32)).decode()}}
        )
    )
    ExternalLedger(root / "ledger", (root / "ledger-key").read_bytes(), create=True)
    host = make_host(root, port)
    try:
        owner = host.auth.bootstrap("w4_operator", "W4 operator", secrets.token_urlsafe(24))
        accounts = []
        for i in range(8):
            account = {"login_name": f"w4_player_{i}", "password": secrets.token_urlsafe(24)}
            host.auth.credentials(
                account["login_name"], account["password"], f"provision-{i}", f"W4 test {i}"
            )
            accounts.append(account)
        host.packs.embedder = embedder
        published = host.packs.install(
            manifest, owner_id=owner, operator_id=owner, rights_reference=rights, accept=True
        )
        kwargs = {
            "pack_id": published.installation.pack_id,
            "version": published.installation.version,
            "operator_id": owner,
        }
        artifact = host.packs.accept_casual_artifact(**kwargs, **configuration)
        short = host.packs.accept_casual_artifact(
            **kwargs, initial_board=configuration["initial_board"], schedule=[]
        )
        return accounts, artifact.artifact_id, short.artifact_id
    finally:
        host.close()


def worker(kind, root, port):
    embedder = model(root / f"{kind}-model.jsonl", kind)
    identity = embedder.identity()
    append(
        root / f"{kind}-model.jsonl",
        {"event": "identity", "identity": identity, "fingerprint_hash": fingerprint_hash(identity)},
    )
    if kind == "server":
        from semaphore_hub.host import exclusive_host

        with exclusive_host(root / "hub.db", root / "assets"):
            host = make_host(root, port, embedder)
            try:
                host.serve(port)
            finally:
                host.close()
    else:
        value = parse_manifest((root / "accepted-manifest.json").read_bytes())
        while True:
            started = time.time_ns()
            result = verify_pack(value, embedder, "experiment-arcade-paced-v1")
            append(
                root / "verifier-model.jsonl",
                {
                    "event": "verification_completed",
                    "started_ns": started,
                    "finished_ns": time.time_ns(),
                    "status": result["status"],
                },
            )


def launch(kind, root, port):
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "experiments.durable_acceptance.real_run",
            "--worker",
            kind,
            "--workspace",
            str(root),
            "--port",
            str(port),
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def stop(process):
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)


def ready(process, origin, seconds=60):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("server_start_failed")
        try:
            Client(origin, timeout=1).request("/config")
            return
        except Exception:
            time.sleep(0.1)
    raise RuntimeError("server_start_timeout")


def read_events(path):
    if not path.exists():
        return []
    result = []
    for line in path.read_text(encoding="utf8").splitlines():
        try:
            result.append(json.loads(line))
        except ValueError:
            pass  # A killed subprocess can leave one partial final record.
    return result


def overlap(events, start, finish):
    """Require observed complete successful model calls intersecting load, not a live PID."""
    return any(
        e.get("event") == "end"
        and e.get("success") is True
        and e["started_ns"] < finish
        and e["finished_ns"] > start
        for e in events
    )


def restart_check(client, artifact, root, port, process, origin, account):
    envelope = client.request("/games", {"mode": "casual", "artifact_id": artifact})
    gid = envelope["snapshot"]["game_id"]
    deadline = time.monotonic() + 15
    while envelope["snapshot"]["status"] == "active" and time.monotonic() < deadline:
        time.sleep(0.1)
        envelope = client.request(f"/games/{gid}")
    terminal = envelope["snapshot"]
    if terminal["status"] != "over" or terminal["end_reason"] == "interrupted":
        raise RuntimeError("natural_end_missing")
    history = client.request("/history")
    completed = next(item for item in history["items"] if item["game_id"] == gid)
    active = client.request("/games", {"mode": "casual", "artifact_id": artifact})["snapshot"]
    stop(process)
    replacement = launch("server", root, port)
    try:
        ready(replacement, origin)
        client = Client(origin)
        client.request("/auth/login", account)
        after = client.request(f"/games/{gid}")["snapshot"]
        interrupted = client.request(f"/games/{active['game_id']}")["snapshot"]
        history_after = client.request("/history")
        completed_after = next(item for item in history_after["items"] if item["game_id"] == gid)
        with closing(connect(root / "hub.db")) as db:
            scores = db.execute("SELECT count(*) FROM scores WHERE game_id=?", (gid,)).fetchone()[0]
            aborted_scores = db.execute(
                "SELECT count(*) FROM scores WHERE game_id=?", (active["game_id"],)
            ).fetchone()[0]
        result = {
            "terminal_snapshot_preserved": terminal == after,
            "completed_history_preserved": completed == completed_after,
            "exactly_one_score": scores == 1,
            "active_interrupted": interrupted["end_reason"] == "interrupted",
            "interrupted_without_score": aborted_scores == 0,
        }
        result["passed"] = all(result.values())
        return result
    finally:
        stop(replacement)


def orchestrate(args):
    report = {
        "human_acceptance": False,
        "stage_acceptance": False,
        "server_revision_declared": args.server_revision,
        "load_generator_host": platform.platform(),
        "started_ns": time.time_ns(),
        "remote_model_resources": "not collected",
        "queue_timing": "not instrumented",
    }
    process = verifier = None
    sampler_stop = threading.Event()
    sampler = None
    try:
        raw = args.manifest.read_bytes()
        configuration = json.loads(args.configuration.read_text())
        clues = json.loads(args.clues.read_text())
        if (
            not isinstance(clues, list)
            or not clues
            or any(not isinstance(c, str) or not 1 <= len(c) <= 120 for c in clues)
        ):
            raise ValueError("invalid synthetic clues")
        report["manifest_sha256"] = hashlib.sha256(raw).hexdigest()
        # Workspace must be new; no existing database, secrets, or assets are copied.
        embedder = model(args.output.with_suffix(".installation.jsonl"), "installation")
        report["model_identity"] = embedder.identity()
        accounts, artifact, short = provision(
            args.workspace, args.port, raw, configuration, args.rights_reference, embedder
        )
        (args.workspace / "accepted-manifest.json").write_bytes(raw)
        report["artifact_id"] = artifact
        origin = f"http://127.0.0.1:{args.port}"
        process = launch("server", args.workspace, args.port)
        ready(process, origin)
        resources = []
        try:
            import psutil

            monitored = psutil.Process(process.pid)

            def sample():
                while not sampler_stop.wait(0.1):
                    try:
                        cpu = monitored.cpu_times()
                        resources.append(
                            {
                                "at_ns": time.time_ns(),
                                "rss_bytes": monitored.memory_info().rss,
                                "cpu_seconds": cpu.user + cpu.system,
                            }
                        )
                    except psutil.Error:
                        return

            sampler = threading.Thread(target=sample)
            sampler.start()
            report["local_resources"] = resources
        except ImportError:
            report["local_resources"] = "psutil unavailable; not measured"
        verifier = launch("verifier", args.workspace, args.port)
        deadline = time.monotonic() + 180
        while True:
            observed = read_events(args.workspace / "verifier-model.jsonl")
            if any(
                e.get("event") == "end" and e.get("phase") == "embed_queries" and e.get("success")
                for e in observed
            ):
                break
            if verifier.poll() is not None or time.monotonic() >= deadline:
                raise RuntimeError("verifier_not_ready")
            time.sleep(0.1)
        start = time.time_ns()
        report["load"] = run(origin, accounts, artifact, clues, commands=args.commands)
        finish = time.time_ns()
        report["load_interval"] = {"started_ns": start, "finished_ns": finish}
        report["verifier_exit_was_forced"] = verifier.poll() is None
        stop(verifier)
        report["verifier_exit_code"] = verifier.returncode
        events = read_events(args.workspace / "verifier-model.jsonl")
        report["verifier_events"] = events
        report["verified_overlap"] = overlap(events, start, finish)
        for cohort in report["load"].get("runs", []):
            cohort["verified_overlap"] = any(
                overlap(events, sample["started_ns"], sample["finished_ns"])
                for player in cohort["observations"]
                for sample in player["samples"]
            )
        report["server_model_events"] = read_events(args.workspace / "server-model.jsonl")
        report["real_game_inference_observed"] = overlap(
            report["server_model_events"], start, finish
        )
        client = Client(origin)
        client.request("/auth/login", accounts[0])
        report["restart"] = restart_check(
            client, short, args.workspace, args.port, process, origin, accounts[0]
        )
    except Exception as exc:
        report["failure"] = type(exc).__name__  # Never include model responses/clues/credentials.
    finally:
        sampler_stop.set()
        if sampler:
            sampler.join(timeout=2)
        stop(verifier)
        stop(process)
        report["finished_ns"] = time.time_ns()
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", choices=("server", "verifier"))
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--port", type=int, default=18084)
    for name in ("manifest", "configuration", "clues", "output"):
        parser.add_argument("--" + name, type=Path)
    parser.add_argument("--rights-reference")
    parser.add_argument("--server-revision")
    parser.add_argument("--commands", type=int, default=10)
    parser.add_argument("--allow-model-traffic", action="store_true")
    args = parser.parse_args()
    if args.worker:
        worker(args.worker, args.workspace, args.port)
        return 0
    if not args.allow_model_traffic or not all(
        (
            args.manifest,
            args.configuration,
            args.clues,
            args.output,
            args.rights_reference,
            args.server_revision,
        )
    ):
        parser.error("explicit model traffic opt-in and all input/provenance paths are required")
    if (
        args.workspace.exists()
        or args.output.exists()
        or args.output.with_suffix(".installation.jsonl").exists()
    ):
        parser.error("workspace and evidence outputs must be new")
    if not 1 <= args.commands <= 100 or not 1 <= args.port <= 65535:
        parser.error("invalid command count or port")
    with socket.socket() as check:
        check.bind(("127.0.0.1", args.port))
    args.workspace = args.workspace.resolve()
    args.output = args.output.resolve()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = orchestrate(args)
    cohorts = report.get("load", {}).get("runs", [])
    complete = (
        "failure" not in report
        and report.get("restart", {}).get("passed")
        and report.get("real_game_inference_observed")
        and len(cohorts) == 3
        and all(c["complete"] and c["verified_overlap"] for c in cohorts)
    )
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
