"""Transport security at the account/game composition boundary."""

import json
from contextlib import closing

from semaphore_hub.auth import AuthService
from semaphore_hub.durable_http import DurableHttp
from semaphore_hub.foundation import FoundationDatabase
from semaphore_hub.policy import TransportPolicy
from semaphore_hub.storage import connect, migrate


class GameProbe:
    calls = []

    def create(self, player, payload):
        self.calls.append((player, payload))
        return {"accepted": True}


def test_game_mutation_auth_origin_csrf_before_domain(tmp_path):
    path = tmp_path / "hub.db"
    with closing(connect(path)) as db:
        migrate(db)
    auth = AuthService(
        FoundationDatabase(path).transaction, TransportPolicy("http://localhost:8080"), b"k" * 32
    )
    games = GameProbe()
    games.calls = []
    http = DurableHttp(auth, None, games, None)
    base = [
        ("Host", "localhost:8080"),
        ("Origin", "http://localhost:8080"),
        ("Content-Type", "application/json"),
    ]
    assert http.handle("GET", "http://[invalid", base).status == 400
    body = b'{"mode":"casual","artifact_id":"fixture"}'
    assert http.handle("POST", "/api/v1/games", base, body).status == 401
    registered = http.handle(
        "POST",
        "/api/v1/auth/signup",
        base,
        json.dumps(
            {"login_name": "alice", "display_name": "Alice", "password": "long test password"}
        ).encode(),
    )
    assert registered.status == 201
    headers = base + [("Cookie", registered.headers["Set-Cookie"].split(";")[0])]
    assert http.handle("POST", "/api/v1/games", headers, body).status == 403
    valid = headers + [("X-CSRF-Token", registered.body["csrf_token"])]
    assert http.handle("POST", "/api/v1/games", valid + [("Host", "evil")], body).status == 400
    bad_origin = [(k, "http://evil" if k == "Origin" else v) for k, v in valid]
    assert http.handle("POST", "/api/v1/games", bad_origin, body).status == 403
    assert http.handle("POST", "/api/v1/games", valid, b"x" * 16385).status == 413
    assert not games.calls
    assert http.handle("POST", "/api/v1/games", valid, body).status == 201
    assert games.calls == [(registered.body["account"]["account_id"], json.loads(body))]
    assert http.handle("POST", "/api/v1/auth/logout", valid).status == 204
    assert http.handle("POST", "/api/v1/games", valid, body).status == 401
    assert len(games.calls) == 1
