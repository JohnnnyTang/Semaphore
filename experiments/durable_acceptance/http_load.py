"""Opt-in HTTP load observations against disposable, operator-prepared accounts.

No model calls occur on import. Never point this runner at participant accounts.
"""

import argparse
import http.client
import json
import math
import platform
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import quote, urlsplit


class ProbeError(Exception):
    """Safe fixed diagnostic; never contains response bodies or credentials."""


class Client:
    def __init__(self, origin, timeout=5):
        url = urlsplit(origin)
        if (
            url.scheme != "http"
            or not url.hostname
            or url.username
            or url.password
            or url.path not in {"", "/"}
            or url.query
            or url.fragment
        ):
            raise ValueError("origin must be an HTTP origin without credentials or path")
        self.host, self.port = url.hostname, url.port or 80
        self.origin = origin.rstrip("/")
        self.timeout = timeout
        self.cookie = self.csrf = None

    def request(self, path, body=None):
        headers = {"Origin": self.origin}
        if self.cookie:
            headers["Cookie"] = self.cookie
        if self.csrf:
            headers["X-CSRF-Token"] = self.csrf
        raw = None if body is None else json.dumps(body).encode()
        if raw is not None:
            headers["Content-Type"] = "application/json"
        conn = http.client.HTTPConnection(self.host, self.port, timeout=self.timeout)
        try:
            conn.request("GET" if raw is None else "POST", "/api/v1" + path, raw, headers)
            response = conn.getresponse()
            data = response.read(1_048_577)
            if len(data) > 1_048_576:
                raise ProbeError("response_too_large")
            if response.status not in {200, 201, 202}:
                raise ProbeError(f"http_{response.status}")
            value = json.loads(data)
            if not isinstance(value, dict):
                raise ProbeError("invalid_response")
            cookie = response.getheader("Set-Cookie")
            if cookie:
                parsed = SimpleCookie(cookie)
                if "semaphore_session" in parsed:
                    self.cookie = "semaphore_session=" + parsed["semaphore_session"].value
            if path == "/auth/login":
                self.csrf = value["csrf_token"]
            return value
        except ProbeError:
            raise
        except Exception:
            raise ProbeError("transport_or_response_error") from None
        finally:
            conn.close()


def summary(samples):
    completed = sorted(s["elapsed_ms"] for s in samples if s["success"])
    return {
        "attempted": len(samples),
        "successful": len(completed),
        "failed": len(samples) - len(completed),
        "p50_ms": completed[math.ceil(len(completed) * 0.5) - 1] if completed else None,
        "p95_ms": completed[math.ceil(len(completed) * 0.95) - 1] if completed else None,
    }


def player(client, artifact, clues, count, gate, *, deadline=10, poll=0.02):
    """One account, one game, one outstanding command. No create retry."""
    samples, errors = [], []
    game = None
    try:
        envelope = client.request("/games", {"mode": "casual", "artifact_id": artifact})
        game = quote(envelope["snapshot"]["game_id"], safe="")
        gate.wait(timeout=15)
        for index in range(count):
            snapshot = client.request(f"/games/{game}")["snapshot"]
            if snapshot["status"] != "active":
                errors.append("early_game_end")
                break
            command = {
                "command_id": str(uuid.uuid4()),
                "expected_revision": snapshot["revision"],
                "clue": clues[index % len(clues)],
            }
            started_ns = time.time_ns()
            started = time.monotonic()
            observation = {"index": index, "success": False, "outcome": "request_failed"}
            try:
                envelope = client.request(f"/games/{game}/commands", command)
                while envelope["receipt"]["outcome"] == "pending":
                    if time.monotonic() - started >= deadline:
                        raise ProbeError("receipt_timeout")
                    time.sleep(poll)
                    envelope = client.request(f"/games/{game}/receipts/{command['command_id']}")
                outcome = envelope["receipt"]["outcome"]
                observation.update(outcome=outcome, success=outcome in {"clear", "miss"})
            except ProbeError as exc:
                observation["outcome"] = str(exc)
            finally:
                observation["started_ns"] = started_ns
                observation["finished_ns"] = time.time_ns()
                observation["elapsed_ms"] = (time.monotonic() - started) * 1000
                samples.append(observation)
            if observation["outcome"] in {"clear", "miss"}:
                retry = client.request(f"/games/{game}/commands", command)
                if retry["receipt"] != envelope["receipt"]:
                    errors.append("exact_retry_changed")
                    break
            elif observation["outcome"] in {"receipt_timeout", "transport_or_response_error"}:
                break  # Do not stack commands after an uncertain response.
    except threading.BrokenBarrierError:
        errors.append("player_start_failed")
    except ProbeError as exc:
        errors.append(str(exc))
        gate.abort()
    except Exception:
        errors.append("invalid_response")
        gate.abort()
    finally:
        if game is not None:
            try:
                client.request(f"/games/{game}/quit", {})
            except Exception:
                errors.append("cleanup_failed")
    return {"samples": samples, "errors": errors, "requested": count}


