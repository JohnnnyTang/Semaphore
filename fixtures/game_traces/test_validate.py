"""Negative checks for specification fixtures, independent of a future engine."""

import json
import unittest
from pathlib import Path

from validate import illegal, validate

HERE = Path(__file__).parent


def fixture(name: str) -> dict:
    return json.loads((HERE / f"{name}.json").read_text(encoding="utf-8"))


class FixtureChecks(unittest.TestCase):
    def test_every_static_expected_state(self) -> None:
        for path in HERE.glob("*.json"):
            with self.subTest(trace=path.name):
                validate(json.loads(path.read_text(encoding="utf-8")))

    def test_wrong_score_does_not_pass(self) -> None:
        trace = fixture("exact-ties-and-miss")
        trace["events"][-1]["expected_state"]["score"] = 200
        with self.assertRaises(AssertionError):
            validate(trace)

    def test_wrong_target_does_not_pass(self) -> None:
        trace = fixture("exact-ties-and-miss")
        trace["events"][-1]["expected_state"]["target"] = "c"
        with self.assertRaises(AssertionError):
            validate(trace)

    def test_missing_due_spawn_does_not_pass(self) -> None:
        trace = fixture("inference-spawn-retry-and-reconnect")
        trace["events"] = [event for event in trace["events"] if event["kind"] != "spawn"]
        with self.assertRaises(AssertionError):
            validate(trace)

    def test_clue_before_same_time_spawn_does_not_pass(self) -> None:
        trace = fixture("equal-time-overflow-beats-inference")
        trace["events"][1], trace["events"][2] = trace["events"][2], trace["events"][1]
        with self.assertRaises(AssertionError):
            validate(trace)

    def test_reusing_an_entry_does_not_pass(self) -> None:
        trace = fixture("empty-board-waits-for-event")
        trace["schedule"][0]["entry_id"] = "a"
        with self.assertRaises(AssertionError):
            validate(trace)

    def test_illegal_match_is_a_phrase_not_a_substring(self) -> None:
        car = {"label": "car", "inflections": ["cars"]}
        self.assertEqual(illegal("CARS!", car), "clue_forbidden")
        self.assertIsNone(illegal("carpet", car))
        self.assertEqual(illegal("an oxbow, lake", {"label": "oxbow lake"}), "clue_forbidden")
        self.assertIsNone(illegal("oxbow on a lake", {"label": "oxbow lake"}))


if __name__ == "__main__":
    unittest.main()
