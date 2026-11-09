"""Semaphore's provisional Stage 1 experiment interfaces.

No game rules or embedding model are implemented by this baseline.
"""

from semaphore_core.ranking import FakeRanker, RankedEntry, Ranker

__all__ = ["FakeRanker", "RankedEntry", "Ranker"]
