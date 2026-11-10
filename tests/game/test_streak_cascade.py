from dataclasses import replace

import pytest
from tests.game.test_engine_service import binding

from semaphore_core.game import ClueCommand, advance, complete, initial_state, submit


def play(state, ranked, clue="a different association"):
    command = ClueCommand("c", state.revision, clue)
    admitted = submit(state, command, now_ms=0, inference_slot_available=True)
    return complete(
        admitted.state,
        command_id="c",
        now_ms=1,
        scores={i: float(len(ranked) - n) for n, i in enumerate(ranked)},
    )


def test_fifth_clear_sweeps_and_cascades_until_empty_without_duplicate_score():
    artifact, _ = binding("casual")
    state = replace(initial_state(artifact, game_id="s"), streak=4)
    result = play(state, sorted(state.board))
    assert result.receipt["strike"]
    assert result.receipt["clear_waves"][0] == sorted(state.board)[:3]
    assert len(result.receipt["clear_waves"]) == 4
    assert result.state.score == 600
    assert result.state.board == () and result.state.streak == 0
    assert result.state.next_spawn_index == 0  # Scheduled arrivals are not pulled forward.
    duplicate = complete(result.state, command_id="c", now_ms=2, scores={})
    assert duplicate.state.score == 600
    retry = submit(
        result.state,
        ClueCommand("c", 0, "a different association"),
        now_ms=2,
        inference_slot_available=True,
    )
    assert retry.receipt == result.receipt and retry.state.score == 600


def test_cascade_stops_at_target_outside_refilled_zone():
    artifact, _ = binding("casual")
    ids = sorted(artifact.entries)[:6]
    state = replace(initial_state(artifact, game_id="s"), board=tuple(ids), target=ids[0], streak=4)
    # One-word zone makes the newly selected lowest ID ineligible after the sweep.
    state = replace(state, artifact=replace(artifact, zone_size=1))
    result = play(state, [ids[0], ids[5], ids[1], ids[2], ids[3], ids[4]])
    assert result.state.target == ids[1]
    assert result.receipt["clear_waves"] == [[ids[0]]]
    assert result.state.score == 100


def test_cascade_checks_legality_for_new_target():
    artifact, _ = binding("casual")
    state = replace(initial_state(artifact, game_id="s"), streak=4)
    ids = sorted(state.board)
    result = play(state, ids, artifact.entries[ids[3]]["label"])
    assert result.receipt["clear_waves"] == [ids[:3]]
    assert result.state.target == ids[3]


@pytest.mark.parametrize("failure", ["miss", "illegal", "timeout", "inference"])
def test_failures_reset_streak(failure):
    artifact, _ = binding("casual")
    state = replace(initial_state(artifact, game_id="s"), streak=4)
    if failure == "miss":
        result = play(state, [i for i in state.board if i != state.target] + [state.target]).state
    else:
        clue = artifact.entries[state.target]["label"] if failure == "illegal" else "association"
        result = submit(
            state, ClueCommand("c", 0, clue), now_ms=0, inference_slot_available=True
        ).state
        if failure == "timeout":
            result = advance(result, now_ms=5000).state
        elif failure == "inference":
            result = complete(result, command_id="c", now_ms=1, scores=None).state
    assert result.streak == 0


def test_fourth_clear_is_target_only():
    artifact, _ = binding("casual")
    state = replace(initial_state(artifact, game_id="s"), streak=3)
    result = play(state, sorted(state.board))
    assert result.state.streak == 4 and result.state.score == 100
    assert not result.receipt["strike"]
