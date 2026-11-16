"""Cross-domain real SQLite composition, distinct from W1 fake smoke tests."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing

import pytest

from semaphore_hub.foundation import FoundationDatabase
from semaphore_hub.repositories import Account, Installation, NotFound
from semaphore_hub.storage import connect, migrate


def test_foundation_domains_commit_and_rollback_together(tmp_path):
    path = tmp_path / "hub.db"
    with closing(connect(path)) as connection:
        migrate(connection)
    database = FoundationDatabase(path)
    with pytest.raises(RuntimeError, match="rollback"):
        with database.unit_of_work() as work:
            work.accounts.create(Account("owner", "owner", "Owner", "hash"))
            work.packs.reserve(Installation("install", "owner", "pack", "1", "digest"))
            raise RuntimeError("rollback")
    with database.unit_of_work() as work:
        with pytest.raises(NotFound):
            work.accounts.by_id("owner")
        work.accounts.create(Account("owner", "owner", "Owner", "hash"))
        work.packs.reserve(Installation("install", "owner", "pack", "1", "digest"))
    with FoundationDatabase(path).unit_of_work() as work:
        assert work.accounts.by_id("owner").login_name == "owner"
        assert (
            work.packs.reserve(Installation("retry", "owner", "pack", "1", "digest")).install_id
            == "install"
        )
        assert work.games.active_ids() == ()
        assert work.maintenance.required_hmac_keys(0) == frozenset()


def test_transactions_use_thread_owned_connections(tmp_path):
    path = tmp_path / "hub.db"
    with closing(connect(path)) as connection:
        migrate(connection)
    database = FoundationDatabase(path)

    def create(index):
        with database.unit_of_work() as work:
            work.accounts.create(Account(str(index), f"user{index}", "Player", "hash"))

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(create, range(4)))
    with database.unit_of_work() as work:
        assert all(work.accounts.by_id(str(index)) for index in range(4))