def run(origin, accounts, artifact, clues, *, counts=(1, 4, 8), commands=10, client_factory=Client):
    """Sequential cohorts; clients log in before timed work and synchronize game starts."""
    report = {
        "kind": "automated_http_load",
        "human_acceptance": False,
        "model_execution_verified": False,
        "verifier_overlap": False,
        "queue_and_embedding_timing_available": False,
        "resource_measurements": None,
        "latency_definition": "command POST through final receipt, including polling",
        "target_p95_ms": 100,
        "load_generator_host": platform.platform(),
        "runs": [],
    }
    try:
        clients = []
        account_ids = set()
        for account in accounts[: max(counts)]:
            client = client_factory(origin)
            session = client.request("/auth/login", account)
            account_id = session["account"]["account_id"]
            if account_id in account_ids:
                raise ProbeError("duplicate_account")
            account_ids.add(account_id)
            clients.append(client)
        report["artifact"] = clients[0].request("/artifacts/" + quote(artifact, safe=""))
        for count in counts:
            cohort_started = time.time_ns()
            gate = threading.Barrier(count)
            with ThreadPoolExecutor(max_workers=count) as pool:
                futures = [
                    pool.submit(player, client, artifact, clues, commands, gate)
                    for client in clients[:count]
                ]
                players = [f.result() for f in futures]
            samples = [s for p in players for s in p["samples"]]
            stats = summary(samples)
            complete = (
                stats["attempted"] == count * commands
                and stats["failed"] == 0
                and not any(p["errors"] for p in players)
            )
            report["runs"].append(
                {
                    "players": count,
                    "started_ns": cohort_started,
                    "finished_ns": time.time_ns(),
                    "observations": players,
                    **stats,
                    "complete": complete,
                    "latency_target_met": complete and stats["p95_ms"] <= 100,
                }
            )
    except Exception:
        report["setup_error"] = "setup_failed"
    # HTTP alone cannot establish real inference, verifier contention or human acceptance.
    report["stage_acceptance"] = False
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--accounts", type=Path, required=True)
    parser.add_argument("--clues", type=Path, required=True)
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--server-revision", required=True)
    parser.add_argument("--commands", type=int, default=10)
    parser.add_argument("--players", type=int, choices=(1, 4, 8), nargs="+", default=[1, 4, 8])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--disposable-test-installation", action="store_true", required=True)
    args = parser.parse_args()
    if len(args.server_revision) != 40 or any(
        c not in "0123456789abcdef" for c in args.server_revision
    ):
        parser.error("server revision must be the full lowercase commit SHA")
    accounts, clues = json.loads(args.accounts.read_text()), json.loads(args.clues.read_text())
    if (
        not 1 <= args.commands <= 100
        or not isinstance(accounts, list)
        or len(accounts) < max(args.players)
    ):
        parser.error("provide enough test accounts and 1..100 commands")
    if any(
        not isinstance(a, dict)
        or set(a) != {"login_name", "password"}
        or not all(isinstance(v, str) and v for v in a.values())
        for a in accounts
    ):
        parser.error("accounts must contain login_name/password objects")
    if len({a["login_name"].casefold() for a in accounts}) != len(accounts):
        parser.error("test accounts must be distinct")
    if (
        not isinstance(clues, list)
        or not clues
        or any(not isinstance(c, str) or not 1 <= len(c) <= 120 for c in clues)
    ):
        parser.error("clues must be a nonempty list of synthetic clues of 1..120 characters")
    Client(args.origin)  # Validate before any network mutation.
    # Reserve the evidence path before running, so a typo cannot discard observations.
    with args.output.open("x", encoding="utf8") as output:
        result = run(
            args.origin, accounts, args.artifact, clues, counts=args.players, commands=args.commands
        )
        result["server_revision_declared"] = args.server_revision
        json.dump(result, output, indent=2)
        output.write("\n")
    return (
        0
        if result.get("runs")
        and all(r["complete"] for r in result["runs"])
        and "setup_error" not in result
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
