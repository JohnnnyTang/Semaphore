"""Initial coordinator-owned composition interfaces (W1, not yet frozen)."""

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
    def interrupt_active_games(self, now_ms: int) -> None: ...
    def clean_orphan_assets(self) -> None: ...


TransactionFactory = Callable[[], AbstractContextManager[sqlite3.Connection]]
