"""Explicit scripted rankings for experiment design, not semantic evaluation.

This interface is provisional until Stage 1 Wave 3. Rankings list the most
related entry first; a future browser may display that entry at the bottom.
The fake deliberately has no normalization, legality, game, or model policy.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite
from typing import Protocol


@dataclass(frozen=True)
class RankedEntry:
    """An entry identity and a scripted similarity score."""

    entry_id: str
    score: float


class Ranker(Protocol):
    """Rank unique candidate IDs for a clue; highest score is first."""

    def rank(self, clue: str, entry_ids: Sequence[str]) -> tuple[RankedEntry, ...]: ...


class FakeRanker:
    """Replay caller-authored scores, failing on missing fixture data.

    Scores are copied on construction so mutation of the source fixture cannot
    alter a run. Exact ties use ascending entry ID, independent of input order.
    This tie policy is for the fake only, not a frozen production rule.
    """

    def __init__(self, scores: Mapping[str, Mapping[str, float]]) -> None:
        self._scores: dict[str, dict[str, float]] = {}
        for clue, entries in scores.items():
            self._scores[clue] = {}
            for entry_id, score in entries.items():
                if not isfinite(score):
                    raise ValueError("fixture scores must be finite")
                self._scores[clue][entry_id] = float(score)

    def rank(self, clue: str, entry_ids: Sequence[str]) -> tuple[RankedEntry, ...]:
        """Return scripted results; reject duplicates and unknown inputs.

        Unknown clues or entry IDs raise KeyError even for an empty candidate
        list, so a typo in a trace never silently becomes a plausible ranking.
        """
        if len(set(entry_ids)) != len(entry_ids):
            raise ValueError("candidate entry IDs must be unique")
        scores = self._scores[clue]
        ranked = (RankedEntry(entry_id, scores[entry_id]) for entry_id in entry_ids)
        return tuple(sorted(ranked, key=lambda entry: (-entry.score, entry.entry_id)))
