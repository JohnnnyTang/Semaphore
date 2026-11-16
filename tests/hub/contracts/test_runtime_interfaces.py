"""Executable adapter contracts; no real inference/recovery claim."""

import pytest

from semaphore_hub.interfaces import InferenceRequest
from semaphore_hub.runtime_testing import (
    FakeCommandKeys,
    FakeGameLocks,
    ManualInference,
    smoke,
)


def test_runtime_composition_smoke():
    smoke()


def test_logical_cancel_does_not_free_physical_capacity():
    queue = ManualInference(capacity=1)
    received = []
    first = InferenceRequest("g", "1", "synthetic", "f", 5000)
    second = InferenceRequest("g", "2", "synthetic", "f", 5000)
    assert queue.submit(first, received.append)
    assert received == []
    queue.cancel("g", "1")
    assert not queue.submit(second, received.append)
    queue.finish("g", "1", (1.0,))
    assert received == []
    assert queue.submit(second, received.append)
    queue.close()
    queue.finish("g", "2", (1.0,))
    assert received == []
    assert not queue.submit(second, received.append)


def test_missing_key_never_silently_replaces_digest_key():
    keys = FakeCommandKeys()
    with pytest.raises(ValueError, match="missing key"):
        keys.digest("lost-key", b"synthetic")
    with pytest.raises(ValueError):
        keys.validate_versions(frozenset({"lost-key"}))
    assert keys.digest(keys.active_version(), b"a") != keys.digest(keys.active_version(), b"A")


def test_fake_lock_is_shared_and_released_on_error():
    locks = FakeGameLocks()
    with pytest.raises(RuntimeError):
        with locks.hold("g"):
            with locks.hold("g"):
                pass
    assert not locks.held
