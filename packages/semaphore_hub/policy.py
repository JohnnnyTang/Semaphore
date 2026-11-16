"""Frozen W1 policy values and pure configuration/input validation.

These helpers are not authentication, rate limiting or an HTTP middleware.
"""

import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import urlsplit

DAY_MS = 86_400_000
SESSION_ABSOLUTE_MS = DAY_MS
SESSION_IDLE_MS = 8 * 60 * 60 * 1000
TOKEN_BYTES = 32
PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 128
LOGIN_ATTEMPTS_PER_MINUTE = 5
SOURCE_ATTEMPTS_PER_MINUTE = 20
THROTTLE_KEYS = 4096
PASSWORD_WORKERS = 2
ARGON2_MEMORY_KIB = 65536
ARGON2_TIME_COST = 3
ARGON2_PARALLELISM = 1
REQUEST_MAX_BYTES = 16384
MAX_ACTIVE_GAMES = 64
MAX_ACTIVE_GAMES_PER_ACCOUNT = 1
MAX_COMMANDS_PER_GAME = 4096
MAX_GAME_DURATION_MS = 600000
MAX_OUTSTANDING_INFERENCES = 8
INFERENCE_DEADLINE_MS = 5000
RAW_RETENTION_MS = 30 * DAY_MS
RECEIPT_RETENTION_MS = 90 * DAY_MS
BACKUP_RETENTION_MS = 30 * DAY_MS
CLEANUP_INTERVAL_MS = DAY_MS
INSTALL_MAX_BYTES = 8 * 1024 * 1024
INSTALL_MAX_ENTRIES = 500
INSTALL_MAX_CLUES = 2500
INSTALL_DEADLINE_MS = 600000
INSTALL_WORKERS = 1
PAGE_MAX_ITEMS = 100
CURSOR_MAX_LENGTH = 200
SESSION_COOKIE = "semaphore_session"


def normalize_login(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_]{3,32}", value):
        raise ValueError("invalid_login")
    return value.lower()


def normalize_display_name(value: str) -> str:
    if not 1 <= len(value) <= 64:
        raise ValueError("invalid_display_name")
    normalized = " ".join(unicodedata.normalize("NFKC", value).split())
    if not 1 <= len(normalized) <= 64 or any(
        unicodedata.category(char).startswith("C") for char in normalized
    ):
        raise ValueError("invalid_display_name")
    return normalized


def validate_password(value: str, *, registering: bool = True) -> str:
    minimum = PASSWORD_MIN_LENGTH if registering else 1
    if not minimum <= len(value) <= PASSWORD_MAX_LENGTH or any(
        0xD800 <= ord(char) <= 0xDFFF for char in value
    ):
        raise ValueError("invalid_password")
    # Never trim, normalize or casefold secrets.
    return value


@dataclass(frozen=True)
class TransportPolicy:
    """Exact single-origin deployment; browser request headers are compared literally.

    Multiple entry points need separate explicit policies, not wildcard hosts.
    Network exposure remains an operator/firewall responsibility.
    """

    origin: str
    signup_enabled: bool = True

    def __post_init__(self) -> None:
        parsed = urlsplit(self.origin)
        try:
            port = parsed.port
        except ValueError as error:
            raise ValueError("invalid_origin") from error
        if (
            port == 0
            or parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or not self.origin.isascii()
            or "\\" in self.origin
            or parsed.netloc.endswith(":")
            or (
                parsed.port is not None
                and (
                    str(parsed.port) != parsed.netloc.rsplit(":", 1)[1]
                    or (parsed.scheme, parsed.port) in {("http", 80), ("https", 443)}
                )
            )
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path
            or parsed.query
            or parsed.fragment
            or any(char.isspace() or ord(char) < 33 for char in self.origin)
            or "*" in self.origin
            or parsed.netloc != parsed.netloc.lower()
            or self.origin != f"{parsed.scheme}://{parsed.netloc}"
        ):
            raise ValueError("invalid_origin")

    @property
    def host(self) -> str:
        return urlsplit(self.origin).netloc

    @property
    def secure_cookie(self) -> bool:
        return urlsplit(self.origin).scheme == "https"

    def accepts(self, *, host: str, origin: str | None, mutation: bool) -> bool:
        return host == self.host and (
            origin == self.origin if mutation or origin is not None else True
        )
