"""Bounded shared locks, external command keys and one physical inference worker."""

import base64
import hashlib
import hmac
import json
import re
import threading
from collections import deque
from pathlib import Path

from semaphore_core.embeddings import fingerprint_hash
from semaphore_core.verification import vector
from semaphore_hub.auth.http import object_pairs
from semaphore_hub.interfaces import InferenceCompletion, SystemClock
from semaphore_hub.policy import MAX_OUTSTANDING_INFERENCES


class StripedGameLocks:
    """Fixed memory; collisions serialize safely, and lifecycle calls may reenter."""

    def __init__(self):
        self._locks = tuple(threading.RLock() for _ in range(256))

    def hold(self, game_id):
        index = hashlib.sha256(game_id.encode()).digest()[0]
        return self._locks[index]


class FileCommandKeys:
    """Load immutable externally provisioned versions; never generate missing keys."""

    def __init__(self, path):
        with Path(path).open("rb") as stream:
            raw = stream.read(65537)
        if len(raw) > 65536:
            raise ValueError("keyring too large")
        data = json.loads(raw, object_pairs_hook=object_pairs)
        if not isinstance(data, dict) or set(data) != {"active", "keys"}:
            raise ValueError("invalid keyring")
        self._active = data["active"]
        self._keys = {}
        if not isinstance(data["keys"], dict):
            raise ValueError("invalid keyring")
        for version, encoded in data["keys"].items():
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", version):
                raise ValueError("invalid key version")
            key = base64.b64decode(encoded, validate=True)
            if len(key) < 32:
                raise ValueError("short command key")
            self._keys[version] = key
        self.validate_versions(frozenset())

    def active_version(self):
        return self._active

    def validate_versions(self, required):
        if self._active not in self._keys or required - self._keys.keys():
            raise ValueError("missing command key")

    def digest(self, version, canonical_payload):
        self.validate_versions(frozenset({version}))
        return hmac.new(self._keys[version], canonical_payload, hashlib.sha256).hexdigest()


class QueuedInference:
    """FIFO, at most eight physically outstanding requests, no inline callbacks.

    Cancellation never frees running capacity. Model calls have transport timeouts
    supplied by the embedder; shutdown does not pretend to kill a blocked call.
    """

    def __init__(self, embedder, *, clock=None):
        self.embedder = embedder
        self.clock = clock or SystemClock()
        self._condition = threading.Condition()
        self._waiting = deque()
        self._outstanding = {}
        self._closed = False
        self._thread = threading.Thread(target=self._run, name="hub-inference", daemon=True)
        self._thread.start()

    def submit(self, request, complete):
        with self._condition:
            if (
                self._closed
                or len(self._outstanding) >= MAX_OUTSTANDING_INFERENCES
                or request.game_id in self._outstanding
            ):
                return False
            item = [request, complete, False]
            self._outstanding[request.game_id] = item
            self._waiting.append(item)
            self._condition.notify()
            return True

    def cancel(self, game_id, command_id):
        with self._condition:
            item = self._outstanding.get(game_id)
            if item is not None and item[0].command_id == command_id:
                item[2] = True

    def close(self):
        with self._condition:
            self._closed = True
            for item in self._outstanding.values():
                item[2] = True
            self._condition.notify_all()

    def _run(self):
        while True:
            with self._condition:
                self._condition.wait_for(lambda: self._waiting or self._closed)
                if not self._waiting:
                    return
                batch = [self._waiting.popleft() for _ in range(len(self._waiting))]
            active = [
                item
                for item in batch
                if not item[2] and self.clock.monotonic_ms() < item[0].deadline_monotonic_ms
            ]
            rows = {}
            error = None
            if active:
                try:
                    identity = fingerprint_hash(self.embedder.identity())
                    if any(item[0].fingerprint_hash != identity for item in active):
                        raise ValueError("identity mismatch")
                    vectors = self.embedder.embed_queries(
                        [item[0].normalized_clue for item in active]
                    )
                    if len(vectors) != len(active):
                        raise ValueError("batch length")
                    validated = [vector(row) for row in vectors]
                    if fingerprint_hash(self.embedder.identity()) != identity:
                        raise ValueError("identity changed")
                    rows = {
                        item[0].game_id: row for item, row in zip(active, validated, strict=True)
                    }
                except Exception:
                    error = "inference_failed"
            for item in batch:
                request, callback, _ = item
                with self._condition:
                    self._outstanding.pop(request.game_id, None)
                    deliver = not self._closed and not item[2]
                if deliver:
                    expired = self.clock.monotonic_ms() >= request.deadline_monotonic_ms
                    completion = InferenceCompletion(
                        request.game_id,
                        request.command_id,
                        request.fingerprint_hash,
                        None if expired or error else rows.get(request.game_id),
                        "inference_timeout" if expired else error,
                    )
                    try:
                        callback(completion)
                    except Exception:
                        # Service owns failure closure; never print private exception data.
                        pass
