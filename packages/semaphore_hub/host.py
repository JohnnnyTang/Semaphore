"""Bounded loopback host for W2 account/pack services.

This listener refuses game-bearing databases until W3 recovery is composed.
"""

import json
import os
import threading
from contextlib import ExitStack, closing, contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from socketserver import ThreadingMixIn

from semaphore_hub.auth import AuthService
from semaphore_hub.foundation import FoundationDatabase
from semaphore_hub.http import FoundationHttp, error
from semaphore_hub.packs import PackService
from semaphore_hub.policy import REQUEST_MAX_BYTES
from semaphore_hub.storage import connect, migrate


def prepare(database, assets, policy, key_path, embedder=None):
    key = Path(key_path).read_bytes()
    if len(key) != 32:
        raise ValueError("external CSRF key must contain exactly 32 bytes")
    with closing(connect(database)) as db:
        migrate(db)
    transactions = FoundationDatabase(database).transaction
    auth = AuthService(transactions, policy, key)
    packs = PackService(transactions, assets, embedder)
    return auth, packs


def foundation_ready(auth, packs):
    # No game/private-data recovery implementation is hidden behind a no-op.
    with auth.transactions() as db:
        if db.execute("SELECT 1 FROM games LIMIT 1").fetchone():
            raise RuntimeError("W3 recovery required for game-bearing database")
        if db.execute("SELECT 1 FROM accounts WHERE deleted_at IS NOT NULL LIMIT 1").fetchone():
            raise RuntimeError("W3 deletion-ledger recovery required")
    packs.clean_orphan_assets()


class FoundationServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    request_queue_size = 16
    allow_reuse_address = False

    def __init__(self, address, dispatcher, *, workers=8):
        if address[0] != "127.0.0.1":
            raise ValueError("foundation host binds IPv4 loopback only")
        self.dispatcher = dispatcher
        self.slots = threading.BoundedSemaphore(workers)
        super().__init__(address, FoundationHandler)

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()

    def handle_error(self, request, client_address):
        # Deliberately never print bodies, credential-bearing headers or exceptions.
        pass


class FoundationHandler(BaseHTTPRequestHandler):
    server_version = "Semaphore"
    sys_version = ""
    protocol_version = "HTTP/1.0"

    def setup(self):
        self.request.settimeout(5)
        super().setup()

    def log_message(self, format, *args):
        pass

    def _response(self, response):
        raw = b"" if response.body is None else json.dumps(response.body).encode()
        self.send_response(response.status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Connection", "close")
        self.send_header("X-Content-Type-Options", "nosniff")
        for key, value in response.headers.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(raw)
        self.close_connection = True

    def _dispatch(self):
        lengths = self.headers.get_all("Content-Length", [])
        if self.headers.get_all("Transfer-Encoding") or len(lengths) > 1:
            return self._response(error(400, "invalid_request"))
        length = lengths[0] if lengths else "0"
        if not length.isascii() or not length.isdecimal() or len(length) > 8:
            return self._response(error(400, "invalid_request"))
        length = int(length)
        if length > REQUEST_MAX_BYTES:
            return self._response(error(413, "body_too_large"))
        try:
            body = self.rfile.read(length)
            if len(body) != length:
                return self._response(error(400, "invalid_request"))
            response = self.server.dispatcher.handle(
                self.command,
                self.path,
                list(self.headers.raw_items()),
                body,
                self.client_address[0],
            )
        except TimeoutError:
            response = error(408, "request_timeout")
        except Exception:
            response = error(503, "unavailable")
        self._response(response)

    do_GET = _dispatch
    do_POST = _dispatch
    do_DELETE = _dispatch
    do_PUT = _dispatch
    do_PATCH = _dispatch


def serve(auth, packs, port):
    foundation_ready(auth, packs)
    with FoundationServer(("127.0.0.1", port), FoundationHttp(auth, packs)) as server:
        server.serve_forever()


@contextmanager
def exclusive_host(database, assets=None):
    with ExitStack() as stack:
        stack.enter_context(_exclusive_file(database))
        if assets is not None:
            root = Path(assets).resolve()
            root.mkdir(parents=True, exist_ok=True)
            stack.enter_context(_exclusive_file(root / "assets"))
        yield


@contextmanager
def _exclusive_file(database):
    """One listener or operator process per database, including recovery/install.

    Keep the stable lock file: unlinking it permits inode replacement races.
    OS locks release automatically after process death.
    """
    path = Path(database).resolve().with_suffix(Path(database).suffix + ".host.lock")
    with path.open("a+b") as lock:
        if lock.tell() == 0:
            lock.write(b"0")
            lock.flush()
        lock.seek(0)
        if os.name == "nt":
            import msvcrt

            try:
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                raise RuntimeError("hub host is busy") from None
            try:
                yield
            finally:
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                raise RuntimeError("hub host is busy") from None
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)
