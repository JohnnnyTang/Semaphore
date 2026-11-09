"""Smoke and boundary checks for the installed provisional package."""

from importlib.metadata import version

import pytest

from semaphore_core import FakeRanker, RankedEntry, Ranker


def test_installed_package_and_scripted_ranking() -> None:
    assert version("semaphore-core") == "0.0.1"
    ranker: Ranker = FakeRanker({"ice": {"glacier": 0.9, "lake": 0.4, "desert": -0.2}})

    assert ranker.rank("ice", ["desert", "glacier", "lake"]) == (
        RankedEntry("glacier", 0.9),
        RankedEntry("lake", 0.4),
        RankedEntry("desert", -0.2),
    )


def test_ties_are_stable_across_candidate_order_and_fixture_mutation() -> None:
    scores = {"water": {"lake": 0.5, "glacier": 0.5}}
    ranker = FakeRanker(scores)
    scores["water"]["lake"] = 1.0
    expected = (RankedEntry("glacier", 0.5), RankedEntry("lake", 0.5))

    assert ranker.rank("water", ["lake", "glacier"]) == expected
    assert ranker.rank("water", ["glacier", "lake"]) == expected


def test_candidate_subset_and_empty_candidates() -> None:
    ranker = FakeRanker({"ice": {"glacier": 0.9, "lake": 0.4}})
    assert ranker.rank("ice", ["lake"]) == (RankedEntry("lake", 0.4),)
    assert ranker.rank("ice", []) == ()


def test_missing_fixture_data_fails_instead_of_inventing_scores() -> None:
    ranker = FakeRanker({"ice": {"glacier": 0.9}})
    with pytest.raises(KeyError):
        ranker.rank("ice", ["lake"])
    with pytest.raises(KeyError):
        ranker.rank("unknown clue", [])


def test_duplicate_candidates_are_rejected() -> None:
    ranker = FakeRanker({"ice": {"glacier": 0.9}})
    with pytest.raises(ValueError, match="unique"):
        ranker.rank("ice", ["glacier", "glacier"])


@pytest.mark.parametrize("score", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_fixture_scores_are_rejected(score: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        FakeRanker({"ice": {"glacier": score}})
