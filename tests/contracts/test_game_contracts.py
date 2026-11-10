"""Independent schema, cross-field and source-trace checks for W3 wire examples."""

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "contracts/events.schema.json").read_text())
VALIDATOR = Draft202012Validator(SCHEMA)
FIXTURES = sorted((ROOT / "fixtures/protocol").glob("*.json"))


def invariant(envelope):
    VALIDATOR.validate(envelope)
    state = envelope["snapshot"]
    board = state["board"]
    assert state["zone_size"] < state["capacity"]
    assert len(board) <= state["capacity"]
    assert state["score"] == state["clears"] * 100
    assert state["level"] == 1 + state["clears"] // 5
    assert (state["target"] in board) if board else state["target"] is None
    if state["status"] == "active":
        assert len(board) < state["capacity"]
    if state["end_reason"] == "overflow":
        assert len(board) == state["capacity"]
    if state["pending"]:
        assert state["pending"]["target"] == state["target"]
    receipt = envelope["receipt"]
    if receipt:
        assert receipt["applied_revision"] <= state["revision"]
        if receipt["outcome"] in ("clear", "miss"):
            assert receipt["ranked_board"][receipt["target_rank"] - 1] == receipt["target"]
            assert (receipt["target_rank"] <= state["zone_size"]) == (receipt["outcome"] == "clear")


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.stem)
def test_protocol_promotes_independent_game_trace(path):
    fixture = json.loads(path.read_text())
    trace = json.loads((ROOT / "fixtures/game_traces" / fixture["source_trace"]).read_text())
    expected = [trace["initial_state"]] + [e["expected_state"] for e in trace["events"]]
    assert len(fixture["envelopes"]) == len(expected)
    revision = 0
    final_receipts = {}
    for sequence, (envelope, source) in enumerate(zip(fixture["envelopes"], expected, strict=True)):
        invariant(envelope)
        assert envelope["sequence"] == sequence
        state = envelope["snapshot"]
        assert state["revision"] >= revision
        revision = state["revision"]
        assert {key: state[key] for key in source} == source
        receipt = envelope["receipt"]
        if receipt and receipt["outcome"] not in ("pending", "command_conflict"):
            cid = receipt["command_id"]
            if cid in final_receipts:
                assert final_receipts[cid] == receipt
            final_receipts[cid] = receipt


def test_schema_documents_and_http_operations():
    assert len(FIXTURES) == 10
    for name in ("events.schema.json", "http.schema.json"):
        Draft202012Validator.check_schema(json.loads((ROOT / "contracts" / name).read_text()))
    api = json.loads((ROOT / "contracts/openapi.json").read_text())
    assert api["openapi"] == "3.1.0"
    for path, methods in api["paths"].items():
        assert path.startswith("/experiment/v1/games")
        for operation in methods.values():
            refs = [
                r["content"]["application/json"]["schema"]["$ref"]
                for r in operation["responses"].values()
            ]
            for reference in refs:
                filename, _, fragment = reference.partition("#/$defs/")
                document = json.loads((ROOT / "contracts" / filename).read_text())
                assert not fragment or fragment in document["$defs"]


@pytest.mark.parametrize(
    "mutation",
    [
        "terminal_pending",
        "active_reason",
        "duplicate",
        "score",
        "target",
        "capacity",
        "rank",
        "future_receipt",
    ],
)
def test_rejects_plausible_but_invalid_state(mutation):
    fixture = json.loads((ROOT / "fixtures/protocol/bottom-three-target-only.json").read_text())
    envelope = copy.deepcopy(fixture["envelopes"][-1])
    state = envelope["snapshot"]
    if mutation == "terminal_pending":
        state.update(
            status="over",
            end_reason="interrupted",
            pending={"command_id": "bad", "target": state["target"], "admitted_ms": 0},
        )
    elif mutation == "active_reason":
        state["end_reason"] = "overflow"
    elif mutation == "duplicate":
        state["board"].append(state["board"][0])
    elif mutation == "score":
        state["score"] += 100
    elif mutation == "target":
        state["target"] = "missing"
    elif mutation == "capacity":
        state["capacity"] = len(state["board"])
    elif mutation == "rank":
        envelope["receipt"]["target_rank"] = 1
    else:
        envelope["receipt"]["applied_revision"] = 999
    with pytest.raises((AssertionError, ValidationError)):
        invariant(envelope)


@pytest.mark.parametrize(
    "payload,valid",
    [
        ({"command_id": "c1", "expected_revision": 0, "clue": "ice"}, True),
        ({"command_id": "c1", "expected_revision": 0, "clue": ""}, True),
        ({"command_id": "c1", "expected_revision": 0, "clue": "x" * 121}, True),
        ({"command_id": "c1", "expected_revision": -1, "clue": "ice"}, False),
        ({"command_id": "c1", "expected_revision": 0, "clue": "ice", "score": 100}, False),
        ({"command_id": "c1", "clue": "ice"}, False),
    ],
)
def test_command_boundary_preserves_game_rejections(payload, valid):
    schema = json.loads((ROOT / "contracts/http.schema.json").read_text())
    validator = Draft202012Validator(schema["$defs"]["command"])
    assert validator.is_valid(payload) == valid


def test_terminal_spawn_immediately_resolves_pending_before_worker():
    fixture = json.loads(
        (ROOT / "fixtures/protocol/equal-time-overflow-beats-inference.json").read_text()
    )
    admitted, ended, retry, completed = fixture["envelopes"][1:5]
    assert admitted["receipt"]["outcome"] == "pending"
    assert ended["snapshot"]["pending"] is None
    assert ended["receipt"]["outcome"] == "game_over"
    assert ended["receipt"] == retry["receipt"] == completed["receipt"]
    assert ended["snapshot"]["revision"] == completed["snapshot"]["revision"]
    assert ended["snapshot"]["score"] == completed["snapshot"]["score"] == 0
