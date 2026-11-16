"""Concrete durable host. Caller holds exclusive_host for its entire lifetime."""

import threading
from contextlib import closing
from pathlib import Path

from semaphore_hub.application import Application
from semaphore_hub.durable_http import DurableHttp
from semaphore_hub.games import GameService
from semaphore_hub.host import FoundationServer, prepare
from semaphore_hub.http import error
from semaphore_hub.interfaces import SystemClock
from semaphore_hub.operations import EncryptedBackups, ExternalLedger, Operations, validate_assets
from semaphore_hub.policy import CLEANUP_INTERVAL_MS
from semaphore_hub.results import ResultsService
from semaphore_hub.runtime import FileCommandKeys, QueuedInference, StripedGameLocks
from semaphore_hub.storage import connect


class OfflineInference:
    """Operator recovery cancels pending work; it never admits new inference."""

    def submit(self, request, complete):
        return False

    def cancel(self, game_id, command_id):
        pass

    def close(self, *, wait=False):
        pass


class DurableServer(FoundationServer):
    # Finish request threads before relinquishing the exclusive process lock.
    daemon_threads = False


class DurableHost:
    def __init__(
        self,
        database,
        assets,
        policy,
        csrf_key,
        command_keys,
        ledger_path,
        ledger_key,
        backup_root,
        backup_key,
        *,
        embedder=None,
        clock=None,
        web_root=None,
    ):
        self.database, self.assets = Path(database), Path(assets)
        self.browser = None
        if web_root is not None:
            from semaphore_hub.browser_assets import BrowserAssets

            self.browser = BrowserAssets(web_root)
        self.clock = clock or SystemClock()
        self.guard = threading.RLock()
        self.ready = False
        self.embedder = embedder
        self.keys = FileCommandKeys(command_keys)
        self.ledger = ExternalLedger(ledger_path, Path(ledger_key).read_bytes())
        self.backups = EncryptedBackups(backup_root, Path(backup_key).read_bytes())
        self.auth, self.packs = prepare(database, assets, policy, csrf_key)
        self.transactions = self.auth.transactions
        self.inference = (
            QueuedInference(embedder, clock=self.clock) if embedder else OfflineInference()
        )
        self.locks = StripedGameLocks()
        self.games = GameService(
            self.transactions, self.inference, self.keys, self.locks, clock=self.clock
        )
        self.operations = Operations(
            self.transactions,
            self.locks,
            self.games,
            self.keys,
            self.ledger,
            self.clean_assets,
            self.clock,
            self.backups.rotate,
        )
        self.dispatcher = DurableHttp(
            self.auth, self.packs, self.games, ResultsService(self.transactions)
        )
        self.last_backup = None

    def validate_assets(self, connection):
        return validate_assets(connection, self.assets)

    def validate_backups(self):
        self.backups.validate_restorable(self.clock.utc_ms(), self.keys, self.validate_assets)

    def clean_assets(self):
        # Retained snapshots may reference assets absent from the current DB.
        # Defer orphan removal until their encrypted retention window ends.
        self.backups.rotate(self.clock.utc_ms())
        if not any(self.backups.root.glob("*.backup")):
            self.packs.clean_orphan_assets()

    def start(self):
        with self.guard:
            self.ready = False
            self.validate_backups()
            with closing(connect(self.database)) as db:
                Application(db, self.clock, self.operations).start()
                self.validate_assets(db)
            self.ready = True

    def handle(self, *args, **kwargs):
        with self.guard:
            if not self.ready:
                return error(503, "unavailable")
            if self.browser is not None:
                response = self.browser.handle(self.dispatcher, *args, **kwargs)
                if response is not None:
                    return response
            return self.dispatcher.handle(*args, **kwargs)

    def backup(self):
        with self.guard:
            self.validate_backups()
            with closing(connect(self.database)) as db:
                self.validate_assets(db)
            self.operations.validate_key_material()
            result = self.backups.create(self.database, self.clock.utc_ms())
            self.last_backup = self.clock.utc_ms()
            return result

    def maintenance(self):
        with self.guard:
            if not self.ready:
                raise RuntimeError("durable host not ready")
            try:
                self.games.tick()
                self.operations.daily_cleanup()
                now = self.clock.utc_ms()
                if (
                    self.last_backup is None
                    or now < self.last_backup
                    or now - self.last_backup >= CLEANUP_INTERVAL_MS
                ):
                    self.backup()
            except BaseException:
                self.ready = False
                raise

    def restore(self, backup, destination):
        from semaphore_hub.foundation import FoundationDatabase

        def recover(path):
            tx = FoundationDatabase(path).transaction
            games = GameService(tx, OfflineInference(), self.keys, self.locks, clock=self.clock)
            operations = Operations(
                tx, self.locks, games, self.keys, self.ledger, lambda: None, self.clock
            )
            with closing(connect(path)) as db:
                Application(db, self.clock, operations).start()
                self.validate_assets(db)

        with self.guard:
            self.validate_backups()
            return self.backups.prepare_restore(backup, destination, self.clock.utc_ms(), recover)

    def serve(self, port):
        if self.embedder is None:
            raise RuntimeError("durable serving requires a pinned model provider")
        self.embedder.identity()
        self.start()
        self.maintenance()
        # handle_request returns at least every 100 ms, so maintenance errors propagate
        # to the operator and close the listener instead of silently losing a thread.
        with DurableServer(("127.0.0.1", port), self) as server:
            server.timeout = 0.1
            try:
                while self.ready:
                    server.handle_request()
                    with self.guard:
                        if self.ready:
                            self.maintenance()
            finally:
                self.close()

    def close(self):
        with self.guard:
            self.ready = False
            self.inference.close(wait=True)
