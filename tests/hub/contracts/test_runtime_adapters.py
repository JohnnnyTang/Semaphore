import base64
import json
import threading

import pytest

from semaphore_core.embeddings import fingerprint_hash
from semaphore_hub.interfaces import InferenceRequest
from semaphore_hub.runtime import FileCommandKeys, QueuedInference, StripedGameLocks


class Clock:
    now = 10

    def monotonic_ms(self):
        return self.now


class Embedder:
    def __init__(self):
        self.entered = threading.Event()
        self.release = threading.Event()
        self.bad = False

    def identity(self):
        return {"fixture": True}

    def embed_queries(self, texts):
        self.entered.set()
        assert self.release.wait(5)
        return [[1.0] + [0.0] * 2559 for _ in texts] if not self.bad else []


def request(index, deadline=100):
    return InferenceRequest(
        str(index), "command", "fixture", fingerprint_hash({"fixture": True}), deadline
    )


def test_keys_rotation_and_missing_version_fail_closed(tmp_path):
    path = tmp_path / "keys.json"
    path.write_text(
        json.dumps(
            {
                "active": "v2",
                "keys": {
                    "v1": base64.b64encode(b"a" * 32).decode(),
                    "v2": base64.b64encode(b"b" * 32).decode(),
                },
            }
        )
    )
    keys = FileCommandKeys(path)
    assert keys.active_version() == "v2"
    assert keys.digest("v1", b"original") != keys.digest("v2", b"original")
    assert keys.digest("v1", b"original") == FileCommandKeys(path).digest("v1", b"original")
    with pytest.raises(ValueError, match="missing"):
        keys.digest("lost", b"original")
    path.write_text('{"active":"missing","keys":{}}')
    with pytest.raises(ValueError, match="missing"):
        FileCommandKeys(path)


def test_cancel_retains_physical_capacity_and_callbacks_are_async():
    embedder = Embedder()
    queue = QueuedInference(embedder, clock=Clock())
    seen = []
    done = threading.Event()
    caller = threading.get_ident()

    def callback(value):
        seen.append((value, threading.get_ident()))
        if len(seen) == 7:
            done.set()

    try:
        assert queue.submit(request(0), callback)
        assert embedder.entered.wait(3)
        for index in range(1, 8):
            assert queue.submit(request(index), callback)
        queue.cancel("0", "command")
        assert not queue.submit(request(8), callback)
        assert not queue.submit(request(1), callback)
        assert seen == []
        embedder.release.set()
        assert done.wait(5)
        assert all(value.game_id != "0" and tid != caller for value, tid in seen)
        assert all(value.error is None for value, _ in seen)
    finally:
        embedder.release.set()
        queue.close()


def test_late_result_times_out_and_malformed_batch_fails():
    for malformed in (False, True):
        embedder, clock = Embedder(), Clock()
        embedder.bad = malformed
        queue = QueuedInference(embedder, clock=clock)
        done, results = threading.Event(), []

        def callback(value, results=results, done=done):
            results.append(value)
            done.set()

        try:
            assert queue.submit(request(0), callback)
            assert embedder.entered.wait(3)
            if not malformed:
                clock.now = 100
            embedder.release.set()
            assert done.wait(5)
            assert results[0].vector is None
            assert results[0].error == ("inference_failed" if malformed else "inference_timeout")
        finally:
            embedder.release.set()
            queue.close()


def test_game_lock_is_reentrant_and_bounded():
    locks = StripedGameLocks()
    with locks.hold("game"), locks.hold("game"):
        assert locks.hold("game") is locks.hold("game")
    for index in range(10000):
        locks.hold(str(index))
    assert len(locks._locks) == 256
