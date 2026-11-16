import json
import threading
from contextlib import closing, contextmanager
from types import SimpleNamespace

import pytest
from cryptography.exceptions import InvalidTag

from semaphore_hub.application import Application
from semaphore_hub.foundation import FoundationDatabase
from semaphore_hub.operations import EncryptedBackups, ExternalLedger, Operations, SQLiteMaintenance
from semaphore_hub.policy import BACKUP_RETENTION_MS, RAW_RETENTION_MS, RECEIPT_RETENTION_MS
from semaphore_hub.repositories import Deletion, NotFound
from semaphore_hub.storage import connect, migrate


class Locks:
    def __init__(self):
        self.lock = threading.RLock()
        self.depth = 0

    @contextmanager
    def hold(self, game_id):
        with self.lock:
            assert self.depth == 0, "maintenance must never nest game locks"
            self.depth += 1
            try:
                yield
            finally:
                self.depth -= 1


class Keys:
    missing = False

    def active_version(self):
        return "k1"

    def validate_versions(self, required):
        assert "k1" in required
        if self.missing:
            raise ValueError("missing key")


class Lifecycle:
    def __init__(self, database, locks):
        self.database, self.locks = database, locks
        self.forgot = []

    def interrupt(self, game_id, now):
        with self.locks.hold(game_id), self.database.transaction() as db:
            active = db.execute("SELECT status FROM games WHERE game_id=?", (game_id,)).fetchone()
            if active[0] == "active":
                db.execute(
                    "UPDATE games SET "
                    "status='over',finished_at=?,end_reason='interrupted',"
                    "revision=revision+1 WHERE game_id=?",
                    (now, game_id),
                )
                db.execute(
                    "UPDATE commands SET state='final',receipt_json='{}' WHERE game_id=? "
                    "AND state='pending'",
                    (game_id,),
                )
                db.execute(
                    "UPDATE commands SET expires_at=? WHERE game_id=?",
                    (now + RECEIPT_RETENTION_MS, game_id),
                )

    def forget(self, game_id):
        self.forgot.append(game_id)


def populate(path):
    with closing(connect(path)) as db:
        migrate(db)
        db.execute("INSERT INTO accounts VALUES ('a','alice','Alice','hash',1,0,NULL)")
        db.execute("INSERT INTO sessions VALUES ('s','a','token','csrf',0,0,999999999999)")
        db.execute("INSERT INTO packs VALUES ('p','a',0,NULL)")
        db.execute("INSERT INTO pack_versions VALUES ('v','p','1',X'00','m','s','v',0)")
        db.execute(
            "INSERT INTO verification_reports VALUES ('r','v','m','s','f','p','rules',1,1,'{}',0)"
        )
        db.execute("INSERT INTO published_versions VALUES ('v','r','a','authored',0)")
        db.execute(
            "INSERT INTO games VALUES ('g','a','v','casual','f','{}','r','c','{}',"
            "'art',NULL,0,'active',0,NULL,NULL,'{}')"
        )
        db.execute("INSERT INTO commands VALUES ('g','c','hmac','k1',0,'pending','{}',NULL)")
        db.execute(
            "INSERT INTO clue_attempts VALUES ('g','c','synthetic test clue','entry',"
            "0,NULL,NULL,NULL)"
        )


@pytest.fixture
def env(tmp_path):
    path = tmp_path / "hub.db"
    populate(path)
    database = FoundationDatabase(path)
    locks, keys = Locks(), Keys()
    clock = SimpleNamespace(utc_ms=lambda: 100, monotonic_ms=lambda: 5)
    ledger = ExternalLedger(tmp_path / "deletions.ledger", b"l" * 32, create=True)
    lifecycle = Lifecycle(database, locks)
    operations = Operations(
        database.transaction, locks, lifecycle, keys, ledger, lambda: None, clock
    )
    return SimpleNamespace(
        path=path,
        db=database,
        locks=locks,
        keys=keys,
        clock=clock,
        ledger=ledger,
        lifecycle=lifecycle,
        ops=operations,
    )


