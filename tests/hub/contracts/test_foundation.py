"""Storage invariants and startup failures, independent of production services."""

import sqlite3
from contextlib import closing

import pytest

from semaphore_hub.application import Application
from semaphore_hub.storage import MigrationError, connect, migrate, transaction


@pytest.fixture
def db():
    with closing(connect(":memory:")) as connection:
        assert migrate(connection) == 2
        yield connection


def seed(db):
    db.execute("INSERT INTO accounts VALUES ('a', 'alice', 'Alice', 'hash', 0, 0, NULL)")
    db.execute("INSERT INTO packs VALUES ('p', 'a', 0, NULL)")
    db.execute("INSERT INTO pack_versions VALUES ('v', 'p', '1', X'00', 'm', 's', 'v', 0)")
    db.execute("""INSERT INTO games VALUES (
        'g', 'a', 'v', 'casual', 'f', '{}', 'r', 'c', '{}', 'artifact', NULL,
        0, 'active', 0, NULL, NULL, '{}')""")


def test_migration_reopen_and_constraints(tmp_path):
    path = tmp_path / "hub.sqlite3"
    with closing(connect(path)) as db:
        migrate(db)
        seed(db)
    with closing(connect(path)) as db:
        assert migrate(db) == 2
        assert db.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM games").fetchone()[0] == 1
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("INSERT INTO packs VALUES ('other', 'missing', 0, NULL)")
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("INSERT INTO accounts VALUES ('b', 'alice', 'B', 'hash', 0, 0, NULL)")
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("INSERT INTO pack_versions VALUES ('w','p','1',X'01','x','s','v',0)")


@pytest.mark.parametrize(
    "change",
    [
        "UPDATE schema_migrations SET sha256 = 'edited'",
        "INSERT INTO schema_migrations VALUES (999, 'future.sql', 'future')",
    ],
)
def test_modified_or_newer_history_rejected(db, change):
    db.execute(change)
    with pytest.raises(MigrationError):
        migrate(db)
    assert not db.in_transaction


def test_unversioned_database_not_adopted():
    with closing(connect(":memory:")) as db:
        db.execute("CREATE TABLE experiment (id TEXT)")
        with pytest.raises(MigrationError, match="unversioned"):
            migrate(db)
        assert (
            db.execute("SELECT name FROM sqlite_master WHERE name='schema_migrations'").fetchone()
            is None
        )


def test_migration_failure_rolls_back_ddl_and_ledger(tmp_path, monkeypatch):
    from semaphore_hub.storage import database

    (tmp_path / "0001_broken.sql").write_text(
        "CREATE TABLE example (id TEXT);\nINSERT INTO missing VALUES (1);\n"
    )
    monkeypatch.setattr(database, "files", lambda _: tmp_path)
    with closing(connect(":memory:")) as db:
        with pytest.raises(sqlite3.OperationalError):
            migrate(db)
        assert list(db.execute("SELECT name FROM sqlite_master WHERE type='table'")) == []


def test_transaction_rollback_and_nesting(db):
    with pytest.raises(RuntimeError, match="nested"):
        with transaction(db):
            with transaction(db):
                pass
    assert not db.in_transaction
    with pytest.raises(ValueError):
        with transaction(db):
            seed(db)
            raise ValueError("commit must not happen")
    assert db.execute("SELECT count(*) FROM accounts").fetchone()[0] == 0


def test_immutable_pins_and_final_receipts(db):
    seed(db)
    for sql in [
        "UPDATE pack_versions SET manifest_digest='changed'",
        "UPDATE games SET config_digest='changed'",
    ]:
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(sql)
    db.execute("INSERT INTO commands VALUES ('g','c','hmac','key1',0,'pending','{}',NULL)")
    db.execute("UPDATE commands SET state='final', receipt_json='{\"outcome\":\"miss\"}'")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("UPDATE commands SET receipt_json='{}'")
    # Terminal time can set retention without rewriting the immutable final receipt.
    db.execute("UPDATE commands SET expires_at=7776000000")


