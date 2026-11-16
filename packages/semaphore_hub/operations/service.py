"""Host-only recovery and maintenance; exceptions propagate and readiness stays closed."""

import uuid

from semaphore_hub.interfaces import SystemClock
from semaphore_hub.policy import BACKUP_RETENTION_MS, CLEANUP_INTERVAL_MS
from semaphore_hub.repositories import Deletion

from .repository import SQLiteMaintenance


class Operations:
    def __init__(
        self,
        transactions,
        locks,
        lifecycle,
        keys,
        ledger,
        clean_assets,
        clock=None,
        rotate_backups=None,
    ):
        self.transactions, self.locks, self.lifecycle = transactions, locks, lifecycle
        self.keys, self.ledger, self.clean_assets = keys, ledger, clean_assets
        self.clock = clock or SystemClock()
        self.last_cleanup = None
        self.rotate_backups = rotate_backups

    def _ids(self, account_id=None, active=False):
        with self.transactions() as db:
            clauses, values = [], []
            if account_id is not None:
                clauses.append("player_id=?")
                values.append(account_id)
            if active:
                clauses.append("status='active'")
            sql = "SELECT game_id FROM games" + (
                " WHERE " + " AND ".join(clauses) if clauses else ""
            )
            return tuple(r[0] for r in db.execute(sql + " ORDER BY game_id", values))

    def _apply(self, deletion):
        with self.transactions() as db:
            existing = db.execute(
                "SELECT * FROM deletion_ledger WHERE deletion_id=?", (deletion.deletion_id,)
            ).fetchone()
            if existing is not None:
                SQLiteMaintenance(db).record_deletion(deletion)
                return
        ids = self._ids(deletion.account_id)
        for game_id in ids:
            self.lifecycle.interrupt(game_id, self.clock.utc_ms())
        for game_id in ids:
            with self.locks.hold(game_id), self.transactions() as db:
                if deletion.scope == "account":
                    db.execute("DELETE FROM commands WHERE game_id=?", (game_id,))
                else:
                    db.execute(
                        "UPDATE clue_attempts SET raw_clue=NULL WHERE game_id=? AND received_at<=?",
                        (game_id, deletion.requested_at),
                    )
            self.lifecycle.forget(game_id)
        with self.transactions() as db:
            repo = SQLiteMaintenance(db)
            repo.record_deletion(deletion)
            if deletion.scope == "account":
                repo.erase_account(deletion.account_id, deletion.requested_at)

    def _delete(self, account_id, scope):
        now = self.clock.utc_ms()
        deletion = Deletion(uuid.uuid4().hex, account_id, scope, now, now + BACKUP_RETENTION_MS)
        # Host must serialize operations/backups with its exclusive process lock.
        # A crash after fsync but before SQL commit is repaired by replay at startup.
        self.ledger.append(deletion)
        self._apply(deletion)
        if scope == "account":
            self.clean_orphan_assets()
        return deletion

    def delete_clues(self, account_id):
        return self._delete(account_id, "clues")

    def delete_account(self, account_id):
        return self._delete(account_id, "account")

    def apply_deletion_ledger(self):
        for deletion in self.ledger.entries():
            self._apply(deletion)

    def expire_private_data(self, now_ms):
        for game_id in self._ids():
            with self.locks.hold(game_id), self.transactions() as db:
                SQLiteMaintenance(db).expire(now_ms, game_id)

    def validate_key_material(self):
        with self.transactions() as db:
            required = SQLiteMaintenance(db).required_hmac_keys(self.clock.utc_ms())
        self.keys.validate_versions(required | {self.keys.active_version()})

    def interrupt_active_games(self, now_ms):
        for game_id in self._ids(active=True):
            self.lifecycle.interrupt(game_id, now_ms)

    def clean_orphan_assets(self):
        self.clean_assets()

    def daily_cleanup(self):
        now = self.clock.utc_ms()
        if (
            self.last_cleanup is None
            or now < self.last_cleanup
            or now - self.last_cleanup >= CLEANUP_INTERVAL_MS
        ):
            self.expire_private_data(now)
            if self.rotate_backups is not None:
                self.rotate_backups(now)
            self.last_cleanup = now

    def read_clue(self, game_id, command_id):
        """Private host callback only; never bind this to an HTTP route."""
        with self.locks.hold(game_id), self.transactions() as db:
            return SQLiteMaintenance(db).read_clue(game_id, command_id, self.clock.utc_ms())
