"""Real transaction composition for integrated account, pack, game and maintenance adapters.

Call migrate/startup recovery before use. This module does not open a listener or
claim that the complete durable application is ready to serve traffic.
"""

from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path

from semaphore_hub.storage import connect, transaction


class FoundationDatabase:
    """Open a thread-owned connection for each short service transaction."""

    def __init__(self, path: str | Path):
        if str(path) == ":memory:":
            raise ValueError("foundation composition requires a persistent database path")
        self.path = Path(path).resolve()

    @contextmanager
    def transaction(self):
        with closing(connect(self.path)) as connection, transaction(connection):
            yield connection

    @contextmanager
    def unit_of_work(self) -> Iterator["FoundationRepositories"]:
        with self.transaction() as connection:
            yield FoundationRepositories(connection)


class FoundationRepositories:
    """Transaction-scoped real adapters; deliberately no fake W3 fallback."""

    def __init__(self, connection):
        from semaphore_hub.auth import SqliteAccounts
        from semaphore_hub.games import SQLiteGames
        from semaphore_hub.operations import SQLiteMaintenance
        from semaphore_hub.packs import SQLitePacks

        self.accounts = SqliteAccounts(connection)
        self.packs = SQLitePacks(connection)

        self.games = SQLiteGames(connection)
        self.maintenance = SQLiteMaintenance(connection)
