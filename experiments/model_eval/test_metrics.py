"""Boundary tests for benchmark arithmetic, independent of model packages."""

import copy
import hashlib
import unittest

from run import ROOT, percentile, rank, read_json, summarize, validate


class MetricTests(unittest.TestCase):
    def test_ties_use_id_and_highest_score_is_rank_one(self):
        self.assertEqual(rank("a", ["z", "a", "x"], [0.5, 0.5, -0.1])[0], 1)
        self.assertEqual(rank("x", ["z", "a", "x"], [0.5, 0.5, -0.1])[0], 3)

    def test_nonfinite_and_duplicate_scores_fail(self):
        for ids, scores in [
            (["a"], [float("nan")]),
            (["a", "a"], [1, 2]),
            (["a"], []),
            (["a"], [float("inf")]),
        ]:
            with self.assertRaises(ValueError):
                rank("a", ids, scores)

    def test_top3_boundary_and_nearest_rank_percentile(self):
        result = summarize([1, 3, 4, 20])
        self.assertEqual(result["top3_rate"], 0.5)
        self.assertEqual(result["median_rank"], 3.5)
        self.assertEqual(percentile(list(range(1, 101)), 0.95), 95)

    def test_fixture_and_split_leakage_detection(self):
        fixture = read_json(ROOT / "fixtures/semantic/fixture.json")
        self.assertEqual(validate(fixture)["held_out_targets"], 60)
        invalid = copy.deepcopy(fixture)
        invalid["cases"][0]["split"] = "calibration"
        with self.assertRaises(AssertionError):
            validate(invalid)

    def test_fixture_canonical_bytes_match_frozen_digest(self):
        directory = ROOT / "fixtures/semantic"
        content = (directory / "fixture.json").read_bytes()
        self.assertNotIn(b"\r", content)
        self.assertEqual(
            hashlib.sha256(content).hexdigest(),
            (directory / "fixture.sha256").read_text().strip(),
        )


if __name__ == "__main__":
    unittest.main()
