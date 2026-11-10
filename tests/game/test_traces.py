import json
from pathlib import Path

import pytest

from semaphore_core.trace import TraceReplay

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "path", sorted((ROOT / "fixtures/game_traces").glob("*.json")), ids=lambda p: p.stem
)
def test_authored_traces(path):
    trace = json.loads(path.read_text())
    replay = TraceReplay(trace)
    for event in trace["events"]:
        actual = replay.step(
            {k: v for k, v in event.items() if k not in ("expected_state", "expected_result")}
        )
        assert actual == {"result": event["expected_result"], "state": event["expected_state"]}
