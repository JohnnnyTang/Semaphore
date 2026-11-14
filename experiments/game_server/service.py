"""Disposable in-memory service and bounded FIFO batched inference worker."""

import queue
import secrets
import threading
import time
from dataclasses import dataclass, field
from urllib.parse import unquote, urlsplit

from jsonschema import Draft202012Validator

from semaphore_core._manifest import parse
from semaphore_core.game import (
    ClueCommand,
    advance,
    complete,
    freeze,
    initial_state,
    quit_game,
    snapshot,
    submit,
    thaw,
)
from semaphore_core.verification import CoreValidationError, dot, load, vector


class ProtocolError(Exception):
    def __init__(self, status, code):
        self.status, self.code = status, code
        super().__init__(code)


@dataclass
class Session:
    state: object
    started: float
    vectors: dict
    sequence: int = -1
    timings: dict = field(default_factory=dict)
    lock: object = field(default_factory=threading.RLock)


class GameService:
    def __init__(self, artifacts, embedder, *, clock=time.monotonic, max_games=128):
        # artifacts map operator IDs to (validated artifact, trusted precomputed vectors).
        self.artifacts = {}
        for name, (artifact, rows) in artifacts.items():
            if artifact.test_mode:
                raise ValueError("test artifacts require a fixture transport")
            if set(rows) != set(artifact.entries):
                raise ValueError("artifact vector table mismatch")
            self.artifacts[name] = (artifact, freeze({i: vector(row) for i, row in rows.items()}))
        self.embedder, self.clock, self.max_games = embedder, clock, max_games
        self.sessions, self.tombstones = {}, set()
        self.lock = threading.RLock()
        schemas = load("http.schema.json")["$defs"]
        self.validators = {
            name: Draft202012Validator(schemas[name]) for name in ("create", "command")
        }
        self.slots = threading.BoundedSemaphore(8)
        self.jobs = queue.Queue(maxsize=8)
        self.closed = threading.Event()
        self.worker = threading.Thread(target=self._work, daemon=True, name="game-inference")
        self.worker.start()

    def close(self):
        self.closed.set()
        self.worker.join(timeout=1)

    def _now(self, session):
        return max(0, int((self.clock() - session.started) * 1000))

    def _advance(self, session):
        session.state = advance(session.state, now_ms=self._now(session)).state

    def _envelope(self, session, receipt=None):
        session.sequence += 1
        return dict(
            protocol="experiment-v1",
            sequence=session.sequence,
            kind="receipt" if receipt else "snapshot",
            snapshot=snapshot(session.state, now_ms=session.state.elapsed_ms),
            receipt=thaw(receipt) if receipt else None,
        )

    def _sweep(self):
        for ident, session in list(self.sessions.items()):
            with session.lock:
                self._advance(session)
                if (
                    session.state.terminal_ms is not None
                    and self._now(session) >= session.state.terminal_ms + 900000
                ):
                    del self.sessions[ident]
                    self.tombstones.add(ident)

    def _session(self, ident):
        with self.lock:
            # Receipt polling must not advance or lock unrelated games. Creation
            # still sweeps all sessions; direct access expires this session exactly.
            session = self.sessions.get(ident)
            if session is not None:
                with session.lock:
                    self._advance(session)
                    if (
                        session.state.terminal_ms is not None
                        and self._now(session) >= session.state.terminal_ms + 900000
                    ):
                        del self.sessions[ident]
                        self.tombstones.add(ident)
            if ident in self.tombstones:
                raise ProtocolError(410, "game_expired")
            if ident not in self.sessions:
                raise ProtocolError(404, "not_found")
            return self.sessions[ident]

    def _work(self):
        while not self.closed.is_set():
            try:
                batch = [self.jobs.get(timeout=0.1)]
            except queue.Empty:
                continue
            # No batching delay: collect only work already queued, in FIFO order.
            while len(batch) < 8:
                try:
                    batch.append(self.jobs.get_nowait())
                except queue.Empty:
                    break
            try:
                active = []
                for session, request, queued_at in batch:
                    with session.lock:
                        self._advance(session)
                        if session.state.pending == request:
                            active.append((session, request, queued_at))
                if not active:
                    continue
                started = time.perf_counter()
                try:
                    rows = self.embedder.embed_queries([request.text for _, request, _ in active])
                    finished = time.perf_counter()
                    if len(rows) != len(active):
                        raise ValueError()
                    # Validate the complete response before applying any member.
                    queries = [vector(row) for row in rows]
                    error = None
                except Exception:
                    finished = time.perf_counter()
                    queries, error = [None] * len(active), "inference_failed"
                for (session, request, queued_at), query in zip(active, queries, strict=True):
                    with session.lock:
                        session.timings[request.command_id] = {
                            "X-Semaphore-Queue-Ms": f"{(started - queued_at) * 1000:.3f}",
                            "X-Semaphore-Embedding-Ms": f"{(finished - started) * 1000:.3f}",
                        }
                        self._advance(session)
                        # Timed-out/quit requests cannot score, even if their batch succeeds.
                        scores = (
                            {i: dot(query, session.vectors[i]) for i in session.state.board}
                            if query is not None and session.state.pending == request
                            else None
                        )
                        session.state = complete(
                            session.state,
                            command_id=request.command_id,
                            now_ms=session.state.elapsed_ms,
                            scores=scores,
                            error=error,
                        ).state
            finally:
                for _ in batch:
                    self.slots.release()
                    self.jobs.task_done()

    def timing_headers(self, envelope):
        """Completed adapter timings only; never synthesize zeros for unmeasured work."""
        receipt = envelope.get("receipt")
        if not receipt or receipt["outcome"] in {"pending", "command_conflict"}:
            return {}
        with self.lock:
            session = self.sessions.get(envelope["snapshot"]["game_id"])
        if session is None:
            return {}
        with session.lock:
            return dict(session.timings.get(receipt["command_id"], {}))

    def request(self, method, path, raw=b""):
        parts = [unquote(p) for p in urlsplit(path).path.strip("/").split("/")]
        prefix = ["experiment", "v1", "games"]
        if parts[:3] != prefix:
            raise ProtocolError(404, "not_found")
        payload = None
        if method == "POST":
            if len(raw) > 16384:
                raise ProtocolError(400, "invalid_request")
            if len(parts) == 3 or (len(parts) == 5 and parts[4] == "commands"):
                try:
                    payload = parse(raw)
                    validator = self.validators["create" if len(parts) == 3 else "command"]
                    if next(validator.iter_errors(payload), None) is not None:
                        raise ValueError()
                except ValueError:
                    raise ProtocolError(400, "invalid_request") from None
        if len(parts) == 3 and method == "POST":
            with self.lock:
                self._sweep()
                if len(self.sessions) >= self.max_games:
                    raise ProtocolError(503, "unavailable")
                binding = self.artifacts.get(payload["artifact_id"])
                if binding is None or binding[0].mode != payload["mode"]:
                    raise ProtocolError(400, "invalid_request")
                artifact, vectors = binding
                ident = secrets.token_urlsafe(24)
                session = Session(initial_state(artifact, game_id=ident), self.clock(), vectors)
                self.sessions[ident] = session
                return 201, self._envelope(session)
        if len(parts) < 4:
            raise ProtocolError(404, "not_found")
        session = self._session(parts[3])
        with session.lock:
            self._advance(session)
            if method == "GET" and len(parts) == 4:
                return 200, self._envelope(session)
            if method == "POST" and len(parts) == 5 and parts[4] == "quit":
                if raw not in (b"", b"{}"):
                    raise ProtocolError(400, "invalid_request")
                session.state = quit_game(session.state, now_ms=session.state.elapsed_ms).state
                return 200, self._envelope(session)
            if method == "GET" and len(parts) == 6 and parts[4] == "receipts":
                receipt = session.state.receipts.get(parts[5])
                if receipt is None:
                    raise ProtocolError(404, "receipt_not_found")
                return 200, self._envelope(session, receipt)
            if method == "POST" and len(parts) == 5 and parts[4] == "commands":
                slot = self.slots.acquire(blocking=False)
                try:
                    t = submit(
                        session.state,
                        ClueCommand(**payload),
                        now_ms=session.state.elapsed_ms,
                        inference_slot_available=slot,
                    )
                except CoreValidationError:
                    if slot:
                        self.slots.release()
                    raise ProtocolError(503, "unavailable") from None
                session.state = t.state
                if t.effects:
                    self.jobs.put_nowait((session, t.effects[0], time.perf_counter()))
                elif slot:
                    self.slots.release()
                return (202 if t.receipt["outcome"] == "pending" else 200), self._envelope(
                    session, t.receipt
                )
        raise ProtocolError(404, "not_found")