def test_score_requires_natural_terminal_and_is_once_only(db):
    seed(db)
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO scores VALUES ('g','a','Alice',0,1)")
    with transaction(db):
        db.execute("UPDATE games SET status='over', finished_at=1, end_reason='pack_cleared'")
        db.execute("INSERT INTO scores VALUES ('g','a','Alice',0,1)")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO scores VALUES ('g','a','Alice',0,1)")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("UPDATE games SET status='active', finished_at=NULL, end_reason=NULL")
    db.execute("UPDATE scores SET player_id=NULL, display_name=NULL")
    assert db.execute("SELECT score FROM scores").fetchone()[0] == 0


def test_interrupted_game_has_no_score(db):
    seed(db)
    db.execute("UPDATE games SET status='over', finished_at=1, end_reason='interrupted'")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO scores VALUES ('g','a','Alice',0,1)")


class FakeClock:
    def utc_ms(self):
        return 42

    def monotonic_ms(self):
        return 7


class FakeRecovery:
    def __init__(self, fail_at=None):
        self.calls = []
        self.fail_at = fail_at

    def record(self, name):
        self.calls.append(name)
        if name == self.fail_at:
            raise RuntimeError("recovery failed")

    def apply_deletion_ledger(self):
        self.record("deletions")

    def expire_private_data(self, now_ms):
        assert now_ms == 42
        self.record("expiry")

    def validate_key_material(self):
        self.record("keys")

    def interrupt_active_games(self, now_ms):
        assert now_ms == 42
        self.record("interrupt")

    def clean_orphan_assets(self):
        self.record("orphans")


@pytest.mark.parametrize("failure", [None, "deletions", "expiry", "keys", "interrupt", "orphans"])
def test_startup_is_ordered_and_fails_closed(db, failure):
    recovery = FakeRecovery(failure)
    app = Application(db, FakeClock(), recovery)
    if failure:
        with pytest.raises(RuntimeError):
            app.start()
        assert not app.ready
    else:
        app.start()
        assert app.ready
    expected = ["deletions", "expiry", "keys", "interrupt", "orphans"]
    count = expected.index(failure) + 1 if failure else 5
    assert recovery.calls == expected[:count]


def test_terminal_write_rolls_back_when_score_insert_fails(db):
    seed(db)
    with pytest.raises(sqlite3.IntegrityError):
        with transaction(db):
            db.execute("UPDATE games SET status='over', finished_at=1, end_reason='pack_cleared'")
            db.execute("INSERT INTO scores VALUES ('g','a','Alice',-1,1)")
    assert db.execute("SELECT status FROM games").fetchone()[0] == "active"
    assert db.execute("SELECT count(*) FROM scores").fetchone()[0] == 0


def test_known_history_upgrades_without_rewriting_data(db, tmp_path, monkeypatch):
    from importlib.resources import files

    from semaphore_hub.storage import database

    seed(db)
    for entry in files("semaphore_hub.migrations").iterdir():
        if entry.name.endswith(".sql"):
            (tmp_path / entry.name).write_bytes(entry.read_bytes())
    (tmp_path / "0003_probe.sql").write_text("CREATE TABLE upgrade_probe (id TEXT);\n")
    monkeypatch.setattr(database, "files", lambda _: tmp_path)
    assert migrate(db) == 3
    assert migrate(db) == 3
    assert db.execute("SELECT login_name FROM accounts").fetchone()[0] == "alice"


def test_ready_application_cannot_run_recovery_again(db):
    recovery = FakeRecovery()
    app = Application(db, FakeClock(), recovery)
    app.start()
    calls = list(recovery.calls)
    with pytest.raises(RuntimeError, match="serving traffic"):
        app.start()
    assert app.ready
    assert recovery.calls == calls


def test_v1_database_upgrades_to_v2_without_publishing_existing_content(tmp_path, monkeypatch):
    from importlib.resources import files

    from semaphore_hub.storage import database

    original = files("semaphore_hub.migrations").joinpath("0001_foundation.sql").read_bytes()
    (tmp_path / "0001_foundation.sql").write_bytes(original)
    with closing(connect(":memory:")) as db:
        with monkeypatch.context() as context:
            context.setattr(database, "files", lambda _: tmp_path)
            assert migrate(db) == 1
            seed(db)
        assert migrate(db) == 2
        assert db.execute("SELECT count(*) FROM games").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM published_versions").fetchone()[0] == 0
