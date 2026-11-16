"""Transaction-scoped privacy maintenance; callers own locks and commits."""

from semaphore_hub.policy import RAW_RETENTION_MS
from semaphore_hub.repositories import Conflict, Deletion, NotFound


class SQLiteMaintenance:
    def __init__(self, connection):
        self.db = connection

    def record_deletion(self, deletion):
        old = self.db.execute(
            "SELECT * FROM deletion_ledger WHERE deletion_id=?", (deletion.deletion_id,)
        ).fetchone()
        values = (
            deletion.deletion_id,
            deletion.account_id,
            deletion.scope,
            deletion.requested_at,
            deletion.retain_until,
        )
        if old is not None and tuple(old) != values:
            raise Conflict("deletion identity conflict")
        self.db.execute("INSERT OR IGNORE INTO deletion_ledger VALUES(?,?,?,?,?)", values)

    def deletions(self):
        return tuple(
            Deletion(*r)
            for r in self.db.execute(
                "SELECT * FROM deletion_ledger ORDER BY requested_at,deletion_id"
            )
        )

    def erase_clues(self, account_id, through_ms):
        self.db.execute(
            "UPDATE clue_attempts SET raw_clue=NULL WHERE received_at<=? AND game_id IN "
            "(SELECT game_id FROM games WHERE player_id=?)",
            (through_ms, account_id),
        )

    def erase_account(self, account_id, now_ms):
        if self.db.execute(
            "SELECT 1 FROM games WHERE player_id=? AND status='active'", (account_id,)
        ).fetchone():
            raise Conflict("interrupt active games before erasure")
        private_versions = self.db.execute(
            "SELECT v.version_id,v.vector_hash FROM pack_versions v JOIN packs p USING(pack_id) "
            "LEFT JOIN published_versions u USING(version_id) "
            "WHERE p.owner_id=? AND u.version_id IS NULL",
            (account_id,),
        ).fetchall()
        for version_id, vector_hash in private_versions:
            if self.db.execute("SELECT 1 FROM games WHERE version_id=?", (version_id,)).fetchone():
                raise Conflict("unpublished version referenced by game")
            self.db.execute("DELETE FROM pack_entries WHERE version_id=?", (version_id,))
            self.db.execute("DELETE FROM verification_reports WHERE version_id=?", (version_id,))
            self.db.execute("DELETE FROM pack_versions WHERE version_id=?", (version_id,))
            self.db.execute(
                "DELETE FROM vector_caches WHERE vector_hash=? AND NOT EXISTS "
                "(SELECT 1 FROM pack_versions WHERE vector_hash=?)",
                (vector_hash, vector_hash),
            )
        self.db.execute("DELETE FROM sessions WHERE account_id=?", (account_id,))
        self.db.execute(
            "DELETE FROM commands WHERE game_id IN (SELECT game_id FROM games WHERE player_id=?)",
            (account_id,),
        )
        self.db.execute(
            "UPDATE scores SET player_id=NULL,display_name=NULL WHERE player_id=?", (account_id,)
        )
        self.db.execute("UPDATE games SET player_id=NULL WHERE player_id=?", (account_id,))
        self.db.execute(
            "UPDATE accounts SET "
            "login_name=NULL,display_name=NULL,password_hash=NULL,is_operator=0,"
            "deleted_at=COALESCE(deleted_at,?) WHERE account_id=?",
            (now_ms, account_id),
        )
        self.db.execute(
            "UPDATE packs SET retired_at=COALESCE(retired_at,?) WHERE owner_id=?",
            (now_ms, account_id),
        )
        self.db.execute(
            "UPDATE install_reservations SET state='cancelled',finished_at=? WHERE "
            "state='pending' AND pack_id IN (SELECT pack_id FROM packs WHERE owner_id=?)",
            (now_ms, account_id),
        )

    def expire(self, now_ms, game_id=None):
        self.db.execute(
            "UPDATE clue_attempts SET raw_clue=NULL WHERE received_at<=? "
            "AND (? IS NULL OR game_id=?)",
            (now_ms - RAW_RETENTION_MS, game_id, game_id),
        )
        self.db.execute(
            "DELETE FROM commands WHERE expires_at<=? AND game_id IN (SELECT game_id FROM "
            "games WHERE status='over') AND (? IS NULL OR game_id=?)",
            (now_ms, game_id, game_id),
        )

    def required_hmac_keys(self, now_ms):
        return frozenset(
            r[0]
            for r in self.db.execute(
                "SELECT DISTINCT hmac_key_version FROM commands WHERE expires_at IS NULL "
                "OR expires_at>?",
                (now_ms,),
            )
        )

    def read_clue(self, game_id, command_id, now_ms):
        row = self.db.execute(
            "SELECT raw_clue FROM clue_attempts WHERE game_id=? AND command_id=? AND received_at>?",
            (game_id, command_id, now_ms - RAW_RETENTION_MS),
        ).fetchone()
        if row is None or row[0] is None:
            raise NotFound("clue unavailable")
        return row[0]
