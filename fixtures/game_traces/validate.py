"""Replay static W2 expected states against a small, fixture-only rules oracle.

This is specification scaffolding, not a production engine. Run from any cwd:
  python fixtures/game_traces/validate.py
It uses the existing W1 FakeRanker; no embedding dependencies or network needed.
"""

from __future__ import annotations

import json
import sys
import unicodedata
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages"))

from semaphore_core import FakeRanker  # noqa: E402


def tokens(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return "".join(c if c.isalnum() else " " for c in normalized).split()


def illegal(clue: str, entry: dict) -> str | None:
    if len(clue) > 120:
        return "clue_too_long"
    if any(unicodedata.category(c).startswith("C") and c not in "\t\n\r" for c in clue):
        return "clue_control_character"
    words = tokens(clue)
    if not words:
        return "clue_empty"
    forms = [entry["label"], *entry.get("aliases", []), *entry.get("forbidden", [])]
    forms += entry.get("inflections", [])
    for form in forms:
        phrase = tokens(form)
        if phrase and any(
            words[start : start + len(phrase)] == phrase for start in range(len(words))
        ):
            return "clue_forbidden"
    return None


def apply(trace: dict, state: dict, receipts: dict, event: dict) -> str:
    kind = event["kind"]
    if kind in {"read", "disconnect", "reconnect"}:
        return "snapshot"
    if kind == "admit":
        command_id = event["command_id"]
        payload = [event["clue"], event["expected_revision"]]
        if command_id in receipts:
            previous = receipts[command_id]
            return previous["result"] if previous["payload"] == payload else "command_conflict"
        reason = None
        if state["status"] == "over":
            reason = "game_over"
        elif state["pending"]:
            reason = "busy"
        elif event["expected_revision"] != state["revision"]:
            reason = "stale_revision"
        elif state["target"] is None:
            reason = "no_target"
        else:
            reason = illegal(event["clue"], trace["entries"][state["target"]])
        receipts[command_id] = {"payload": payload, "result": reason or "pending"}
        if reason:
            return reason
        state["pending"] = {
            "command_id": command_id,
            "target": state["target"],
            "admitted_ms": event["at_ms"],
        }
        state["revision"] += 1
        return "pending"
    if kind in {"complete", "fail"}:
        command_id = event["command_id"]
        if state["status"] == "over":
            assert command_id in receipts
            receipts[command_id]["result"] = "game_over"
            return "game_over"
        assert state["pending"] and state["pending"]["command_id"] == command_id
        target = state["pending"]["target"]
        state["pending"] = None
        state["revision"] += 1
        if kind == "fail":
            result = "inference_failed"
        else:
            clue = receipts[command_id]["payload"][0]
            ranker = FakeRanker({clue: event["scores"]})
            ranked = [item.entry_id for item in ranker.rank(clue, state["board"])]
            state["board"] = ranked
            if ranked.index(target) < trace["config"]["zone_size"]:
                state["board"].remove(target)
                state["score"] += 100
                state["clears"] += 1
                state["level"] = 1 + state["clears"] // 5
                state["target"] = min(state["board"], default=None)
                result = "clear"
                if (
                    trace["mode"] == "casual"
                    and not state["board"]
                    and state["next_spawn_index"] == len(trace["schedule"])
                ):
                    state["status"] = "over"
                    state["end_reason"] = "pack_cleared"
            else:
                result = "miss"
        receipts[command_id]["result"] = result
        return result
    if state["status"] == "over":
        return "ignored_terminal"
    if kind == "spawn":
        scheduled = trace["schedule"][state["next_spawn_index"]]
        assert scheduled == {"at_ms": event["at_ms"], "entry_id": event["entry_id"]}
        assert event["entry_id"] not in state["board"]
        state["next_spawn_index"] += 1
        state["board"].append(event["entry_id"])
        if state["target"] is None:
            state["target"] = event["entry_id"]
        state["revision"] += 1
        if len(state["board"]) == trace["config"]["capacity"]:
            state["status"] = "over"
            state["end_reason"] = "overflow"
            if state["pending"]:
                receipts[state["pending"]["command_id"]]["result"] = "game_over"
            state["pending"] = None
        return "overflow" if state["status"] == "over" else "spawn"
    if kind == "deadline":
        assert event["at_ms"] == trace["deadline_ms"]
        state["status"] = "over"
        state["end_reason"] = "event_complete" if trace["mode"] == "event" else "pack_exhausted"
        if state["pending"]:
            receipts[state["pending"]["command_id"]]["result"] = "game_over"
        state["pending"] = None
        state["revision"] += 1
        return state["end_reason"]
    raise AssertionError(f"unknown fixture event {kind}")


def validate(trace: dict) -> int:
    assert trace["fixture_version"] == "s1-w2-game-trace-1"
    assert trace["provenance"] == "synthetic-author-authored; MIT"
    state = deepcopy(trace["initial_state"])
    receipts: dict = {}
    assert state["target"] == min(state["board"], default=None)
    assert 1 <= trace["config"]["zone_size"] < trace["config"]["capacity"]
    assert 0 < len(state["board"]) < trace["config"]["capacity"]
    all_ids = state["board"] + [spawn["entry_id"] for spawn in trace["schedule"]]
    assert len(all_ids) == len(set(all_ids)), "a pack entry cannot be reused"
    assert set(all_ids) <= trace["entries"].keys()
    spawn_times = [spawn["at_ms"] for spawn in trace["schedule"]]
    assert spawn_times == sorted(set(spawn_times)), "spawn times must strictly increase"
    assert all(0 < time < trace["deadline_ms"] for time in spawn_times)
    previous = (-1, -1)
    scheduled_seen = 0
    deadline_seen = False
    for index, event in enumerate(trace["events"]):
        priority = {"deadline": 0, "spawn": 1}.get(event["kind"], 2)
        current = (event["at_ms"], priority)
        assert current >= previous, "events must follow timestamp and system priority"
        previous = current
        if state["status"] == "active" and event["kind"] not in {"spawn", "deadline"}:
            if scheduled_seen < len(trace["schedule"]):
                assert trace["schedule"][scheduled_seen]["at_ms"] > event["at_ms"], (
                    "missing due spawn before external input"
                )
            assert event["at_ms"] < trace["deadline_ms"] or deadline_seen
        if event["kind"] == "spawn":
            assert event["at_ms"] < trace["deadline_ms"]
            scheduled_seen += 1
        if event["kind"] == "deadline":
            if state["status"] == "active":
                assert scheduled_seen == len(trace["schedule"]), "missing spawn before deadline"
            deadline_seen = True
        actual_result = apply(trace, state, receipts, event)
        assert actual_result == event["expected_result"], (trace["scenario"], index, actual_result)
        assert state == event["expected_state"], (
            f"{trace['scenario']} event {index}:\n"
            f"actual {json.dumps(state, sort_keys=True)}\n"
            f"expected {json.dumps(event['expected_state'], sort_keys=True)}"
        )
    return len(trace["events"])


def main() -> None:
    traces = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(Path(__file__).parent.glob("*.json"))
    ]
    assert traces, "no trace fixtures found"
    count = sum(validate(trace) for trace in traces)
    paired = [trace for trace in traces if trace.get("challenge_id") == "shared-signal-1"]
    assert len(paired) == 2
    assert paired[0]["schedule"] == paired[1]["schedule"]
    assert paired[0]["initial_state"] == paired[1]["initial_state"]
    assert paired[0]["deadline_ms"] == paired[1]["deadline_ms"]
    assert paired[0]["config"] == paired[1]["config"]
    assert paired[0]["entries"] == paired[1]["entries"]
    assert (
        paired[0]["events"][-1]["expected_state"]["board"]
        != (paired[1]["events"][-1]["expected_state"]["board"])
    )
    print(f"Validated {len(traces)} traces, {count} event states, and shared schedule pair.")


if __name__ == "__main__":
    main()
