"""Fail-closed startup composition; this skeleton does not expose HTTP routes."""

import sqlite3
from dataclasses import dataclass, field

from .interfaces import Clock, Recovery
from .storage import migrate


@dataclass
class Application:
    connection: sqlite3.Connection
    clock: Clock
    recovery: Recovery
    ready: bool = field(default=False, init=False)

    def start(self) -> None:
        self.ready = False
        migrate(self.connection)
        now = self.clock.utc_ms()
        self.recovery.apply_deletion_ledger()
        self.recovery.expire_private_data(now)
        self.recovery.interrupt_active_games(now)
        self.recovery.clean_orphan_assets()
        self.ready = True
