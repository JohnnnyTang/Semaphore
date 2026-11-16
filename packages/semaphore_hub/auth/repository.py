"""Transaction-scoped SQLite accounts. Never commits or exposes tombstones."""

import sqlite3

from semaphore_hub.repositories import Account, Conflict, NotFound, Session


class SqliteAccounts:
    def __init__(self, connection):
        self.db = connection

    def create(self, account):
        try:
            self.db.execute(
                "INSERT INTO "
                "accounts(account_id,login_name,display_name,password_hash,"
                "is_operator,created_at) VALUES(?,?,?,?,?,?)",
                (
                    account.account_id,
                    account.login_name,
                    account.display_name,
                    account.password_hash,
                    account.is_operator,
                    account.created_at,
                ),
            )
        except sqlite3.IntegrityError as error:
            raise Conflict("login_conflict") from error

    def by_login(self, normalized_login):
        row = self.db.execute(
            "SELECT account_id,login_name,display_name,password_hash,is_operator,created_at "
            "FROM accounts WHERE login_name=? AND deleted_at IS NULL",
            (normalized_login,),
        ).fetchone()
        return Account(*row) if row else None

    def by_id(self, account_id):
        row = self.db.execute(
            "SELECT account_id,login_name,display_name,password_hash,is_operator,created_at "
            "FROM accounts WHERE account_id=? AND deleted_at IS NULL",
            (account_id,),
        ).fetchone()
        if not row:
            raise NotFound(account_id)
        return Account(*row)

    def issue_session(self, session):
        self.by_id(session.account_id)
        self.db.execute(
            "INSERT INTO sessions VALUES(?,?,?,?,?,?,?)",
            (
                session.session_id,
                session.account_id,
                session.token_digest,
                session.csrf_digest,
                session.created_at,
                session.last_seen_at,
                session.absolute_expires_at,
            ),
        )

    def session(self, token_digest, now_ms, idle_ms):
        row = self.db.execute(
            "SELECT s.* FROM sessions s JOIN accounts a USING(account_id) WHERE "
            "s.token_digest=? AND a.deleted_at IS NULL AND s.absolute_expires_at>? "
            "AND s.last_seen_at>?",
            (token_digest, now_ms, now_ms - idle_ms),
        ).fetchone()
        return Session(*row) if row else None

    def touch_session(self, session_id, now_ms):
        self.db.execute(
            "UPDATE sessions SET last_seen_at=max(last_seen_at,?) WHERE session_id=?",
            (now_ms, session_id),
        )

    def revoke_session(self, session_id):
        self.db.execute("DELETE FROM sessions WHERE session_id=?", (session_id,))

    def revoke_all(self, account_id):
        self.db.execute("DELETE FROM sessions WHERE account_id=?", (account_id,))

    def reset_password(self, account_id, password_hash):
        self.by_id(account_id)
        self.db.execute(
            "UPDATE accounts SET password_hash=? WHERE account_id=?", (password_hash, account_id)
        )
        self.revoke_all(account_id)
