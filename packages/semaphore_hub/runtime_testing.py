"""Deterministic W1 composition fakes. Never wire these into a real HTTP server."""

import hashlib
import hmac
from collections.abc import Callable, Iterator
from contextlib import contextmanager

from .interfaces import InferenceCompletion, InferenceRequest


class FakeClock:
    def utc_ms(self) -> int:
        return 1_800_000_000_000

    def monotonic_ms(self) -> int:
        return 10_000


class FakeGameLocks:
    def __init__(self) -> None:
        self.held: set[str] = set()

    @contextmanager
    def hold(self, game_id: str) -> Iterator[None]:
        if game_id in self.held:
            raise RuntimeError("fake game lock already held")
        self.held.add(game_id)
        try:
            yield
        finally:
            self.held.remove(game_id)


class FakeCommandKeys:
    """Public synthetic key, only for deterministic boundary tests."""

    def active_version(self) -> str:
        return "fixture-key-v1"

    def validate_versions(self, required: frozenset[str]) -> None:
        if required - {self.active_version()}:
            raise ValueError("missing key version")

    def digest(self, version: str, canonical_payload: bytes) -> str:
        self.validate_versions(frozenset({version}))
        return hmac.new(
            b"public-fixture-key-not-for-deployment", canonical_payload, hashlib.sha256
        ).hexdigest()


class ManualInference:
    """No model, threads or timing evidence. The test drives physical completion."""

    def __init__(self, capacity: int = 8) -> None:
        self.capacity = capacity
        self.pending: dict[
            tuple[str, str], tuple[InferenceRequest, Callable[[InferenceCompletion], None]]
        ] = {}
        self.cancelled: set[tuple[str, str]] = set()
        self.closed = False

    def submit(
        self, request: InferenceRequest, complete: Callable[[InferenceCompletion], None]
    ) -> bool:
        key = (request.game_id, request.command_id)
        if self.closed or key in self.pending or len(self.pending) >= self.capacity:
            return False
        self.pending[key] = (request, complete)
        return True

    def cancel(self, game_id: str, command_id: str) -> None:
        key = (game_id, command_id)
        if key in self.pending:
            self.cancelled.add(key)

    def finish(self, game_id: str, command_id: str, vector: tuple[float, ...]) -> None:
        key = (game_id, command_id)
        request, callback = self.pending.pop(key)
        if key not in self.cancelled and not self.closed:
            callback(InferenceCompletion(game_id, command_id, request.fingerprint_hash, vector))
        self.cancelled.discard(key)

    def close(self) -> None:
        self.closed = True
        self.cancelled.update(self.pending)


class FakeRecovery:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def apply_deletion_ledger(self) -> None:
        self.calls.append("deletions")

    def expire_private_data(self, now_ms: int) -> None:
        self.calls.append("expiry")

    def validate_key_material(self) -> None:
        FakeCommandKeys().validate_versions(frozenset({"fixture-key-v1"}))
        self.calls.append("keys")

    def interrupt_active_games(self, now_ms: int) -> None:
        self.calls.append("interrupt")

    def clean_orphan_assets(self) -> None:
        self.calls.append("orphans")


class FakeLifecycle:
    def __init__(self, locks: FakeGameLocks) -> None:
        self.locks = locks
        self.interrupted: set[str] = set()
        self.forgotten: set[str] = set()

    def interrupt(self, game_id: str, now_utc_ms: int) -> None:
        with self.locks.hold(game_id):
            self.interrupted.add(game_id)

    def forget(self, game_id: str) -> None:
        with self.locks.hold(game_id):
            self.forgotten.add(game_id)


def smoke() -> None:
    from contextlib import closing

    from .application import Application
    from .storage import connect

    clock = FakeClock()
    recovery = FakeRecovery()
    with closing(connect(":memory:")) as db:
        app = Application(db, clock, recovery)
        app.start()
        assert app.ready
    assert recovery.calls == ["deletions", "expiry", "keys", "interrupt", "orphans"]
    locks = FakeGameLocks()
    lifecycle = FakeLifecycle(locks)
    lifecycle.interrupt("fixture-game", clock.utc_ms())
    lifecycle.forget("fixture-game")
    queue = ManualInference()
    completed: list[InferenceCompletion] = []
    request = InferenceRequest(
        "fixture-game",
        "fixture-command",
        "synthetic input",
        "fixture-fingerprint",
        clock.monotonic_ms() + 5000,
    )
    assert queue.submit(request, completed.append)
    assert not completed
    queue.finish(request.game_id, request.command_id, (1.0, 0.0))
    assert len(completed) == 1
    queue.close()
    keys = FakeCommandKeys()
    assert len(keys.digest(keys.active_version(), b"synthetic canonical bytes")) == 64
