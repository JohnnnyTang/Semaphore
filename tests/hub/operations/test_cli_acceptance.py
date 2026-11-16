"""W4 operator acceptance through the installed module's public CLI boundary."""

import base64
import json
import os
import secrets
import subprocess
import sys
from contextlib import closing
from hashlib import sha256
from importlib.resources import files
from pathlib import Path

import pytest

from semaphore_hub.host import exclusive_host
from semaphore_hub.operations import ExternalLedger
from semaphore_hub.storage import connect

ROOT = Path(__file__).resolve().parents[3]


def cli(*args, input=None, success=True):
    env = dict(os.environ, PYTHONPATH=os.pathsep.join((str(ROOT / "packages"), str(ROOT))))
    result = subprocess.run(
        [sys.executable, "-m", "semaphore_hub", *map(str, args)],
        cwd=ROOT,
        env=env,
        input=input,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if success:
        assert result.returncode == 0, result.stderr
    else:
        assert result.returncode != 0
    return result


@pytest.fixture
def deployment(tmp_path):
    for name in ("csrf", "ledger-key", "backup-key"):
        (tmp_path / name).write_bytes(secrets.token_bytes(32))
    (tmp_path / "commands.json").write_text(
        json.dumps(
            {"active": "v1", "keys": {"v1": base64.b64encode(secrets.token_bytes(32)).decode()}}
        )
    )
    ExternalLedger(tmp_path / "ledger", (tmp_path / "ledger-key").read_bytes(), create=True)
    database = tmp_path / "hub.db"
    common = [database, "--assets", tmp_path / "assets"]
    for option, name in (
        ("csrf-key", "csrf"),
        ("command-keys", "commands.json"),
        ("ledger", "ledger"),
        ("ledger-key", "ledger-key"),
        ("backups", "backups"),
        ("backup-key", "backup-key"),
    ):
        common.extend(("--" + option, tmp_path / name))
    return database, common


def test_cli_fresh_migrate_bootstrap_delete_restore(deployment, tmp_path, monkeypatch, capsys):
    database, common = deployment
    assert "schema version 2" in cli(database, "migrate").stdout
    # Windows getpass reads the console even when stdin is piped. Exercise main
    # with only the interactive password boundary replaced; other commands use subprocesses.
    from semaphore_hub.__main__ import main

    password = "synthetic operator password"
    monkeypatch.setattr("getpass.getpass", lambda _: password)
    main([*map(str, common), "bootstrap", "operator", "Operator"])
    output = capsys.readouterr()
    account = output.out.strip()
    assert password not in output.out + output.err
    with closing(connect(database)) as db:
        assert db.execute("SELECT account_id FROM accounts").fetchone()[0] == account
    backup = Path(cli(*common, "backup").stdout.strip())
    assert backup.is_file()
    cli(*common, "delete-clues", account)
    cli(*common, "delete-account", account)
    cli(*common, "cleanup")
    destination = tmp_path / "restored.db"
    cli(*common, "restore", backup, destination)
    with closing(connect(destination)) as db:
        row = db.execute("SELECT deleted_at, display_name, password_hash FROM accounts").fetchone()
        assert row[0] is not None and row[1] is None and row[2] is None
        assert db.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert db.execute("PRAGMA foreign_key_check").fetchone() is None
    before = destination.read_bytes()
    cli(*common, "restore", backup, destination, success=False)
    assert destination.read_bytes() == before


def test_cli_upgrades_v1_and_rejects_edited_history(tmp_path):
    path = tmp_path / "v1.db"
    name = "0001_foundation.sql"
    raw = files("semaphore_hub.migrations").joinpath(name).read_bytes()
    with closing(connect(path)) as db:
        db.executescript(raw.decode())
        db.execute(
            "CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, name TEXT, sha256 TEXT)"
        )
        db.execute("INSERT INTO schema_migrations VALUES (1,?,?)", (name, sha256(raw).hexdigest()))
        db.execute("INSERT INTO accounts VALUES ('a','alice','Alice','hash',1,0,NULL)")
    cli(path, "migrate")
    cli(path, "migrate")
    with closing(connect(path)) as db:
        assert db.execute("SELECT display_name FROM accounts").fetchone()[0] == "Alice"
        assert db.execute("SELECT count(*) FROM published_versions").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM schema_migrations").fetchone()[0] == 2
        db.execute("UPDATE schema_migrations SET sha256='edited' WHERE version=1")
    result = cli(path, "migrate", success=False)
    assert "unknown or modified migration history" in result.stderr


def test_cli_refuses_live_host_and_missing_ledger(deployment, tmp_path):
    database, common = deployment
    cli(database, "migrate")
    with exclusive_host(database):
        result = cli(*common, "cleanup", success=False)
        assert "hub host is busy" in result.stderr
    (tmp_path / "ledger").unlink()
    cli(*common, "backup", success=False)
    assert not (tmp_path / "ledger").exists()
    assert not list((tmp_path / "backups").glob("*.backup"))
