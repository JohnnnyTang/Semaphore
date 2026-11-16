"""Real E/F composition with synthetic inference, never model-quality evidence."""

from contextlib import closing

from semaphore_hub.application import Application
from semaphore_hub.foundation import FoundationDatabase
from semaphore_hub.games import GameService
from semaphore_hub.operations import EncryptedBackups, ExternalLedger, Operations
from semaphore_hub.packs import PackService
from semaphore_hub.runtime import StripedGameLocks
from semaphore_hub.runtime_testing import FakeClock, FakeCommandKeys, ManualInference
from semaphore_hub.storage import connect


def test_pending_clue_deletion_account_erasure_and_restore(setup, raw, measured, tmp_path):
    tx, packs = setup
    published = packs.install(
        raw,
        owner_id="owner",
        operator_id="admin",
        rights_reference="synthetic integration only",
        accept=True,
    )
    import json

    entries = [json.loads(item)["id"] for item in published.entries_json]
    artifact = packs.accept_casual_artifact(
        published.installation.pack_id,
        published.installation.version,
        operator_id="admin",
        initial_board=entries[:5],
        schedule=[],
    )
    clock, keys, locks = FakeClock(), FakeCommandKeys(), StripedGameLocks()
    inference = ManualInference()
    games = GameService(tx, inference, keys, locks, clock=clock)
    gid = games.create("owner", {"mode": "casual", "artifact_id": artifact.artifact_id})[
        "snapshot"
    ]["game_id"]
    command = {
        "command_id": "private-command",
        "expected_revision": 0,
        "clue": "synthetic association",
    }
    assert games.command("owner", gid, command)["receipt"]["outcome"] == "pending"
    ledger = ExternalLedger(tmp_path / "deletions.jsonl", b"l" * 32, create=True)
    backups = EncryptedBackups(tmp_path / "backups", b"b" * 32)
    ops = Operations(
        tx, locks, games, keys, ledger, packs.clean_orphan_assets, clock, backups.rotate
    )
    ops.delete_clues("owner")
    receipt = games.command("owner", gid, command)["receipt"]
    assert receipt["outcome"] == "game_over"
    with tx() as db:
        assert db.execute("SELECT raw_clue FROM clue_attempts").fetchone()[0] is None
        assert db.execute("SELECT count(*) FROM scores").fetchone()[0] == 0
    encrypted = backups.create(tmp_path / "packs.db", clock.utc_ms())
    ops.delete_account("owner")

    def recover(path):
        restored_tx = FoundationDatabase(path).transaction
        restored_packs = PackService(restored_tx, tmp_path / "assets", None)
        restored_games = GameService(restored_tx, ManualInference(), keys, locks, clock=clock)
        recovery = Operations(
            restored_tx,
            locks,
            restored_games,
            keys,
            ledger,
            restored_packs.clean_orphan_assets,
            clock,
        )
        with closing(connect(path)) as connection:
            app = Application(connection, clock, recovery)
            app.start()
            assert app.ready

    restored = backups.prepare_restore(encrypted, tmp_path / "restored.db", clock.utc_ms(), recover)
    with closing(connect(restored)) as db:
        assert db.execute("SELECT count(*) FROM commands").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM clue_attempts").fetchone()[0] == 0
        assert db.execute("SELECT player_id FROM games").fetchone()[0] is None
        assert (
            db.execute("SELECT deleted_at FROM accounts WHERE account_id='owner'").fetchone()[0]
            is not None
        )
        assert db.execute("SELECT count(*) FROM published_versions").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM scores").fetchone()[0] == 0
