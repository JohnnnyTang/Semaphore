"""Arcade capacity, rank boundaries, and score-dependent timing."""

import json
from dataclasses import replace
from pathlib import Path

import pytest
from experiments.game_server.generate_practice import recording
from jsonschema import Draft202012Validator
from tests.game.test_engine_service import binding

from semaphore_core.game import ClueCommand, advance, complete, initial_state, snapshot, submit


def load(name):
    return json.loads(Path(name).read_text())


def test_casual_capacity_and_event_compatibility():
    casual, _ = binding("casual")
    event, _ = binding("event")
    assert (casual.capacity, casual.zone_size, casual.score_pacing) == (20, 3, True)
    assert (event.capacity, event.zone_size, event.score_pacing) == (12, 3, False)
    assert casual.identities["config_digest"] != event.identities["config_digest"]


@pytest.mark.parametrize("rank,clears", [(1, True), (2, True), (3, True), (4, False)])
def test_clear_zone_boundary(rank, clears):
    artifact, _ = binding("casual")
    state = initial_state(artifact, game_id="range")
    admitted = submit(
        state,
        ClueCommand("c", 0, "a different association"),
        now_ms=0,
        inference_slot_available=True,
    )
    ordered = [i for i in state.board if i != state.target]
    ordered.insert(rank - 1, state.target)
    result = complete(
        admitted.state,
        command_id="c",
        now_ms=10,
        scores={i: float(len(ordered) - j) for j, i in enumerate(ordered)},
    )
    assert result.receipt["target_rank"] == rank
    assert result.receipt["outcome"] == ("clear" if clears else "miss")
    assert result.state.score == (100 if clears else 0)
    assert len(result.state.board) == len(state.board) - int(clears)


def test_level_crossing_accelerates_remaining_arrival_and_future_gaps():
    artifact, _ = binding("casual")
    state = replace(initial_state(artifact, game_id="pace"), clears=4, score=400)
    admitted = submit(
        state,
        ClueCommand("c", 0, "a different association"),
        now_ms=900,
        inference_slot_available=True,
    )
    result = complete(
        admitted.state,
        command_id="c",
        now_ms=1000,
        scores={i: 1.0 if i == state.target else 0.0 for i in state.board},
    )
    assert result.state.score == 500
    assert snapshot(result.state, now_ms=1000)["next_spawn_ms"] == 4600
    before = advance(result.state, now_ms=4599).state
    assert before.next_spawn_index == 0
    after = advance(before, now_ms=4600).state
    assert after.next_spawn_index == 1
    assert snapshot(after, now_ms=4600)["next_spawn_ms"] == 9100


def test_pacing_has_a_floor_and_overflow_stays_authoritative():
    artifact, _ = binding("casual")
    state = replace(initial_state(artifact, game_id="fast"), clears=100, score=10000)
    state = advance(state, now_ms=5000).state
    assert snapshot(state, now_ms=5000)["next_spawn_ms"] == 7000
    # A board one below the limit terminates on the next scheduled arrival.
    artifact = replace(artifact, capacity=7)
    state = advance(initial_state(artifact, game_id="full"), now_ms=5000).state
    assert state.end_reason == "overflow"
    assert len(state.board) == 7


def test_practice_recording_is_current_and_schema_valid():
    data = recording()
    assert data == load("web/practice/spacious-arcade.json")
    validator = Draft202012Validator(load("contracts/events.schema.json"))
    for envelope in data["envelopes"]:
        validator.validate(envelope)
    assert data["envelopes"][0]["snapshot"]["capacity"] == 20
    assert data["envelopes"][-1]["snapshot"]["score"] == 1200
