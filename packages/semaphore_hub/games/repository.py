"""Transaction-scoped durable game adapters; callers own locks and commits."""

import json
from dataclasses import astuple

from semaphore_hub.packs import SQLitePacks
from semaphore_hub.policy import RECEIPT_RETENTION_MS
from semaphore_hub.repositories import Cohort, Command, Conflict, Game, NotFound, Score


class SQLiteGames:
    def __init__(self, connection):
        self.db = connection

    def _game(self, row):
        if row is None:
            raise NotFound("game")
        return Game(row[0], row[1], SQLitePacks(self.db).artifact(row[2]), *row[3:])

    def for_recovery(self, game_id):
        return self._game(
            self.db.execute(
                "SELECT game_id,player_id,artifact_id,model_identity_json,revision,snapshot_json,"
                "started_at,finished_at,end_reason FROM games WHERE game_id=?",
                (game_id,),
            ).fetchone()
        )

    def owned(self, game_id, player_id):
        game = self.for_recovery(game_id)
        if game.player_id != player_id or player_id is None:
            raise NotFound("game")
        return game

    def current(self, player_id):
        row = self.db.execute(
            "SELECT game_id FROM games WHERE player_id=? AND status='active'", (player_id,)
        ).fetchone()
        return self.for_recovery(row[0]) if row else None

    def active_ids(self):
        return tuple(
            r[0]
            for r in self.db.execute(
                "SELECT game_id FROM games WHERE status='active' ORDER BY game_id"
            )
        )

    def create(self, game):
        if self.current(game.player_id):
            raise Conflict("active game exists")
        if not self.db.execute(
            "SELECT 1 FROM accounts WHERE account_id=? AND deleted_at IS NULL", (game.player_id,)
        ).fetchone():
            raise NotFound("account")
        a = game.artifact
        self.db.execute(
            "INSERT INTO games VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                game.game_id,
                game.player_id,
                a.version_id,
                a.mode,
                a.fingerprint_hash,
                game.model_identity_json,
                a.ruleset_id,
                a.config_digest,
                a.config_json,
                a.artifact_id,
                a.challenge_digest,
                game.revision,
                "active",
                game.started_at,
                None,
                None,
                game.snapshot_json,
            ),
        )

    def receipt(self, game_id, command_id, player_id):
        self.owned(game_id, player_id)
        row = self.db.execute(
            "SELECT game_id,command_id,payload_hmac,hmac_key_version,received_at,"
            "receipt_json,state,expires_at FROM commands WHERE game_id=? AND "
            "command_id=?",
            (game_id, command_id),
        ).fetchone()
        if row is None:
            raise NotFound("receipt")
        return Command(*row[:6], row[6] == "final", row[7])

    def admit(self, player_id, command, attempt):
        game = self.owned(command.game_id, player_id)
        if (attempt.game_id, attempt.command_id) != (command.game_id, command.command_id):
            raise Conflict("attempt identity")
        try:
            old = self.receipt(command.game_id, command.command_id, player_id)
        except NotFound:
            old = None
        if old:
            if (old.payload_hmac, old.hmac_key_version) != (
                command.payload_hmac,
                command.hmac_key_version,
            ):
                raise Conflict("command conflict")
            return old
        if game.finished_at is not None and not command.final:
            raise Conflict("terminal admission")
        self.db.execute(
            "INSERT INTO commands VALUES (?,?,?,?,?,?,?,?)",
            (
                command.game_id,
                command.command_id,
                command.payload_hmac,
                command.hmac_key_version,
                command.received_at,
                "final" if command.final else "pending",
                command.receipt_json,
                game.finished_at + RECEIPT_RETENTION_MS if game.finished_at is not None else None,
            ),
        )
        self.db.execute("INSERT INTO clue_attempts VALUES (?,?,?,?,?,?,?,?)", astuple(attempt))
        return command

    def finalize_command(self, player_id, command):
        old = self.receipt(command.game_id, command.command_id, player_id)
        if old.final:
            if old.receipt_json != command.receipt_json:
                raise Conflict("immutable receipt")
            return
        if not command.final:
            raise Conflict("completion must be final")
        self.db.execute(
            "UPDATE commands SET state='final',receipt_json=? WHERE game_id=? AND command_id=?",
            (command.receipt_json, command.game_id, command.command_id),
        )
        receipt = json.loads(command.receipt_json)
        self.db.execute(
            "UPDATE clue_attempts SET resolved_at=?,outcome=?,target_rank=? WHERE"
            " game_id=? AND command_id=?",
            (
                command.received_at,
                receipt["outcome"],
                receipt["target_rank"],
                command.game_id,
                command.command_id,
            ),
        )

    def save_transition(self, player_id, game):
        old = self.owned(game.game_id, player_id)
        if (
            old.finished_at is not None
            or old.artifact != game.artifact
            or old.started_at != game.started_at
            or old.player_id != game.player_id
            or old.model_identity_json != game.model_identity_json
            or old.revision > game.revision
        ):
            raise Conflict("immutable game")
        self.db.execute(
            "UPDATE games SET "
            "revision=?,snapshot_json=?,status=?,finished_at=?,end_reason=? WHERE"
            " game_id=?",
            (
                game.revision,
                game.snapshot_json,
                "over" if game.finished_at is not None else "active",
                game.finished_at,
                game.end_reason,
                game.game_id,
            ),
        )

    def resolve(self, player_id, game, command, attempt):
        old = self.receipt(game.game_id, command.command_id, player_id)
        if old.final:
            if old.receipt_json != command.receipt_json:
                raise Conflict("immutable receipt")
            return
        self.finalize_command(player_id, command)
        self.save_transition(player_id, game)
        self.db.execute(
            "UPDATE clue_attempts SET resolved_at=?,outcome=?,target_rank=? WHERE"
            " game_id=? AND command_id=?",
            (
                attempt.resolved_at,
                attempt.outcome,
                attempt.target_rank,
                game.game_id,
                command.command_id,
            ),
        )

    def cohort(self, game):
        a = game.artifact
        row = self.db.execute(
            "SELECT pack_id,version,manifest_digest FROM pack_versions WHERE version_id=?",
            (a.version_id,),
        ).fetchone()
        return Cohort(
            a.mode, *row, a.fingerprint_hash, a.ruleset_id, a.config_digest, a.challenge_digest
        )

    def finish(self, player_id, game, score, pending):
        old = self.owned(game.game_id, player_id)
        if old.finished_at is not None:
            return old
        if game.finished_at is None or (game.end_reason == "interrupted") != (score is None):
            raise Conflict("terminal result")
        if score is not None and (
            score.game_id != game.game_id
            or score.player_id != player_id
            or score.cohort != self.cohort(game)
            or score.completed_at != game.finished_at
            or score.score != json.loads(game.snapshot_json)["score"]
        ):
            raise Conflict("score binding")
        required = {
            r[0]
            for r in self.db.execute(
                "SELECT command_id FROM commands WHERE game_id=? AND state='pending'",
                (game.game_id,),
            )
        }
        if any(c.game_id != game.game_id or not c.final for c in pending) or not required.issubset(
            {c.command_id for c in pending}
        ):
            raise Conflict("unsettled terminal receipt")
        self.save_transition(player_id, game)
        for command in pending:
            self.finalize_command(player_id, command)
        if score is not None:
            self.db.execute("INSERT INTO scores VALUES (?,?,?,?,?)", astuple(score)[:5])
        self.db.execute(
            "UPDATE commands SET expires_at=? WHERE game_id=?",
            (game.finished_at + RECEIPT_RETENTION_MS, game.game_id),
        )
        return game

    def history(self, player_id, after_game_id, limit):
        anchor = self.owned(after_game_id, player_id) if after_game_id else None
        if anchor and anchor.finished_at is None:
            raise Conflict("nonterminal cursor")
        rows = self.db.execute(
            "SELECT game_id FROM games WHERE player_id=? AND status='over' "
            + ("AND (finished_at<? OR (finished_at=? AND game_id>?)) " if anchor else "")
            + "ORDER BY finished_at DESC,game_id COLLATE BINARY LIMIT ?",
            (
                player_id,
                *((anchor.finished_at, anchor.finished_at, anchor.game_id) if anchor else ()),
                limit,
            ),
        )
        return tuple(self.for_recovery(r[0]) for r in rows)

    def board(self, cohort, after, limit):
        query = (
            "SELECT s.game_id,s.player_id,s.display_name,s.score,s.completed_at "
            "FROM scores s JOIN games g USING(game_id) JOIN pack_versions v "
            "USING(version_id) WHERE g.mode=? AND v.pack_id=? AND v.version=? AND"
            " v.manifest_digest=? AND g.fingerprint_hash=? AND g.ruleset_id=? AND"
            " g.config_digest=? AND g.challenge_digest IS ? "
        )
        args = list(astuple(cohort))
        if after:
            query += (
                "AND (s.score<? OR (s.score=? AND (s.completed_at>? OR "
                "(s.completed_at=? AND s.game_id>?)))) "
            )
            args += [after[0], after[0], after[1], after[1], after[2]]
        query += "ORDER BY s.score DESC,s.completed_at,s.game_id COLLATE BINARY LIMIT ?"
        return tuple(Score(*r, cohort) for r in self.db.execute(query, (*args, limit)))
