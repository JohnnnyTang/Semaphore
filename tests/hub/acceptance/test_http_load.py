"""Runner self-checks, deliberately synthetic; these are not model measurements."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from experiments.durable_acceptance.http_load import Client, ProbeError, player, run, summary


class ScriptClient:
    def __init__(self, origin=None):
        self.clues = 0
        self.receipt = None
        self.commands = []

    def request(self, path, body=None):
        if path == "/auth/login":
            return {"csrf_token": "private-token", "account": {"account_id": str(id(self))}}
        if path.startswith("/artifacts/"):
            return {"artifact_id": "test", "cohort": {"fingerprint_hash": "synthetic"}}
        if path.endswith("/quit"):
            return {}
        if path.endswith("/commands"):
            self.commands.append(body)
            if self.receipt is None or self.receipt["command_id"] != body["command_id"]:
                self.clues += 1
                self.receipt = {"command_id": body["command_id"], "outcome": "miss"}
            return {"receipt": self.receipt}
        return {"snapshot": {"game_id": "test", "revision": self.clues, "status": "active"}}


def test_counts_and_retry_and_no_sensitive_report():
    report = run(
        "http://test",
        [{"login_name": f"private-{i}", "password": "secret"} for i in range(8)],
        "test",
        ["private-clue"],
        commands=2,
        client_factory=ScriptClient,
    )
    assert [r["attempted"] for r in report["runs"]] == [2, 8, 16]
    assert all(r["complete"] for r in report["runs"])
    assert not report["stage_acceptance"]
    assert not report["model_execution_verified"]
    assert not report["verifier_overlap"]
    assert "private" not in json.dumps(report)
    client = ScriptClient()
    result = player(client, "test", ["clue"], 2, threading.Barrier(1))
    assert client.clues == 2
    assert len(client.commands) == 4
    assert not result["errors"]


def test_failures_and_rejections_do_not_become_fast_successes():
    class Reject(ScriptClient):
        def request(self, path, body=None):
            if path.endswith("/commands"):
                return {"receipt": {"outcome": "illegal_clue"}}
            return super().request(path, body)

    report = run(
        "http://test", [{}], "test", ["clue"], counts=[1], commands=2, client_factory=Reject
    )
    result = report["runs"][0]
    assert result["failed"] == 2
    assert result["p95_ms"] is None
    assert not result["complete"] and not result["latency_target_met"]
    assert summary([])["p50_ms"] is None


def test_start_failure_unblocks_other_players():
    class Fail(ScriptClient):
        def request(self, path, body=None):
            if path == "/games":
                raise ProbeError("http_503")
            return super().request(path, body)

    report = run(
        "http://test", [{}] * 4, "test", ["clue"], counts=[4], commands=2, client_factory=Fail
    )
    assert report["runs"][0]["attempted"] == 0
    assert not report["runs"][0]["complete"]


def test_pending_timeout_preserves_sample_and_stops():
    class Pending(ScriptClient):
        def request(self, path, body=None):
            if path.endswith("/commands"):
                return {"receipt": {"outcome": "pending"}}
            return super().request(path, body)

    result = player(Pending(), "test", ["clue"], 3, threading.Barrier(1), deadline=0)
    assert len(result["samples"]) == 1
    assert result["samples"][0]["outcome"] == "receipt_timeout"
    assert not result["samples"][0]["success"]


def test_http_cookie_csrf_and_no_redirect_following():
    seen = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            seen.append(dict(self.headers))
            self.rfile.read(int(self.headers["Content-Length"]))
            self.send_response(200)
            self.send_header("Set-Cookie", "semaphore_session=secret; HttpOnly; Path=/")
            self.end_headers()
            self.wfile.write(b'{"csrf_token":"csrf-secret"}')

        def do_GET(self):
            self.send_response(302)
            self.send_header("Location", "http://example.invalid/steal")
            self.end_headers()

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        client = Client(f"http://127.0.0.1:{server.server_port}")
        client.request("/auth/login", {"login_name": "test", "password": "secret"})
        client.request("/games", {})
        assert seen[1]["Cookie"] == "semaphore_session=secret"
        assert seen[1]["X-CSRF-Token"] == "csrf-secret"
        with pytest.raises(ProbeError, match="http_302"):
            client.request("/artifacts/test")
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def test_duplicate_server_accounts_fail_before_creating_games():
    class Duplicate(ScriptClient):
        def request(self, path, body=None):
            if path == "/auth/login":
                return {"account": {"account_id": "same"}}
            raise AssertionError("must not create games")

    report = run("http://test", [{}] * 4, "test", ["clue"], counts=[4], client_factory=Duplicate)
    assert report["setup_error"] == "setup_failed"
    assert report["runs"] == []
