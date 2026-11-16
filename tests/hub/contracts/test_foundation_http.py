import json
from contextlib import closing

from semaphore_hub.auth import AuthService
from semaphore_hub.foundation import FoundationDatabase
from semaphore_hub.http import FoundationHttp
from semaphore_hub.policy import TransportPolicy
from semaphore_hub.storage import connect, migrate


class ReadProbe:
    calls = 0

    def list_packs(self, cursor=None, limit=20):
        self.calls += 1
        assert limit == 20 and cursor is None
        return {"items": [], "next_cursor": None}


def test_pack_routes_authenticate_before_reading_and_reopen_sessions(tmp_path):
    path = tmp_path / "hub.db"
    with closing(connect(path)) as connection:
        migrate(connection)
    database = FoundationDatabase(path)
    policy = TransportPolicy("http://localhost:8080")
    service = AuthService(database.transaction, policy, b"x" * 32)
    packs = ReadProbe()
    http = FoundationHttp(service, packs)
    base = [("Host", policy.host), ("Origin", policy.origin)]
    assert http.handle("GET", "/api/v1/packs", base).status == 401
    assert packs.calls == 0
    response = http.handle(
        "POST",
        "/api/v1/auth/signup",
        base + [("Content-Type", "application/json")],
        json.dumps(
            {"login_name": "alice", "display_name": "Alice", "password": "long test password"}
        ).encode(),
        "peer",
    )
    assert response.status == 201
    headers = base + [("Cookie", response.headers["Set-Cookie"].split(";")[0])]
    # A new service instance reads the committed session from a new DB connection.
    http = FoundationHttp(AuthService(database.transaction, policy, b"x" * 32), packs)
    result = http.handle("GET", "/api/v1/packs", headers)
    assert result.status == 200 and result.body == {"items": [], "next_cursor": None}
    assert result.headers["Cache-Control"] == "no-store"
    assert http.handle("GET", "/api/v1/packs", headers + [("Host", "evil")]).status == 400
    assert http.handle("GET", "/api/v1/packs?limit=1&limit=2", headers).status == 400
    assert http.handle("GET", "/api/v1/packs?limit=0", headers).status == 400
    assert packs.calls == 1
    assert http.handle("GET", "/api/v1/games/current", headers).status == 404
    logout = http.handle(
        "POST", "/api/v1/auth/logout", headers + [("X-CSRF-Token", response.body["csrf_token"])]
    )
    assert logout.status == 204
    assert http.handle("GET", "/api/v1/packs", headers).status == 401
