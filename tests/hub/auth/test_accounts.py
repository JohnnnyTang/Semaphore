import json
from contextlib import contextmanager

import pytest

from semaphore_hub.auth import AuthError, AuthHttp, AuthService, SqliteAccounts
from semaphore_hub.auth.service import Admission, digest
from semaphore_hub.policy import SESSION_ABSOLUTE_MS, SESSION_IDLE_MS, TransportPolicy
from semaphore_hub.storage import connect, migrate, transaction


class Clock:
    now = 100000

    def utc_ms(self):
        return self.now

    def monotonic_ms(self):
        return self.now


@pytest.fixture
def setup(tmp_path):
    db = connect(tmp_path / "auth.sqlite3")
    migrate(db)

    @contextmanager
    def tx():
        with transaction(db):
            yield db

    clock = Clock()
    service = AuthService(tx, TransportPolicy("http://localhost:8080"), b"x" * 32, clock)
    yield service, AuthHttp(service), db, clock
    db.close()


def signup(service, login="Alice"):
    return service.credentials(login, "twelve chars password", "127.0.0.1", "<Alice>")


def test_rotation_reset_and_private_projection(setup):
    s, http, db, clock = setup
    first, body = signup(s)
    assert set(body["account"]) == {"account_id", "display_name"}
    row = db.execute("SELECT token_digest,csrf_digest FROM sessions").fetchone()
    assert tuple(row) == (digest(first), digest(body["csrf_token"]))
    second, _ = s.credentials("ALICE", "twelve chars password", "127.0.0.1", prior=first)
    with pytest.raises(AuthError):
        s.session(first)
    assert s.session(second)["account"] == body["account"]
    s.reset_password(body["account"]["account_id"], "replacement password")
    with pytest.raises(AuthError):
        s.session(second)
    third, body = s.credentials("alice", "replacement password", "127.0.0.1")
    with pytest.raises(AuthError):
        s.logout(third, "x" * 43)
    s.logout(third, body["csrf_token"])
    with pytest.raises(AuthError):
        s.session(third)


@pytest.mark.parametrize("elapsed", [SESSION_IDLE_MS, SESSION_ABSOLUTE_MS])
def test_expiry_equality(setup, elapsed):
    s, _, _, clock = setup
    token, _ = signup(s)
    clock.now += elapsed
    with pytest.raises(AuthError):
        s.session(token)


def test_signup_collision_disabled_and_generic_failure(setup):
    s, _, _, _ = setup
    signup(s)
    with pytest.raises(AuthError, match="login_conflict"):
        signup(s, "ALICE")
    s.policy = TransportPolicy("http://localhost:8080", signup_enabled=False)
    with pytest.raises(AuthError, match="signup_disabled"):
        signup(s, "Bob")
    assert s.credentials("alice", "twelve chars password", "127.0.0.1")
    for name in ["alice", "absent"]:
        with pytest.raises(AuthError, match="invalid_credentials"):
            s.credentials(name, "wrong password", "127.0.0.1")


def test_http_guards_no_writes_and_cookie(setup):
    s, http, db, _ = setup
    data = json.dumps(
        {"login_name": "alice", "display_name": "Alice", "password": "twelve chars password"}
    ).encode()
    base = [
        ("Host", s.policy.host),
        ("Origin", s.policy.origin),
        ("Content-Type", "application/json"),
    ]
    for headers in [
        [],
        base + [("Host", s.policy.host)],
        [("Host", s.policy.host), ("Origin", "null")],
    ]:
        assert http.handle("POST", "/api/v1/auth/signup", headers, data, "peer").status in {
            400,
            403,
        }
    assert db.execute("SELECT count(*) FROM accounts").fetchone()[0] == 0
    assert http.handle("POST", "/api/v1/auth/signup", base, b"x" * 16385, "peer").status == 413
    assert (
        http.handle(
            "POST", "/api/v1/auth/signup", base, b'{"login_name":"a","login_name":"b"}', "peer"
        ).status
        == 400
    )
    response = http.handle("POST", "/api/v1/auth/signup", base, data, "peer")
    assert response.status == 201
    cookie = response.headers["Set-Cookie"]
    assert "HttpOnly" in cookie and "SameSite=Strict" in cookie and "Secure" not in cookie
    assert response.headers["Cache-Control"] == "no-store"
    headers = base + [("Cookie", cookie.split(";")[0])]
    assert http.handle("POST", "/api/v1/auth/logout", headers).status == 403
    headers.append(("X-CSRF-Token", response.body["csrf_token"]))
    assert http.handle("POST", "/api/v1/auth/logout", headers).status == 204


