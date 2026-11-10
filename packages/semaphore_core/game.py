"""Pure immutable Arcade reducer. Time is elapsed monotonic milliseconds."""

import math
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType

from .verification import CoreValidationError, check_clue, normalize, order

# Frozen ruleset identity, checked against packaged lock by regression tests.
PINNED_FINGERPRINT_HASH = "657120305f464d0fb6a6006b9dbc8152af04ba30317dadcef1b41af0aa2941a4"


def freeze(value):
    if isinstance(value, Mapping):
        return MappingProxyType({k: freeze(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(freeze(v) for v in value)
    return value


def thaw(value):
    if isinstance(value, Mapping):
        return {k: thaw(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [thaw(v) for v in value]
    return value


@dataclass(frozen=True)
class GameArtifact:
    mode: str
    identities: Mapping
    entries: Mapping
    initial_board: tuple[str, ...]
    schedule: tuple[Mapping, ...]
    deadline_ms: int
    capacity: int = 12
    zone_size: int = 3
    test_mode: bool = False
    initial_score: int = 0
    initial_clears: int = 0

    def __post_init__(self):
        try:
            self._validate()
        except (ValueError, TypeError, AttributeError, KeyError, OverflowError):
            raise CoreValidationError("invalid_artifact") from None

    def _validate(self):
        import re

        from .verification import ID, tokens

        if (
            not isinstance(self.identities, Mapping)
            or not isinstance(self.entries, Mapping)
            or not isinstance(self.initial_board, (tuple, list))
            or not isinstance(self.schedule, (tuple, list))
        ):
            raise ValueError()
        if (
            self.mode not in ("casual", "event")
            or type(self.test_mode) is not bool
            or type(self.deadline_ms) is not int
            or not 0 < self.deadline_ms <= 600000
            or type(self.capacity) is not int
            or not 2 <= self.capacity <= 12
            or type(self.zone_size) is not int
            or not 0 < self.zone_size < self.capacity
            or not 0 < len(self.initial_board) < self.capacity
            or type(self.initial_score) is not int
            or type(self.initial_clears) is not int
            or self.initial_clears < 0
            or self.initial_score != self.initial_clears * 100
        ):
            raise ValueError()
        for key in ("identities", "entries", "initial_board", "schedule"):
            object.__setattr__(self, key, freeze(getattr(self, key)))
        if set(self.identities) != {
            "pack_digest",
            "model_fingerprint",
            "ruleset_id",
            "config_digest",
            "challenge_digest",
        }:
            raise ValueError()
        for key, value in self.identities.items():
            if key == "challenge_digest" and value is None:
                continue
            if not isinstance(value, str) or not 1 <= len(value) <= 128:
                raise ValueError()
        if self.identities["ruleset_id"] != "experiment-arcade-v1":
            raise ValueError()
        if not self.test_mode:
            if self.initial_clears or self.initial_score:
                raise ValueError()
            for key in ("pack_digest", "model_fingerprint", "config_digest"):
                if not re.fullmatch(r"[0-9a-f]{64}", self.identities[key]):
                    raise ValueError()
            if self.identities["model_fingerprint"] != PINNED_FINGERPRINT_HASH:
                raise ValueError()
            challenge = self.identities["challenge_digest"]
            if (self.mode == "casual" and challenge is not None) or (
                self.mode == "event"
                and (not isinstance(challenge, str) or not re.fullmatch(r"[0-9a-f]{64}", challenge))
            ):
                raise ValueError()
        used = list(self.initial_board)
        last = 0
        for spawn in self.schedule:
            if set(spawn) != {"at_ms", "entry_id"}:
                raise ValueError()
            at = spawn["at_ms"]
            if type(at) is not int or at <= 0 or at < last or at >= self.deadline_ms:
                raise ValueError()
            last = at
            used.append(spawn["entry_id"])
        if len(set(used)) != len(used) or not set(used) <= set(self.entries):
            raise ValueError()
        if not self.test_mode and self.mode == "casual" and self.deadline_ms != last + 5000:
            raise ValueError()
        if not self.entries or len(self.entries) > 5000:
            raise ValueError()
        labels = set()
        for ident, entry in self.entries.items():
            if (
                not isinstance(ident, str)
                or not ID.fullmatch(ident)
                or not isinstance(entry, Mapping)
            ):
                raise ValueError()
            if set(entry) - {"label", "aliases", "forbidden", "inflections"}:
                raise ValueError()
            label = entry["label"]
            if normalize(label) != label or len(label) > 64 or not tokens(label):
                raise ValueError()
            if label.casefold() in labels:
                raise ValueError()
            labels.add(label.casefold())
            if "inflections" in entry and not self.test_mode:
                raise ValueError()
            for key, limit in (("aliases", 8), ("forbidden", 16), ("inflections", 16)):
                forms = entry.get(key, ())
                if not isinstance(forms, tuple) or len(forms) > limit:
                    raise ValueError()
                if len({text.casefold() for text in forms}) != len(forms):
                    raise ValueError()
                for text in forms:
                    if normalize(text) != text or len(text) > 64 or not tokens(text):
                        raise ValueError()


@dataclass(frozen=True)
class ClueCommand:
    command_id: str
    expected_revision: int
    clue: str

    def __post_init__(self):
        if (
            not isinstance(self.command_id, str)
            or not 1 <= len(self.command_id) <= 128
            or type(self.expected_revision) is not int
            or self.expected_revision < 0
            or not isinstance(self.clue, str)
            or len(self.clue) > 4096
        ):
            raise CoreValidationError("invalid_command")


@dataclass(frozen=True)
class InferenceRequest:
    command_id: str
    text: str
    target: str
    admitted_ms: int
    timeout_ms: int


@dataclass(frozen=True)
class EngineState:
    artifact: GameArtifact
    game_id: str
    board: tuple[str, ...]
    target: str | None
    score: int = 0
    clears: int = 0
    revision: int = 0
    elapsed_ms: int = 0
    next_spawn_index: int = 0
    pending: InferenceRequest | None = None
    end_reason: str | None = None
    terminal_ms: int | None = None
    receipts: Mapping = field(default_factory=lambda: freeze({}))
    payloads: Mapping = field(default_factory=lambda: freeze({}))


@dataclass(frozen=True)
class Transition:
    state: EngineState
    receipt: dict | None = None
    effects: tuple[InferenceRequest, ...] = ()
    changed: bool = False


def initial_state(artifact: GameArtifact, *, game_id: str) -> EngineState:
    return EngineState(
        artifact,
        game_id,
        artifact.initial_board,
        min(artifact.initial_board),
        score=artifact.initial_score,
        clears=artifact.initial_clears,
    )


def _receipt(state, ident, outcome, *, target=None, rank=None, ranked=(), delta=0):
    return dict(
        command_id=ident,
        outcome=outcome,
        applied_revision=state.revision,
        target=target,
        target_rank=rank,
        ranked_board=list(ranked),
        score_delta=delta,
    )


def _store(state, receipt):
    return replace(state, receipts=freeze({**state.receipts, receipt["command_id"]: receipt}))


def _end(state, reason, at):
    state = replace(state, revision=state.revision + 1, end_reason=reason, terminal_ms=at)
    if state.pending:
        state = _store(
            state,
            _receipt(state, state.pending.command_id, "game_over", target=state.pending.target),
        )
    return replace(state, pending=None)


def advance(state: EngineState, *, now_ms: int) -> Transition:
    if type(now_ms) is not int or now_ms < state.elapsed_ms:
        raise CoreValidationError("invalid_time")
    original = state.revision
    a = state.artifact
    while state.end_reason is None:
        spawn = (
            a.schedule[state.next_spawn_index] if state.next_spawn_index < len(a.schedule) else None
        )
        due = min(
            a.deadline_ms,
            spawn["at_ms"] if spawn else math.inf,
            state.pending.timeout_ms if state.pending else math.inf,
        )
        if due > now_ms:
            break
        if due == a.deadline_ms:
            state = _end(state, "event_complete" if a.mode == "event" else "pack_exhausted", due)
        elif spawn and due == spawn["at_ms"]:
            board = (*state.board, spawn["entry_id"])
            state = replace(
                state,
                board=board,
                target=state.target or min(board),
                next_spawn_index=state.next_spawn_index + 1,
            )
            if len(board) >= a.capacity:
                state = _end(state, "overflow", due)
            else:
                state = replace(state, revision=state.revision + 1)
        else:
            request = state.pending
            state = replace(state, pending=None, revision=state.revision + 1)
            state = _store(
                state,
                _receipt(state, request.command_id, "inference_timeout", target=request.target),
            )
    return Transition(replace(state, elapsed_ms=now_ms), changed=state.revision != original)


def _legality(clue, entry):
    if len(clue) > 120:
        return "clue_too_long"
    # N first: whitespace controls are deliberately collapsed under frozen N.
    try:
        text = normalize(clue)
    except ValueError:
        return "clue_empty" if not clue.strip() else "clue_control_character"
    if len(text) > 120:
        return "clue_too_long"
    target = dict(
        text=entry["label"],
        aliases=list(entry.get("aliases", ())),
        forbidden_clues=[*entry.get("forbidden", ()), *entry.get("inflections", ())],
    )
    decision = check_clue(text, target)
    if not decision.legal:
        return "clue_empty" if decision.reason == "empty_tokens" else "clue_forbidden"
    return None


def submit(
    state: EngineState, command: ClueCommand, *, now_ms: int, inference_slot_available: bool
) -> Transition:
    old_revision = state.revision
    state = advance(state, now_ms=now_ms).state
    ident = command.command_id
    if ident in state.payloads:
        receipt = (
            thaw(state.receipts[ident])
            if command == state.payloads[ident]
            else _receipt(state, ident, "command_conflict")
        )
        return Transition(state, receipt, changed=state.revision != old_revision)
    if len(state.payloads) >= 4096:
        raise CoreValidationError("command_limit")
    outcome = (
        "game_over"
        if state.end_reason
        else "busy"
        if state.pending
        else "stale_revision"
        if command.expected_revision != state.revision
        else "no_target"
        if state.target is None
        else _legality(command.clue, state.artifact.entries[state.target])
    )
    if not outcome and not inference_slot_available:
        outcome = "overloaded"
    effects = ()
    if not outcome:
        request = InferenceRequest(
            ident, normalize(command.clue), state.target, now_ms, now_ms + 5000
        )
        state = replace(state, pending=request, revision=state.revision + 1)
        effects = (request,)
        outcome = "pending"
    receipt = _receipt(state, ident, outcome, target=state.target)
    state = replace(state, payloads=freeze({**state.payloads, ident: command}))
    state = _store(state, receipt)
    return Transition(state, receipt, effects, state.revision != old_revision)


def complete(
    state: EngineState,
    *,
    command_id: str,
    now_ms: int,
    scores: Mapping[str, float] | None,
    error: str | None = None,
) -> Transition:
    old_revision = state.revision
    state = advance(state, now_ms=now_ms).state
    if not state.pending or state.pending.command_id != command_id:
        return Transition(state, changed=state.revision != old_revision)
    target = state.pending.target
    try:
        if error or scores is None or set(scores) != set(state.board):
            raise ValueError()
        ranked = order(scores)
        rank = ranked.index(target) + 1
    except (ValueError, TypeError, OverflowError):
        outcome = "inference_timeout" if error == "inference_timeout" else "inference_failed"
        state = replace(state, pending=None, revision=state.revision + 1)
        receipt = _receipt(state, command_id, outcome, target=target)
    else:
        cleared = rank <= state.artifact.zone_size
        board = tuple(i for i in ranked if not (cleared and i == target))
        state = replace(
            state,
            board=board,
            pending=None,
            revision=state.revision + 1,
            target=(min(board) if board else None) if cleared else target,
            score=state.score + (100 if cleared else 0),
            clears=state.clears + int(cleared),
        )
        if (
            not board
            and state.artifact.mode == "casual"
            and state.next_spawn_index == len(state.artifact.schedule)
        ):
            # Ranking and consequent terminal state form one transition.
            state = replace(state, end_reason="pack_cleared", terminal_ms=now_ms)
        receipt = _receipt(
            state,
            command_id,
            "clear" if cleared else "miss",
            target=target,
            rank=rank,
            ranked=ranked,
            delta=100 if cleared else 0,
        )
    state = _store(state, receipt)
    return Transition(state, receipt, changed=state.revision != old_revision)


def quit_game(state: EngineState, *, now_ms: int) -> Transition:
    old_revision = state.revision
    state = advance(state, now_ms=now_ms).state
    if not state.end_reason:
        state = _end(state, "interrupted", now_ms)
    return Transition(state, changed=state.revision != old_revision)


def snapshot(state: EngineState, *, now_ms: int) -> dict[str, object]:
    if now_ms != state.elapsed_ms:
        raise CoreValidationError("state_not_advanced")
    a = state.artifact
    return dict(
        game_id=state.game_id,
        identities=thaw(a.identities),
        mode=a.mode,
        elapsed_ms=now_ms,
        status="over" if state.end_reason else "active",
        board=list(state.board),
        target=state.target,
        score=state.score,
        clears=state.clears,
        level=1 + state.clears // 5,
        revision=state.revision,
        next_spawn_index=state.next_spawn_index,
        next_spawn_ms=(
            a.schedule[state.next_spawn_index]["at_ms"]
            if not state.end_reason and state.next_spawn_index < len(a.schedule)
            else None
        ),
        deadline_ms=a.deadline_ms,
        capacity=a.capacity,
        zone_size=a.zone_size,
        pending=(
            dict(
                command_id=state.pending.command_id,
                target=state.pending.target,
                admitted_ms=state.pending.admitted_ms,
            )
            if state.pending
            else None
        ),
        end_reason=state.end_reason,
        entries={i: {"label": e["label"]} for i, e in a.entries.items()},
    )
