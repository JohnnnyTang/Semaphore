"""Coordinator-owned durable runtime composition interfaces (W1)."""

import sqlite3
import time
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Principal:
    account_id: str
    session_id: str
    is_operator: bool = False


class Clock(Protocol):
    def utc_ms(self) -> int: ...
    def monotonic_ms(self) -> int: ...


class SystemClock:
    def utc_ms(self) -> int:
        return time.time_ns() // 1_000_000

    def monotonic_ms(self) -> int:
        return time.monotonic_ns() // 1_000_000


class GameLocks(Protocol):
    def hold(self, game_id: str) -> AbstractContextManager[None]: ...


class Recovery(Protocol):
    """All hooks complete before traffic. Failure leaves the service unavailable.

    Online maintenance must take the same GameLocks as live game mutations,
    then open a transaction. Never acquire a game lock while holding a DB write lock.
    """

    def apply_deletion_ledger(self) -> None: ...
    def expire_private_data(self, now_ms: int) -> None: ...
    def validate_key_material(self) -> None: ...
    def interrupt_active_games(self, now_ms: int) -> None: ...
    def clean_orphan_assets(self) -> None: ...


TransactionFactory = Callable[[], AbstractContextManager[sqlite3.Connection]]


@dataclass(frozen=True)
class InferenceRequest:
    game_id: str
    command_id: str
    normalized_clue: str
    fingerprint_hash: str
    deadline_monotonic_ms: int


@dataclass(frozen=True)
class InferenceCompletion:
    game_id: str
    command_id: str
    fingerprint_hash: str
    vector: tuple[float, ...] | None
    error: str | None = None


class Inference(Protocol):
    """Physical running + queued work is bounded; callbacks never own transactions.

    A successful submit reserves a physical slot. False means overloaded and no
    callback. Callbacks occur asynchronously, never inline inside submit. Cancel
    suppresses logical delivery, but may not free a still-running physical slot.
    The service rechecks deadline, pins and terminal state under its game lock.
    Completion delivery is not permission to score; late results are discarded.
    """

    def submit(
        self, request: InferenceRequest, complete: Callable[[InferenceCompletion], None]
    ) -> bool: ...
    def cancel(self, game_id: str, command_id: str) -> None: ...
    def close(self) -> None: ...


class CommandKeys(Protocol):
    """External operator key material; never return secrets to repositories.

    digest accepts restricted canonical bytes for the durable-command-v1 array.
    Unknown versions must fail, never generate a replacement key or plain hash.
    validate_versions checks the active key plus all unexpired persisted versions.
    """

    def active_version(self) -> str: ...
    def validate_versions(self, required: frozenset[str]) -> None: ...
    def digest(self, version: str, canonical_payload: bytes) -> str: ...


class GameLifecycle(Protocol):
    """E exports these hooks to F; implementations own the shared game lock.

    now_utc_ms is persistence/retention time. Implementations use their injected
    Clock.monotonic_ms() for due-work ordering; UTC is never reducer elapsed time.
    interrupt drains due work, atomically settles pending work with no score if
    still active, then returns. Terminal games are unchanged. forget cancels and
    drops in-memory private state only after durable erasure has committed.
    """

    def interrupt(self, game_id: str, now_utc_ms: int) -> None: ...
    def forget(self, game_id: str) -> None: ...