def test_exact_raw_deadline_and_receipt_expiry(env):
    with env.db.transaction() as db:
        repo = SQLiteMaintenance(db)
        assert repo.read_clue("g", "c", RAW_RETENTION_MS - 1)
        with pytest.raises(NotFound):
            repo.read_clue("g", "c", RAW_RETENTION_MS)
        repo.expire(RAW_RETENTION_MS)
        assert db.execute("SELECT raw_clue FROM clue_attempts").fetchone()[0] is None
        assert db.execute("SELECT payload_hmac FROM commands").fetchone()[0] == "hmac"
    env.lifecycle.interrupt("g", 100)
    env.ops.expire_private_data(100 + RECEIPT_RETENTION_MS - 1)
    with env.db.transaction() as db:
        assert db.execute("SELECT count(*) FROM commands").fetchone()[0] == 1
    env.ops.expire_private_data(100 + RECEIPT_RETENTION_MS)
    with env.db.transaction() as db:
        assert db.execute("SELECT count(*) FROM commands").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM clue_attempts").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM games").fetchone()[0] == 1


def test_account_erasure_tombstones_retains_shared_content(env):
    deletion = env.ops.delete_account("a")
    assert env.ledger.entries() == (deletion,)
    with env.db.transaction() as db:
        account = db.execute("SELECT * FROM accounts").fetchone()
        assert account["password_hash"] is None and account["deleted_at"] == 100
        assert db.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM commands").fetchone()[0] == 0
        assert db.execute("SELECT player_id FROM games").fetchone()[0] is None
        assert db.execute("SELECT count(*) FROM published_versions").fetchone()[0] == 1
        assert db.execute("SELECT owner_id,retired_at FROM packs").fetchone()[:] == ("a", 100)
        assert db.execute("SELECT count(*) FROM scores").fetchone()[0] == 0
    assert env.lifecycle.forgot == ["g"]
    env.ops.apply_deletion_ledger()
    assert env.lifecycle.forgot == ["g"]


def test_clue_delete_preserves_retry_and_replay_after_crash(env):
    deletion = Deletion("d", "a", "clues", 100, 100 + BACKUP_RETENTION_MS)
    env.ledger.append(deletion)  # simulated crash before SQL deletion
    env.ops.apply_deletion_ledger()
    with env.db.transaction() as db:
        assert db.execute("SELECT raw_clue FROM clue_attempts").fetchone()[0] is None
        assert db.execute("SELECT payload_hmac FROM commands").fetchone()[0] == "hmac"
        assert db.execute("SELECT login_name FROM accounts").fetchone()[0] == "alice"
        assert db.execute("SELECT end_reason FROM games").fetchone()[0] == "interrupted"


def test_ledger_fail_closed_and_missing_key(env, monkeypatch):
    monkeypatch.setattr(env.ledger, "append", lambda d: (_ for _ in ()).throw(OSError("disk full")))
    with pytest.raises(OSError):
        env.ops.delete_account("a")
    with env.db.transaction() as db:
        assert db.execute("SELECT deleted_at FROM accounts").fetchone()[0] is None
    env.keys.missing = True
    with closing(connect(env.path)) as db:
        app = Application(db, env.clock, env.ops)
        with pytest.raises(ValueError, match="missing key"):
            app.start()
        assert not app.ready


def test_ledger_authentication(env):
    env.ops.delete_clues("a")
    raw = env.ledger.path.read_bytes()
    env.ledger.path.write_bytes(raw.replace(b'"clues"', b'"account"'))
    with pytest.raises(ValueError, match="authentication"):
        env.ops.apply_deletion_ledger()


def test_backup_restore_replays_external_deletion_and_recovers(env, tmp_path):
    backups = EncryptedBackups(tmp_path / "backups", b"b" * 32)
    backup = backups.create(env.path, 0)
    assert b"synthetic test clue" not in backup.read_bytes()
    env.ops.delete_account("a")

    def recover(path):
        database = FoundationDatabase(path)
        operations = Operations(
            database.transaction,
            env.locks,
            Lifecycle(database, env.locks),
            env.keys,
            env.ledger,
            lambda: None,
            env.clock,
        )
        with closing(connect(path)) as db:
            app = Application(db, env.clock, operations)
            app.start()
            assert app.ready

    restored = backups.prepare_restore(backup, tmp_path / "restored.db", 100, recover)
    with closing(connect(restored)) as db:
        assert db.execute("SELECT deleted_at FROM accounts").fetchone()[0] == 100
        assert db.execute("SELECT count(*) FROM commands").fetchone()[0] == 0
        assert db.execute("SELECT status,end_reason FROM games").fetchone()[:] == (
            "over",
            "interrupted",
        )
    with pytest.raises(ValueError, match="expired"):
        backups.prepare_restore(backup, tmp_path / "expired.db", BACKUP_RETENTION_MS, recover)
    backups.rotate(BACKUP_RETENTION_MS)
    assert not backup.exists()