def test_tombstone_and_operator_reset(setup):
    s, _, db, clock = setup
    token, body = signup(s)
    operator = s.bootstrap("admin", "Operator", "operator password")
    assert SqliteAccounts(db).by_id(operator).is_operator
    with pytest.raises(ValueError):
        s.bootstrap("other", "Other", "operator password")
    with transaction(db):
        db.execute(
            "UPDATE accounts SET "
            "login_name=NULL,display_name=NULL,password_hash=NULL,"
            "is_operator=0,deleted_at=? WHERE account_id=?",
            (clock.now, body["account"]["account_id"]),
        )
    with pytest.raises(AuthError):
        s.session(token)


def test_admission_bounds():
    admission = Admission()
    for _ in range(5):
        admission.attempt("alice", "peer", 0)
    with pytest.raises(AuthError):
        admission.attempt("alice", "peer", 1)
    admission.attempt("alice", "peer", 60000)
    with admission.work(), admission.work(), pytest.raises(AuthError), admission.work():
        pass
    for i in range(2047):
        admission.attempt(str(i), str(i), 60000)
    with pytest.raises(AuthError):
        admission.attempt("new", "new", 60000)
    assert len(admission.keys) == 4096


def test_commit_failure_returns_no_success(setup):
    s, _, db, _ = setup
    original = s.transactions

    @contextmanager
    def failing():
        with original() as connection:
            yield connection
            raise RuntimeError("commit failed")

    s.transactions = failing
    with pytest.raises(RuntimeError):
        signup(s)
    assert db.execute("SELECT count(*) FROM accounts").fetchone()[0] == 0


def test_security_rejections_do_not_touch_session(setup):
    s, http, db, clock = setup
    token, body = signup(s)
    clock.now += 1000
    base = [
        ("Host", s.policy.host),
        ("Origin", s.policy.origin),
        ("Cookie", "semaphore_session=" + token),
    ]
    before = db.execute("SELECT last_seen_at FROM sessions").fetchone()[0]
    for headers in [
        base,
        base + [("X-CSRF-Token", "x" * 43)],
        base + [("Origin", s.policy.origin)],
    ]:
        assert http.handle("POST", "/api/v1/auth/logout", headers).status in {400, 403}
    assert db.execute("SELECT last_seen_at FROM sessions").fetchone()[0] == before
    assert (
        http.handle(
            "POST", "/api/v1/auth/logout", base + [("X-CSRF-Token", body["csrf_token"])], b"{}"
        ).status
        == 400
    )
    assert (
        http.handle(
            "GET",
            "/api/v1/auth/session",
            [("Host", s.policy.host), ("Cookie", "semaphore_session=" + token)],
        ).status
        == 200
    )


def test_http_content_type_schema_and_key_fail_closed(setup):
    s, http, db, _ = setup
    base = [("Host", s.policy.host), ("Origin", s.policy.origin)]
    assert http.handle("POST", "/api/v1/auth/login", base, b"{}").status == 400
    base.append(("Content-Type", "application/json"))
    for body in [
        b"[]",
        b'{"login_name":1,"password":"x"}',
        b'{"login_name":"abc","password":"x","role":"admin"}',
    ]:
        assert http.handle("POST", "/api/v1/auth/login", base, body).status == 400
    with pytest.raises(ValueError):
        AuthService(s.transactions, s.policy, b"")
    token, _ = signup(s)
    other = AuthService(s.transactions, s.policy, b"y" * 32)
    with pytest.raises(AuthError):
        other.session(token)


def test_password_reset_during_verification_prevents_session(setup):
    s, _, db, _ = setup
    _, body = signup(s)
    real = s.hasher

    class RacingHasher:
        def verify(self, hashed, password):
            result = real.verify(hashed, password)
            with s.transactions() as connection:
                SqliteAccounts(connection).reset_password(
                    body["account"]["account_id"], real.hash("new changed password")
                )
            return result

    s.hasher = RacingHasher()
    with pytest.raises(AuthError, match="invalid_credentials"):
        s.credentials("alice", "twelve chars password", "peer")
    assert db.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0
