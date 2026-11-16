"""Short explicit transactions and checksum-verified, atomic migrations.

Call migrate before constructing services. Connections belong to one thread;
repositories receive a transaction connection and must never commit it themselves.
"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from hashlib import sha256
from importlib.resources import files
from pathlib import Path


class MigrationError(RuntimeError):
    """Database history differs from the migrations shipped in this build."""


def connect(path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path, isolation_level=None, timeout=5.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


@contextmanager
def transaction(connection: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """The service owns the commit; nested transactions are programming errors."""
    if connection.in_transaction:
        raise RuntimeError("nested transaction is not supported")
    connection.execute("BEGIN IMMEDIATE")
    try:
        yield connection
        connection.commit()
    except BaseException:
        connection.rollback()
        raise


def _statements(script: str) -> Iterator[str]:
    # executescript() would implicitly commit, breaking atomic DDL + ledger writes.
    pending = ""
    for line in script.splitlines(keepends=True):
        pending += line
        if sqlite3.complete_statement(pending):
            yield pending
            pending = ""
    if pending.strip():
        raise MigrationError("incomplete migration statement")


def migrate(connection: sqlite3.Connection) -> int:
    """Upgrade an empty/known database atomically; reject edited or future history."""
    migrations = sorted(
        (entry.name, entry.read_bytes())
        for entry in files("semaphore_hub.migrations").iterdir()
        if entry.name.endswith(".sql")
    )
    expected = [(i, name, sha256(raw).hexdigest()) for i, (name, raw) in enumerate(migrations, 1)]
    if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        raise MigrationError("foreign keys must be enabled")
    with transaction(connection):
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        if tables and "schema_migrations" not in tables:
            raise MigrationError("unversioned database is not supported")
        connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "version INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, sha256 TEXT NOT NULL)"
        )
        applied = [
            tuple(row)
            for row in connection.execute(
                "SELECT version, name, sha256 FROM schema_migrations ORDER BY version"
            )
        ]
        if applied != expected[: len(applied)] or len(applied) > len(expected):
            raise MigrationError("unknown or modified migration history")
        for identity, (_, raw) in zip(
            expected[len(applied) :], migrations[len(applied) :], strict=True
        ):
            for statement in _statements(raw.decode("utf-8")):
                connection.execute(statement)
            connection.execute("INSERT INTO schema_migrations VALUES (?, ?, ?)", identity)
        if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise MigrationError("foreign key integrity check failed")
    return len(expected)
