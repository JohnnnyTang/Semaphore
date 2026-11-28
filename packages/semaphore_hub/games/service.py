"""Durable reducer orchestration with injected shared locks, keys and inference."""

import hashlib
import hmac
import json
import secrets
import threading
from dataclasses import dataclass, replace
from pathlib import Path

from jsonschema import Draft202012Validator

from semaphore_core.game import (
    ClueCommand,
    GameArtifact,
    advance,
    complete,
    freeze,
    initial_state,
    quit_game,
    snapshot,
    submit,
    thaw,
)
from semaphore_core.verification import canonical, dot, load, vector
from semaphore_hub.interfaces import InferenceRequest, SystemClock
from semaphore_hub.packs import SQLitePacks
from semaphore_hub.policy import MAX_ACTIVE_GAMES, MAX_COMMANDS_PER_GAME, RECEIPT_RETENTION_MS
from semaphore_hub.repositories import Attempt, Command, Game, NotFound, Score

from .repository import SQLiteGames


class GameError(Exception):
    def __init__(self, status, code):
        self.status, self.code = status, code
        super().__init__(code)


@dataclass
class Live:
    state: object
    origin: int
    vectors: dict


def installed_vectors(transactions, artifact):
    with transactions() as db:
        row = db.execute(
            "SELECT vector_hash,manifest_bytes FROM pack_versions v JOIN "
            "published_versions p USING(version_id) WHERE v.version_id=?",
            (artifact.version_id,),
        ).fetchone()
        if row is None:
            raise NotFound("published version")
        cache = SQLitePacks(db).vectors(row[0], artifact.fingerprint_hash)
    if cache is None:
        raise GameError(503, "unavailable")
    raw = Path(cache.asset_path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != cache.ordered_vectors_digest:
        raise GameError(503, "unavailable")
    entries = json.loads(row[1])["entries"]
    rows = json.loads(raw)
    if len(rows) != len(entries):
        raise GameError(503, "unavailable")
    return {entry["id"]: vector(values) for entry, values in zip(entries, rows, strict=True)}


class GameService:
    def __init__(self, transactions, inference, keys, locks, *, clock=None, artifact_loader=None):
        self.transactions, self.inference, self.keys, self.locks = (
            transactions,
            inference,
            keys,
            locks,
        )
        self.clock = clock or SystemClock()
        self.artifact_loader = artifact_loader or (lambda a: installed_vectors(transactions, a))
        self.live = {}
        self.creation = threading.RLock()
        self.validators = {
            name: Draft202012Validator(load("http.schema.json")["$defs"][name])
            for name in ("create", "command")
        }

    def _validate(self, name, payload):
        if next(self.validators[name].iter_errors(payload), None) is not None:
            raise GameError(400, "invalid_request")

    def _envelope(self, game, receipt=None):
        return dict(
            protocol="experiment-v1",
            sequence=game.revision,
            kind="receipt" if receipt else "snapshot",
            snapshot=json.loads(game.snapshot_json),
            receipt=receipt,
        )

    def create(self, player_id, payload):
        self._validate("create", payload)
        self.keys.validate_versions(frozenset())
        with self.creation:
            with self.transactions() as db:
                repo = SQLiteGames(db)
                if repo.current(player_id) or len(repo.active_ids()) >= MAX_ACTIVE_GAMES:
                    raise GameError(503, "unavailable")
                artifact = SQLitePacks(db).artifact(payload["artifact_id"])
                binding = db.execute(
                    "SELECT v.manifest_digest,v.manifest_bytes,r.fingerprint_hash,r.ruleset_id,"
                    "r.trusted,r.passed FROM pack_versions v JOIN published_versions p "
                    "USING(version_id) JOIN verification_reports r ON r.report_id=? "
                    "AND r.version_id=v.version_id WHERE v.version_id=?",
                    (artifact.report_id, artifact.version_id),
                ).fetchone()
                if binding is None or tuple(binding[2:]) != (
                    artifact.fingerprint_hash,
                    artifact.ruleset_id,
                    1,
                    1,
                ):
                    raise GameError(503, "unavailable")
                if artifact.mode != payload["mode"]:
                    raise GameError(400, "invalid_request")
            body = json.loads(artifact.artifact_json)
            if (
                hashlib.sha256(artifact.artifact_json.encode()).hexdigest()
                != artifact.artifact_digest
            ):
                raise GameError(503, "unavailable")
            config = json.loads(artifact.config_json)
            expected = dict(
                pack_digest=binding[0],
                model_fingerprint=artifact.fingerprint_hash,
                ruleset_id=artifact.ruleset_id,
                config_digest=artifact.config_digest,
                challenge_digest=artifact.challenge_digest,
            )
            if (
                hashlib.sha256(artifact.config_json.encode()).hexdigest() != artifact.config_digest
                or hashlib.sha256(binding[1]).hexdigest() != binding[0]
                or body.get("identities") != expected
                or body.get("mode") != artifact.mode
                or artifact.fingerprint_hash != load("model-lock.json")["fingerprint_sha256"]
                or any(
                    body.get(key) != config.get(key)
                    for key in (
                        "initial_board",
                        "schedule",
                        "deadline_ms",
                        "capacity",
                        "zone_size",
                        "score_pacing",
                        "initial_score",
                        "initial_clears",
                        "mode",
                    )
                )
            ):
                raise GameError(503, "unavailable")
            entries = json.loads(binding[1])["entries"]
            expected_entries = {
                e["id"]: dict(
                    label=e["text"],
                    aliases=e.get("aliases", []),
                    forbidden=e.get("forbidden_clues", []),
                )
                for e in entries
            }
            if body.get("entries") != expected_entries:
                raise GameError(503, "unavailable")
            core = GameArtifact(**body)
            if core.test_mode or core.initial_score or core.initial_clears:
                raise GameError(400, "invalid_request")
            vectors = self.artifact_loader(artifact)
            if set(vectors) != set(core.entries):
                raise GameError(503, "unavailable")
            vectors = {key: vector(row) for key, row in vectors.items()}
            gid = secrets.token_hex(16)
            state = initial_state(core, game_id=gid)
            now = self.clock.utc_ms()
            game = Game(
                gid,
                player_id,
                artifact,
                json.dumps(load("model-lock.json")["fingerprint"]),
                state.revision,
                json.dumps(snapshot(state, now_ms=0)),
                now,
            )
            with self.locks.hold(gid):
                with self.transactions() as db:
                    SQLiteGames(db).create(game)
                self.live[gid] = Live(state, self.clock.monotonic_ms(), vectors)
            return self._envelope(game)

    def _owned(self, player_id, gid):
        with self.transactions() as db:
            return SQLiteGames(db).owned(gid, player_id)

    def _window(self, game):
        if (
            game.finished_at is not None
            and self.clock.utc_ms() >= game.finished_at + RECEIPT_RETENTION_MS
        ):
            raise GameError(410, "game_expired")

    def _persist(self, game, state, now=None):
        now = self.clock.utc_ms() if now is None else now
        updated = replace(
            game,
            revision=state.revision,
            snapshot_json=json.dumps(snapshot(state, now_ms=state.elapsed_ms)),
            finished_at=now if state.end_reason else None,
            end_reason=state.end_reason,
        )
        with self.transactions() as db:
            repo = SQLiteGames(db)
            pending = []
            for cid, receipt in state.receipts.items():
                if receipt["outcome"] == "pending":
                    continue
                old = repo.receipt(game.game_id, cid, game.player_id)
                if not old.final:
                    pending.append(replace(old, final=True, receipt_json=json.dumps(thaw(receipt))))
            if state.end_reason:
                score = None
                if state.end_reason != "interrupted":
                    name = db.execute(
                        "SELECT display_name FROM accounts WHERE account_id=?", (game.player_id,)
                    ).fetchone()[0]
                    score = Score(
                        game.game_id, game.player_id, name, state.score, now, repo.cohort(game)
                    )
                updated = repo.finish(game.player_id, updated, score, tuple(pending))
            else:
                for command in pending:
                    repo.finalize_command(game.player_id, command)
                repo.save_transition(game.player_id, updated)
            for command in pending:
                db.execute(
                    "UPDATE clue_attempts SET resolved_at=? WHERE game_id=? AND command_id=?",
                    (now, game.game_id, command.command_id),
                )
        live = self.live[game.game_id]
        previous = live.state.pending
        live.state = replace(
            state,
            payloads=freeze({}),
            receipts=freeze({k: v for k, v in state.receipts.items() if v["outcome"] == "pending"}),
        )
        if previous and (not state.pending or previous.command_id != state.pending.command_id):
            self.inference.cancel(game.game_id, previous.command_id)
        if state.end_reason:
            self.live.pop(game.game_id, None)
        return updated

    def _advance(self, game):
        if game.finished_at is not None:
            return game
        live = self.live.get(game.game_id)
        if live is None:
            raise GameError(503, "unavailable")  # recovery must run before traffic
        transition = advance(
            live.state, now_ms=max(live.state.elapsed_ms, self.clock.monotonic_ms() - live.origin)
        )
        if not transition.changed:
            # Clock-only reads need a fresh projection, not a durable write. Recovery
            # interrupts active games; elapsed time alone is not a recoverable event.
            live.state = transition.state
            return replace(
                game,
                snapshot_json=json.dumps(snapshot(live.state, now_ms=live.state.elapsed_ms)),
            )
        return self._persist(game, transition.state)

    def tick(self):
        """Host scheduler hook: advance all live games without a client request."""
        with self.transactions() as db:
            ids = SQLiteGames(db).active_ids()
        for gid in ids:
            with self.locks.hold(gid):
                with self.transactions() as db:
                    game = SQLiteGames(db).for_recovery(gid)
                self._advance(game)

    def get(self, player_id, gid):
        with self.locks.hold(gid):
            return self._envelope(self._advance(self._owned(player_id, gid)))

    def current(self, player_id):
        with self.transactions() as db:
            game = SQLiteGames(db).current(player_id)
        return self.get(player_id, game.game_id) if game else None

    def receipt(self, player_id, gid, cid):
        with self.locks.hold(gid):
            game = self._advance(self._owned(player_id, gid))
            self._window(game)
            with self.transactions() as db:
                receipt = SQLiteGames(db).receipt(gid, cid, player_id)
            return self._envelope(game, json.loads(receipt.receipt_json))

    def command(self, player_id, gid, payload):
        self._validate("command", payload)
        with self.locks.hold(gid):
            game = self._advance(self._owned(player_id, gid))
            self._window(game)
            cid = payload["command_id"]
            canonical_payload = canonical(["durable-command-v1", gid, cid, payload])
            with self.transactions() as db:
                repo = SQLiteGames(db)
                try:
                    old = repo.receipt(gid, cid, player_id)
                except NotFound:
                    old = None
                count = db.execute(
                    "SELECT count(*) FROM commands WHERE game_id=?", (gid,)
                ).fetchone()[0]
            if old:
                if hmac.compare_digest(
                    old.payload_hmac, self.keys.digest(old.hmac_key_version, canonical_payload)
                ):
                    return self._envelope(game, json.loads(old.receipt_json))
                receipt = dict(
                    command_id=cid,
                    outcome="command_conflict",
                    applied_revision=game.revision,
                    target=None,
                    target_rank=None,
                    ranked_board=[],
                    score_delta=0,
                )
                return self._envelope(game, receipt)
            if count >= MAX_COMMANDS_PER_GAME:
                raise GameError(503, "unavailable")
            version = self.keys.active_version()
            digest = self.keys.digest(version, canonical_payload)
            state = self.live[gid].state if gid in self.live else None
            submitted = False
            if state is not None:
                transition = submit(
                    state,
                    ClueCommand(**payload),
                    now_ms=state.elapsed_ms,
                    inference_slot_available=True,
                )
                if transition.effects:
                    effect = transition.effects[0]
                    req = InferenceRequest(
                        gid,
                        cid,
                        effect.text,
                        game.artifact.fingerprint_hash,
                        self.live[gid].origin + effect.timeout_ms,
                    )
                    submitted = self.inference.submit(req, self.complete)
                    if not submitted:
                        transition = submit(
                            state,
                            ClueCommand(**payload),
                            now_ms=state.elapsed_ms,
                            inference_slot_available=False,
                        )
                receipt = transition.receipt
            else:
                receipt = dict(
                    command_id=cid,
                    outcome="game_over",
                    applied_revision=game.revision,
                    target=None,
                    target_rank=None,
                    ranked_board=[],
                    score_delta=0,
                )
            now = self.clock.utc_ms()
            command = Command(
                gid, cid, digest, version, now, json.dumps(receipt), receipt["outcome"] != "pending"
            )
            attempt = Attempt(
                gid,
                cid,
                payload["clue"],
                receipt["target"],
                now,
                now if command.final else None,
                receipt["outcome"] if command.final else None,
                receipt["target_rank"],
            )
            try:
                with self.transactions() as db:
                    repo = SQLiteGames(db)
                    repo.admit(player_id, command, attempt)
                    if state is not None:
                        updated = replace(
                            game,
                            revision=transition.state.revision,
                            snapshot_json=json.dumps(
                                snapshot(transition.state, now_ms=transition.state.elapsed_ms)
                            ),
                        )
                        repo.save_transition(player_id, updated)
                if state is not None:
                    self.live[gid].state = replace(
                        transition.state,
                        payloads=freeze({}),
                        receipts=freeze(
                            {
                                k: v
                                for k, v in transition.state.receipts.items()
                                if v["outcome"] == "pending"
                            }
                        ),
                    )
                    game = updated
            except BaseException:
                if submitted:
                    self.inference.cancel(gid, cid)
                raise
            return self._envelope(game, receipt)

    def complete(self, completion):
        gid = completion.game_id
        with self.locks.hold(gid):
            live = self.live.get(gid)
            if (
                live is None
                or live.state.pending is None
                or live.state.pending.command_id != completion.command_id
            ):
                return
            with self.transactions() as db:
                game = SQLiteGames(db).for_recovery(gid)
            game = self._advance(game)
            live = self.live.get(gid)
            if (
                live is None
                or live.state.pending is None
                or live.state.pending.command_id != completion.command_id
            ):
                return
            error = completion.error
            scores = None
            try:
                if completion.fingerprint_hash != game.artifact.fingerprint_hash:
                    raise ValueError("pin mismatch")
                if completion.vector is not None and error is None:
                    query = vector(completion.vector)
                    scores = {key: dot(query, live.vectors[key]) for key in live.state.board}
                else:
                    error = "inference_failed"
            except ValueError:
                error = "inference_failed"
            state = complete(
                live.state,
                command_id=completion.command_id,
                now_ms=live.state.elapsed_ms,
                scores=scores,
                error=error,
            ).state
            self._persist(game, state)

    def quit(self, player_id, gid):
        with self.locks.hold(gid):
            game = self._advance(self._owned(player_id, gid))
            if game.finished_at is None:
                state = self.live[gid].state
                game = self._persist(game, quit_game(state, now_ms=state.elapsed_ms).state)
            return self._envelope(game)

    def interrupt(self, gid, now_utc_ms):
        with self.locks.hold(gid):
            with self.transactions() as db:
                game = SQLiteGames(db).for_recovery(gid)
            if game.finished_at is not None:
                return
            if gid in self.live:
                game = self._advance(game)
                if game.finished_at is None:
                    state = self.live[gid].state
                    self._persist(game, quit_game(state, now_ms=state.elapsed_ms).state, now_utc_ms)
                return
            # A restarted clock cannot replay elapsed work. Interrupt the durable snapshot.
            body = json.loads(game.snapshot_json)
            body.update(
                status="over",
                end_reason="interrupted",
                pending=None,
                next_spawn_ms=None,
                revision=game.revision + 1,
            )
            updated = replace(
                game,
                revision=game.revision + 1,
                snapshot_json=json.dumps(body),
                finished_at=now_utc_ms,
                end_reason="interrupted",
            )
            with self.transactions() as db:
                repo = SQLiteGames(db)
                pending = []
                for row in db.execute(
                    "SELECT command_id FROM commands WHERE game_id=? AND state='pending'", (gid,)
                ):
                    command = repo.receipt(gid, row[0], game.player_id)
                    receipt = json.loads(command.receipt_json)
                    receipt.update(outcome="game_over", applied_revision=updated.revision)
                    pending.append(replace(command, final=True, receipt_json=json.dumps(receipt)))
                repo.finish(game.player_id, updated, None, tuple(pending))
                for command in pending:
                    db.execute(
                        "UPDATE clue_attempts SET resolved_at=? WHERE game_id=? AND command_id=?",
                        (now_utc_ms, gid, command.command_id),
                    )
            for command in pending:
                self.inference.cancel(gid, command.command_id)

    def forget(self, gid):
        with self.locks.hold(gid):
            live = self.live.pop(gid, None)
            if live and live.state.pending:
                self.inference.cancel(gid, live.state.pending.command_id)
