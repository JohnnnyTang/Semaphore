"""Bounded local account service; caller supplies short committing transactions."""

import base64
import hashlib
import hmac
import secrets
import threading
from collections import deque
from contextlib import contextmanager

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError

from semaphore_hub import policy as p
from semaphore_hub.interfaces import Principal, SystemClock
from semaphore_hub.repositories import Account, Conflict, Session

from .repository import SqliteAccounts


class AuthError(Exception):
    def __init__(self, status, code, retry_after=None):
        super().__init__(code)
        self.status, self.code, self.retry_after = status, code, retry_after


def digest(value):
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def encoded(raw):
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def valid_token(value):
    if not isinstance(value, str) or len(value) != 43:
        return False
    try:
        raw = base64.b64decode(value + "=", altchars=b"-_", validate=True)
        return len(raw) == 32 and encoded(raw) == value
    except ValueError:
        return False


class Admission:
    def __init__(self):
        self.lock = threading.Lock()
        self.keys = {}
        self.workers = threading.BoundedSemaphore(p.PASSWORD_WORKERS)

    def attempt(self, login, peer, now):
        with self.lock:
            for key in list(self.keys):
                values = self.keys[key]
                while values and values[0] <= now - 60000:
                    values.popleft()
                if not values:
                    del self.keys[key]
            pairs = [
                (("login", login), p.LOGIN_ATTEMPTS_PER_MINUTE),
                (("peer", peer), p.SOURCE_ATTEMPTS_PER_MINUTE),
            ]
            if len(self.keys) + sum(key not in self.keys for key, _ in pairs) > p.THROTTLE_KEYS:
                raise AuthError(429, "rate_limited", 60)
            for key, limit in pairs:
                values = self.keys.get(key, ())
                if len(values) >= limit:
                    raise AuthError(
                        429, "rate_limited", max(1, (values[0] + 60000 - now + 999) // 1000)
                    )
            for key, _ in pairs:
                self.keys.setdefault(key, deque()).append(now)

    @contextmanager
    def work(self):
        if not self.workers.acquire(blocking=False):
            raise AuthError(429, "rate_limited", 1)
        try:
            yield
        finally:
            self.workers.release()


class AuthService:
    def __init__(self, transaction_factory, policy, csrf_key, clock=None):
        if not isinstance(csrf_key, bytes) or len(csrf_key) != 32:
            raise ValueError("external 32-byte CSRF key required")
        self.transactions = transaction_factory
        self.policy = policy
        self.key = csrf_key
        self.clock = clock or SystemClock()
        self.admission = Admission()
        self.hasher = PasswordHasher(
            time_cost=p.ARGON2_TIME_COST,
            memory_cost=p.ARGON2_MEMORY_KIB,
            parallelism=p.ARGON2_PARALLELISM,
            hash_len=32,
            salt_len=16,
            type=Type.ID,
        )
        self.dummy = self.hasher.hash(secrets.token_urlsafe(32))

    def csrf(self, token):
        return encoded(
            hmac.digest(self.key, b"semaphore-csrf-v1\0" + token.encode("ascii"), "sha256")
        )

    def envelope(self, account, session, token, now):
        return {
            "account": {"account_id": account.account_id, "display_name": account.display_name},
            "csrf_token": self.csrf(token),
            "absolute_expires_at": session.absolute_expires_at,
            "idle_expires_at": min(now + p.SESSION_IDLE_MS, session.absolute_expires_at),
        }

    def _issue(self, repo, account, prior, now):
        if valid_token(prior):
            previous = repo.session(digest(prior), now, p.SESSION_IDLE_MS)
            if previous:
                repo.revoke_session(previous.session_id)
        token = secrets.token_urlsafe(32)
        session = Session(
            secrets.token_hex(16),
            account.account_id,
            digest(token),
            digest(self.csrf(token)),
            now,
            now,
            now + p.SESSION_ABSOLUTE_MS,
        )
        repo.issue_session(session)
        return token, self.envelope(account, session, token, now)

    def credentials(self, login, password, peer, display_name=None, prior=None):
        signup = display_name is not None
        try:
            login = p.normalize_login(login)
            p.validate_password(password, registering=signup)
            if signup:
                display_name = p.normalize_display_name(display_name)
        except (ValueError, TypeError):
            raise AuthError(400, "invalid_request") from None
        if signup and not self.policy.signup_enabled:
            raise AuthError(403, "signup_disabled")
        self.admission.attempt(login, peer, self.clock.monotonic_ms())
        with self.admission.work():
            if signup:
                password_hash = self.hasher.hash(password)
                with self.transactions() as db:
                    repo = SqliteAccounts(db)
                    account = Account(
                        secrets.token_hex(16),
                        login,
                        display_name,
                        password_hash,
                        False,
                        self.clock.utc_ms(),
                    )
                    try:
                        repo.create(account)
                    except Conflict:
                        raise AuthError(409, "login_conflict") from None
                    result = self._issue(repo, account, prior, self.clock.utc_ms())
            else:
                with self.transactions() as db:
                    account = SqliteAccounts(db).by_login(login)
                try:
                    self.hasher.verify(account.password_hash if account else self.dummy, password)
                except (VerificationError, InvalidHashError):
                    raise AuthError(401, "invalid_credentials") from None
                if account is None:
                    raise AuthError(401, "invalid_credentials")
                with self.transactions() as db:
                    repo = SqliteAccounts(db)
                    current = repo.by_login(login)
                    if (
                        current is None
                        or current.password_hash != account.password_hash
                        or current.account_id != account.account_id
                    ):
                        raise AuthError(401, "invalid_credentials")
                    result = self._issue(repo, current, prior, self.clock.utc_ms())
        return result

    def _session(self, repo, token, now, csrf=None, mutation=False):
        if not valid_token(token):
            raise AuthError(401, "unauthenticated")
        session = repo.session(digest(token), now, p.SESSION_IDLE_MS)
        if not session:
            raise AuthError(401, "unauthenticated")
        if not hmac.compare_digest(session.csrf_digest, digest(self.csrf(token))):
            raise AuthError(401, "unauthenticated")
        if mutation and (
            not valid_token(csrf) or not hmac.compare_digest(session.csrf_digest, digest(csrf))
        ):
            raise AuthError(403, "csrf_invalid")
        return session, repo.by_id(session.account_id)

    def authenticate(self, token, csrf=None, mutation=False):
        now = self.clock.utc_ms()
        with self.transactions() as db:
            repo = SqliteAccounts(db)
            session, account = self._session(repo, token, now, csrf, mutation)
            repo.touch_session(session.session_id, now)
        return Principal(account.account_id, session.session_id, account.is_operator)

    def session(self, token):
        now = self.clock.utc_ms()
        with self.transactions() as db:
            repo = SqliteAccounts(db)
            session, account = self._session(repo, token, now)
            repo.touch_session(session.session_id, now)
            result = self.envelope(account, session, token, now)
        return result

    def logout(self, token, csrf):
        with self.transactions() as db:
            repo = SqliteAccounts(db)
            session, _ = self._session(repo, token, self.clock.utc_ms(), csrf, True)
            repo.revoke_session(session.session_id)

    def bootstrap(self, login, display_name, password):
        login = p.normalize_login(login)
        display_name = p.normalize_display_name(display_name)
        p.validate_password(password)
        with self.admission.work():
            hashed = self.hasher.hash(password)
        with self.transactions() as db:
            if db.execute(
                "SELECT 1 FROM accounts WHERE is_operator=1 AND deleted_at IS NULL"
            ).fetchone():
                raise Conflict("operator_exists")
            account = Account(
                secrets.token_hex(16), login, display_name, hashed, True, self.clock.utc_ms()
            )
            SqliteAccounts(db).create(account)
        return account.account_id

    def reset_password(self, account_id, password):
        p.validate_password(password)
        with self.admission.work():
            hashed = self.hasher.hash(password)
        with self.transactions() as db:
            SqliteAccounts(db).reset_password(account_id, hashed)

    def revoke_all(self, account_id):
        with self.transactions() as db:
            SqliteAccounts(db).revoke_all(account_id)