def test_backup_tamper_wrong_key_and_failed_recovery(env, tmp_path):
    backups = EncryptedBackups(tmp_path / "backups", b"b" * 32)
    backup = backups.create(env.path, 0)
    wrong = EncryptedBackups(tmp_path / "backups", b"x" * 32)
    with pytest.raises(InvalidTag):
        wrong.prepare_restore(backup, tmp_path / "wrong.db", 1, lambda _: None)

    def failed(_):
        raise RuntimeError("recovery failed")

    with pytest.raises(RuntimeError):
        backups.prepare_restore(backup, tmp_path / "failed.db", 1, failed)
    assert not (tmp_path / "failed.db").exists()
    assert not list(tmp_path.glob("*.restoring"))
    envelope = json.loads(backup.read_bytes())
    envelope["header"]["created_at"] = 1
    backup.write_text(json.dumps(envelope))
    with pytest.raises(InvalidTag):
        backups.rotate(BACKUP_RETENTION_MS)


def test_cleanup_failure_not_marked_success(env, monkeypatch):
    monkeypatch.setattr(
        env.ops, "expire_private_data", lambda _: (_ for _ in ()).throw(OSError("busy"))
    )
    with pytest.raises(OSError):
        env.ops.daily_cleanup()
    assert env.ops.last_cleanup is None


def test_private_assets_removed_shared_cache_retained_and_cleanup_called(env):
    cleaned = []
    env.ops.clean_assets = lambda: cleaned.append(True)
    with env.db.transaction() as db:
        db.execute("INSERT INTO pack_versions VALUES ('private','p','2',X'01','m2','s2','v2',0)")
        db.execute("INSERT INTO pack_entries VALUES ('private',0,'x','{}')")
        db.execute(
            "INSERT INTO verification_reports VALUES "
            "('private-report','private','m2','s2','f','p','rules',0,0,'{}',0)"
        )
        db.execute("INSERT INTO vector_caches VALUES ('v2','f','digest','private-path',2560,40)")
        db.execute("INSERT INTO vector_caches VALUES ('v','f','digest2','public-path',2560,40)")
        db.execute("UPDATE games SET status='over',finished_at=50,end_reason='pack_cleared'")
        db.execute("INSERT INTO scores VALUES ('g','a','Alice',0,50)")
    env.ops.delete_account("a")
    with env.db.transaction() as db:
        assert (
            db.execute("SELECT count(*) FROM pack_versions WHERE version_id='private'").fetchone()[
                0
            ]
            == 0
        )
        assert db.execute("SELECT vector_hash FROM vector_caches").fetchone()[0] == "v"
        assert db.execute("SELECT player_id,display_name,score FROM scores").fetchone()[:] == (
            None,
            None,
            0,
        )
        assert db.execute("SELECT count(*) FROM published_versions").fetchone()[0] == 1
    assert cleaned == [True]


def test_backup_rotation_failure_keeps_cleanup_retryable(env):
    env.ops.rotate_backups = lambda _: (_ for _ in ()).throw(OSError("backup disk unavailable"))
    with pytest.raises(OSError):
        env.ops.daily_cleanup()
    assert env.ops.last_cleanup is None


def test_account_race_fails_without_tombstone(env, monkeypatch):
    from semaphore_hub.repositories import Conflict

    monkeypatch.setattr(env.lifecycle, "interrupt", lambda *args: None)
    with pytest.raises(Conflict, match="interrupt"):
        env.ops.delete_account("a")
    with env.db.transaction() as db:
        assert db.execute("SELECT deleted_at FROM accounts").fetchone()[0] is None
    assert len(env.ledger.entries()) == 1


def test_restore_failure_removes_plaintext_sidecars(env, tmp_path):
    backups = EncryptedBackups(tmp_path / "backups", b"b" * 32)
    backup = backups.create(env.path, 0)

    def failed(path):
        with closing(connect(path)) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("UPDATE accounts SET display_name='changed'")
        # Simulate journal remnants after a failed/crashed recovery callback.
        from pathlib import Path

        for suffix in ("-wal", "-shm", "-journal"):
            Path(str(path) + suffix).write_bytes(b"synthetic private material")
        raise RuntimeError("recovery failed")

    with pytest.raises(RuntimeError):
        backups.prepare_restore(backup, tmp_path / "failed.db", 1, failed)
    assert not list(tmp_path.glob("*.restoring*"))
