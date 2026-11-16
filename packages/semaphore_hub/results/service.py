"""Private history and public exact-cohort projections with scoped cursors."""

import base64
import hashlib
import json
from dataclasses import asdict

from semaphore_core.verification import canonical
from semaphore_hub.games import SQLiteGames
from semaphore_hub.packs import SQLitePacks
from semaphore_hub.repositories import Game


def cursor_encode(scope, key):
    return (
        base64.urlsafe_b64encode(canonical([hashlib.sha256(scope.encode()).hexdigest()[:32], key]))
        .decode()
        .rstrip("=")
    )


def cursor_decode(scope, value):
    if not isinstance(value, str) or not 1 <= len(value) <= 200:
        raise ValueError("invalid cursor")
    try:
        body = json.loads(
            base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
        )
        if (
            not isinstance(body, list)
            or len(body) != 2
            or body[0] != hashlib.sha256(scope.encode()).hexdigest()[:32]
        ):
            raise ValueError()
        return body[1]
    except (ValueError, UnicodeError):
        raise ValueError("invalid cursor") from None


class ResultsService:
    def __init__(self, transactions):
        self.transactions = transactions

    def history(self, player_id, cursor=None, limit=20):
        self._limit(limit)
        scope = "history:" + player_id
        anchor = cursor_decode(scope, cursor) if cursor else None
        if anchor is not None and not isinstance(anchor, str):
            raise ValueError("invalid cursor")
        with self.transactions() as db:
            repo = SQLiteGames(db)
            rows = repo.history(player_id, anchor, limit + 1)
            items = [
                dict(
                    game_id=g.game_id,
                    cohort=asdict(repo.cohort(g)),
                    score=json.loads(g.snapshot_json)["score"],
                    completed_at=g.finished_at,
                    end_reason=g.end_reason,
                    competitive=g.end_reason != "interrupted",
                )
                for g in rows[:limit]
            ]
        return dict(
            items=items,
            next_cursor=cursor_encode(scope, rows[limit - 1].game_id)
            if len(rows) > limit
            else None,
        )

    def board(self, artifact_id, cursor=None, limit=20):
        self._limit(limit)
        with self.transactions() as db:
            repo = SQLiteGames(db)
            artifact = SQLitePacks(db).artifact(artifact_id)
            cohort = repo.cohort(Game("", None, artifact, "{}", 0, "{}", 0))
            scope = canonical(asdict(cohort)).decode()
            anchor = cursor_decode(scope, cursor) if cursor else None
            if anchor is not None and (
                not isinstance(anchor, list)
                or len(anchor) != 3
                or type(anchor[0]) is not int
                or type(anchor[1]) is not int
                or not 0 <= anchor[0] <= 9223372036854775807
                or not 0 <= anchor[1] <= 9223372036854775807
                or not isinstance(anchor[2], str)
            ):
                raise ValueError("invalid cursor")
            rows = repo.board(cohort, anchor, limit + 1)
        items = [
            dict(
                game_id=s.game_id,
                display_name=s.display_name or "Deleted player",
                score=s.score,
                completed_at=s.completed_at,
            )
            for s in rows[:limit]
        ]
        last = rows[limit - 1] if len(rows) > limit else None
        return dict(
            cohort=asdict(cohort),
            items=items,
            next_cursor=cursor_encode(scope, [last.score, last.completed_at, last.game_id])
            if last
            else None,
        )

    @staticmethod
    def _limit(limit):
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("invalid limit")
