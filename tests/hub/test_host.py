import json
import socket
import threading
from contextlib import closing, contextmanager
from http.client import HTTPConnection

import pytest

from semaphore_hub.__main__ import bounded_read, main
from semaphore_hub.host import FoundationServer, foundation_ready, prepare
from semaphore_hub.http import FoundationHttp
from semaphore_hub.policy import TransportPolicy


@pytest.fixture
def services(tmp_path):
    key = tmp_path / "csrf.key"
    key.write_bytes(b"k" * 32)
    return prepare(
        tmp_path / "hub.db", tmp_path / "assets", TransportPolicy("http://localhost:8080"), key
    )


@contextmanager
def listening(services):
    auth, packs = services
    foundation_ready(auth, packs)
    server = FoundationServer(("127.0.0.1", 0), FoundationHttp(auth, packs))
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def request(port, method, path, body=None, headers=None):
    with closing(HTTPConnection("127.0.0.1", port, timeout=5)) as client:
        client.request(method, path, body, {"Host": "localhost:8080", **(headers or {})})
        response = client.getresponse()
        return response.status, dict(response.getheaders()), response.read()


def test_real_http_login_pack_logout(services):
    with listening(services) as port:
        assert request(port, "GET", "/api/v1/packs")[0] == 401
        status, headers, raw = request(
            port,
            "POST",
            "/api/v1/auth/signup",
            json.dumps(
                {"login_name": "alice", "display_name": "Alice", "password": "long test password"}
            ),
            {"Origin": "http://localhost:8080", "Content-Type": "application/json"},
        )
        assert status == 201
        cookie = headers["Set-Cookie"].split(";")[0]
        assert "HttpOnly" in headers["Set-Cookie"]
        assert request(port, "GET", "/api/v1/packs", headers={"Cookie": cookie})[0] == 200
        assert (
            request(
                port,
                "POST",
                "/api/v1/auth/logout",
                headers={
                    "Origin": "http://localhost:8080",
                    "Cookie": cookie,
                    "X-CSRF-Token": json.loads(raw)["csrf_token"],
                },
            )[0]
            == 204
        )
        assert request(port, "GET", "/api/v1/packs", headers={"Cookie": cookie})[0] == 401


def test_transport_rejects_ambiguous_and_large_body(services):
    with listening(services) as port:
        for extra, expected in [
            (b"Content-Length: 2\r\nContent-Length: 2\r\n", b"400"),
            (b"Transfer-Encoding: chunked\r\n", b"400"),
            (b"Content-Length: 16385\r\n", b"413"),
        ]:
            with socket.create_connection(("127.0.0.1", port), timeout=5) as client:
                client.sendall(
                    b"POST /api/v1/auth/signup HTTP/1.1\r\nHost: localhost:8080\r\n"
                    + extra
                    + b"\r\n"
                )
                assert expected in client.recv(4096).split(b"\r\n")[0]
        assert request(port, "GET", "/api/v1/config", headers={"Host": "evil.example"})[0] == 403


def test_missing_key_and_network_bind_fail_closed(tmp_path):
    with pytest.raises(FileNotFoundError):
        prepare(
            tmp_path / "hub.db",
            tmp_path / "assets",
            TransportPolicy("http://localhost:8080"),
            tmp_path / "missing",
        )
    with pytest.raises(ValueError):
        FoundationServer(("0.0.0.0", 8080), None)


def test_foundation_refuses_deleted_accounts(services):
    auth, packs = services
    account = auth.bootstrap("operator", "Operator", "long test password")
    with auth.transactions() as db:
        db.execute(
            "UPDATE accounts SET deleted_at=1, login_name=NULL, display_name=NULL, "
            "password_hash=NULL, is_operator=0 "
            "WHERE account_id=?",
            (account,),
        )
    with pytest.raises(RuntimeError, match="ledger"):
        foundation_ready(auth, packs)


def test_operator_bootstrap_reset_and_legacy_migrate(tmp_path, monkeypatch, capsys):
    db = tmp_path / "hub.db"
    key = tmp_path / "key"
    key.write_bytes(b"k" * 32)
    main([str(db)])
    assert "schema version" in capsys.readouterr().out
    monkeypatch.setattr("getpass.getpass", lambda _: "long test password")
    args = [str(db), "--csrf-key", str(key), "--assets", str(tmp_path / "assets")]
    main([*args, "bootstrap", "operator", "Operator"])
    account_id = capsys.readouterr().out.strip()
    assert len(account_id) == 32
    main([*args, "reset-password", account_id])
    assert "sessions revoked" in capsys.readouterr().out
    key.write_bytes(b"bad")
    with pytest.raises(ValueError, match="32 bytes"):
        main([*args, "bootstrap", "operator", "Operator"])


def test_operator_input_cap(tmp_path):
    path = tmp_path / "data"
    path.write_bytes(b"abcd")
    with pytest.raises(ValueError):
        bounded_read(path, 3)


def test_host_lock_contention_and_release(tmp_path):
    import subprocess
    import sys

    from semaphore_hub.host import exclusive_host

    database = tmp_path / "hub.db"
    code = (
        "from semaphore_hub.host import exclusive_host; "
        "import sys; "
        "lock=exclusive_host(sys.argv[1]); lock.__enter__(); lock.__exit__(None,None,None)"
    )
    with exclusive_host(database):
        result = subprocess.run([sys.executable, "-c", code, str(database)], capture_output=True)
        assert result.returncode != 0 and b"hub host is busy" in result.stderr
    result = subprocess.run([sys.executable, "-c", code, str(database)], capture_output=True)
    assert result.returncode == 0


def test_shared_assets_exclude_different_databases(tmp_path):
    from semaphore_hub.host import exclusive_host

    with exclusive_host(tmp_path / "a.db", tmp_path / "assets"):
        with pytest.raises(RuntimeError, match="busy"):
            with exclusive_host(tmp_path / "b.db", tmp_path / "assets"):
                pytest.fail("asset lock was bypassed")
