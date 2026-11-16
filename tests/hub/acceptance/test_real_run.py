"""Offline orchestrator checks; model/network execution is deliberately absent."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from experiments.durable_acceptance import real_run

from semaphore_core.verification import load, manifest_hashes


def test_model_telemetry_records_failure_without_text(tmp_path):
    class Model:
        provider = SimpleNamespace(config=SimpleNamespace(batch_size=16))

        def embed_queries(self, texts):
            raise RuntimeError("private clue or model response")

    path = tmp_path / "events"
    model = real_run.ObservedEmbedder(Model(), path, "verifier")
    with pytest.raises(RuntimeError):
        model.embed_queries(["secret clue"])
    events = real_run.read_events(path)
    assert len(events) == 2 and events[1]["success"] is False
    assert events[0]["batch_size"] == 1
    assert "secret" not in path.read_text() and "private" not in path.read_text()
    assert not real_run.overlap(events, 0, 2**64)


def test_overlap_requires_successful_completed_model_call(tmp_path):
    events = [{"event": "start", "started_ns": 100}]
    assert not real_run.overlap(events, 100, 200)
    events += [{"event": "end", "started_ns": 99, "finished_ns": 101, "success": True}]
    assert real_run.overlap(events, 100, 200)
    assert not real_run.overlap(events, 101, 200)
    path = tmp_path / "events"
    path.write_text(json.dumps(events[1]) + '\n{"partial":')
    assert real_run.read_events(path) == [events[1]]


def test_provision_real_accounts_and_sqlite_without_model(tmp_path, monkeypatch):
    def measured(value, embedder, ruleset):
        hashes = manifest_hashes(value)
        embedder.entry_vectors = [[1.0] + [0.0] * 2559 for _ in value.manifest["entries"]]
        return dict(
            manifest_digest=hashes.manifest_digest,
            semantic_hash=hashes.semantic_hash,
            vector_hash=hashes.vector_hash,
            fingerprint_hash=load("model-lock.json")["fingerprint_sha256"],
            protocol_hash="a" * 64,
            ruleset_id=ruleset,
            status="measured",
            metrics=dict(reachability=1.0),
        )

    monkeypatch.setattr("semaphore_hub.packs.service.verify_pack", measured)
    raw = Path("packs/everyday.json").read_bytes()
    ids = [entry["id"] for entry in json.loads(raw)["entries"]]
    root = tmp_path / "new"
    accounts, artifact, short = real_run.provision(
        root, 18084, raw, {"initial_board": ids[:5], "schedule": []}, "offline test only", object()
    )
    assert len(accounts) == 8 and artifact != short
    assert len({a["password"] for a in accounts}) == 8
    assert len({(root / name).read_bytes() for name in ("csrf", "ledger-key", "backup-key")}) == 3
    host = real_run.make_host(root, 18084)
    try:
        host.start()
        with host.transactions() as db:
            assert db.execute("SELECT count(*) FROM accounts").fetchone()[0] == 9
        _, session = host.auth.credentials(
            **{
                "login": accounts[0]["login_name"],
                "password": accounts[0]["password"],
                "peer": "test",
            }
        )
        assert session["account"]["display_name"] == "W4 test 0"
    finally:
        host.close()
    with pytest.raises(FileExistsError):
        real_run.provision(root, 18084, raw, {}, "test", object())


def test_launch_uses_importable_module_and_discards_logs(tmp_path, monkeypatch):
    captured = {}

    def popen(command, **kwargs):
        captured.update(command=command, **kwargs)
        return "process"

    monkeypatch.setattr(real_run.subprocess, "Popen", popen)
    assert real_run.launch("server", tmp_path, 8080) == "process"
    assert captured["command"][2] == "experiments.durable_acceptance.real_run"
    assert captured["stderr"] == real_run.subprocess.DEVNULL


def test_failure_always_writes_safe_report(tmp_path, monkeypatch):
    manifest = tmp_path / "manifest"
    config = tmp_path / "config"
    clues = tmp_path / "clues"
    manifest.write_text("{}")
    config.write_text("{}")
    clues.write_text('["clue"]')

    class Broken:
        def identity(self):
            raise RuntimeError("secret detail")

    monkeypatch.setattr(real_run, "model", lambda *args: Broken())
    args = SimpleNamespace(
        server_revision="a" * 40,
        manifest=manifest,
        configuration=config,
        clues=clues,
        output=tmp_path / "report",
        workspace=tmp_path / "install",
    )
    result = real_run.orchestrate(args)
    assert result["failure"] == "RuntimeError"
    assert "secret detail" not in args.output.read_text()
    assert not result["stage_acceptance"]


def test_resource_tree_includes_child_and_retains_exited_cpu():
    class ProcessError(Exception):
        pass

    class Process:
        def __init__(self, pid, rss, cpu):
            self.pid, self.rss, self.cpu = pid, rss, cpu
            self.alive = True
            self.descendants = []

        def children(self, recursive):
            assert recursive
            return self.descendants

        def create_time(self):
            return self.pid * 10

        def is_running(self):
            return self.alive

        def cpu_times(self):
            return SimpleNamespace(user=self.cpu, system=0.25)

        def memory_info(self):
            return SimpleNamespace(rss=self.rss)

        def name(self):
            return "python.exe"

    launcher, interpreter = Process(10, 3_000_000, 0), Process(11, 90_000_000, 2)
    launcher.descendants = [interpreter]
    collector = real_run.ProcessTreeResources(launcher, ProcessError)
    first = collector.sample()
    assert first["rss_bytes"] == 93_000_000
    assert first["cpu_seconds"] == 2.5
    assert [p["pid"] for p in first["members"]] == [10, 11]
    interpreter.alive = False
    launcher.descendants = []
    after = collector.sample()
    assert after["rss_bytes"] == 3_000_000
    assert after["cpu_seconds"] == first["cpu_seconds"]
