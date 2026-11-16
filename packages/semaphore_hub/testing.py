"""Deterministic in-memory contract adapters. Not a security or durability backend."""

from copy import deepcopy
from dataclasses import replace

from .repositories import (
    Account,
    Artifact,
    Attempt,
    Cohort,
    Command,
    Conflict,
    Deletion,
    Game,
    Installation,
    NotFound,
    Publication,
    Score,
    Session,
    VectorCache,
)

DAY = 86_400_000


class FakeAccounts:
    def __init__(self):
        self.rows: dict[str, Account] = {}
        self.sessions: dict[str, Session] = {}

    def create(self, account: Account) -> None:
        if account.account_id in self.rows or self.by_login(account.login_name):
            raise Conflict("account exists")
        self.rows[account.account_id] = account

    def by_id(self, account_id: str) -> Account:
        try:
            return self.rows[account_id]
        except KeyError:
            raise NotFound("account") from None

    def by_login(self, normalized_login: str) -> Account | None:
        return next((a for a in self.rows.values() if a.login_name == normalized_login), None)

    def issue_session(self, session: Session) -> None:
        if session.account_id not in self.rows:
            raise NotFound("account")
        if session.token_digest in self.sessions:
            raise Conflict("session token")
        self.sessions[session.token_digest] = session

    def session(self, token_digest: str, now_ms: int, idle_ms: int) -> Session | None:
        session = self.sessions.get(token_digest)
        if session and now_ms < min(session.absolute_expires_at, session.last_seen_at + idle_ms):
            return session
        return None

    def touch_session(self, session_id: str, now_ms: int) -> None:
        for digest, session in self.sessions.items():
            if session.session_id == session_id:
                self.sessions[digest] = replace(session, last_seen_at=now_ms)
                return
        raise NotFound("session")

    def revoke_session(self, session_id: str) -> None:
        self.sessions = {k: v for k, v in self.sessions.items() if v.session_id != session_id}

    def revoke_all(self, account_id: str) -> None:
        self.sessions = {k: v for k, v in self.sessions.items() if v.account_id != account_id}

    def reset_password(self, account_id: str, password_hash: str) -> None:
        if account_id not in self.rows:
            raise NotFound("account")
        self.rows[account_id] = replace(self.rows[account_id], password_hash=password_hash)
        self.revoke_all(account_id)


class FakePacks:
    def __init__(self):
        self.owners: dict[str, str] = {}
        self.reservations: dict[str, Installation] = {}
        self.versions: dict[tuple[str, str], Publication] = {}
        self.artifacts: dict[str, Artifact] = {}
        self.caches: dict[tuple[str, str], VectorCache] = {}

    def reserve(self, installation: Installation) -> Installation:
        owner = self.owners.get(installation.pack_id)
        if owner is not None and owner != installation.owner_id:
            raise Conflict("owner conflict")
        key = (installation.pack_id, installation.version)
        previous = self.versions.get(key)
        if previous:
            if previous.installation.manifest_digest != installation.manifest_digest:
                raise Conflict("version conflict")
            return previous.installation
        for pending in self.reservations.values():
            if (pending.pack_id, pending.version) == key:
                if pending.manifest_digest != installation.manifest_digest:
                    raise Conflict("version conflict")
                return pending
        self.owners[installation.pack_id] = installation.owner_id
        self.reservations[installation.install_id] = installation
        return installation

    def release(self, install_id: str, owner_id: str) -> None:
        pending = self.reservations.get(install_id)
        if pending is None or pending.owner_id != owner_id:
            raise NotFound("installation")
        del self.reservations[install_id]

    def publish(self, publication: Publication) -> Publication:
        installation = publication.installation
        if self.owners.get(installation.pack_id) != installation.owner_id:
            raise Conflict("owner conflict")
        key = (installation.pack_id, installation.version)
        previous = self.versions.get(key)
        if previous:
            if previous.manifest_bytes != publication.manifest_bytes:
                raise Conflict("version conflict")
            return previous
        if self.reservations.get(installation.install_id) != installation:
            raise Conflict("reservation missing")
        self.versions[key] = publication
        del self.reservations[installation.install_id]
        return publication

    def published(self, pack_id: str, version: str) -> Publication:
        try:
            return self.versions[pack_id, version]
        except KeyError:
            raise NotFound("published version") from None

    def list_published(self, after_version_id: str | None, limit: int) -> tuple[Publication, ...]:
        def key(p):
            return (p.installation.pack_id, p.installation.version)

        anchor = next((p for p in self.versions.values() if p.version_id == after_version_id), None)
        if after_version_id is not None and anchor is None:
            raise NotFound("cursor version")
        return tuple(
            sorted(
                (p for p in self.versions.values() if anchor is None or key(p) > key(anchor)),
                key=key,
            )[:limit]
        )

    def add_artifact(self, artifact: Artifact) -> None:
        if artifact.artifact_id in self.artifacts:
            raise Conflict("artifact exists")
        if not any(p.version_id == artifact.version_id for p in self.versions.values()):
            raise NotFound("published version")
        self.artifacts[artifact.artifact_id] = artifact

    def artifact(self, artifact_id: str) -> Artifact:
        try:
            return self.artifacts[artifact_id]
        except KeyError:
            raise NotFound("artifact") from None

    def artifacts_for_version(self, version_id: str) -> tuple[Artifact, ...]:
        return tuple(a for a in self.artifacts.values() if a.version_id == version_id)

    def put_vectors(self, cache: VectorCache) -> None:
        key = (cache.vector_hash, cache.fingerprint_hash)
        if key in self.caches and self.caches[key] != cache:
            raise Conflict("immutable cache")
        self.caches[key] = cache

    def vectors(self, vector_hash: str, fingerprint_hash: str) -> VectorCache | None:
        return self.caches.get((vector_hash, fingerprint_hash))


class FakeGames:
    def __init__(self):
        self.rows: dict[str, Game] = {}
        self.commands: dict[tuple[str, str], Command] = {}
        self.attempts: dict[tuple[str, str], Attempt] = {}
        self.scores: dict[str, Score] = {}

    def create(self, game: Game) -> None:
        if game.game_id in self.rows or self.current(game.player_id) is not None:
            raise Conflict("game exists")
        self.rows[game.game_id] = game

    def current(self, player_id: str) -> Game | None:
        return next(
            (g for g in self.rows.values() if g.player_id == player_id and g.finished_at is None),
            None,
        )

    def owned(self, game_id: str, player_id: str) -> Game:
        game = self.rows.get(game_id)
        if game is None or game.player_id != player_id:
            raise NotFound("game")
        return game

    def receipt(self, game_id: str, command_id: str, player_id: str) -> Command:
        self.owned(game_id, player_id)
        try:
            return self.commands[game_id, command_id]
        except KeyError:
            raise NotFound("receipt") from None

    def admit(self, player_id: str, command: Command, attempt: Attempt) -> Command:
        game = self.owned(command.game_id, player_id)
        key = (command.game_id, command.command_id)
        old = self.commands.get(key)
        if old:
            if (old.payload_hmac, old.hmac_key_version) != (
                command.payload_hmac,
                command.hmac_key_version,
            ):
                raise Conflict("command conflict")
            return old
        if game.finished_at is not None:
            raise Conflict("game over")
        if (attempt.game_id, attempt.command_id) != key:
            raise Conflict("attempt identity")
        self.commands[key], self.attempts[key] = command, attempt
        return command

    def resolve(self, player_id: str, game: Game, command: Command, attempt: Attempt) -> None:
        old = self.receipt(game.game_id, command.command_id, player_id)
        if old.final:
            if old != command:
                raise Conflict("immutable receipt")
            return
        if not command.final:
            raise Conflict("completion must be final")
        self.save_transition(player_id, game)
        self.commands[game.game_id, command.command_id] = command
        self.attempts[game.game_id, command.command_id] = attempt

    def save_transition(self, player_id: str, game: Game) -> None:
        old = self.owned(game.game_id, player_id)
        if (
            old.finished_at is not None
            or old.artifact != game.artifact
            or old.started_at != game.started_at
        ):
            raise Conflict("immutable game")
        if game.revision < old.revision:
            raise Conflict("revision rewind")
        self.rows[game.game_id] = game

    def finish(
        self, player_id: str, game: Game, score: Score | None, pending: tuple[Command, ...]
    ) -> Game:
        old = self.owned(game.game_id, player_id)
        if old.finished_at is not None:
            return old
        if game.finished_at is None or (game.end_reason == "interrupted") != (score is None):
            raise Conflict("terminal result")
        self.save_transition(player_id, game)
        for command in pending:
            key = (game.game_id, command.command_id)
            previous = self.commands[key]
            if previous.final and previous != command:
                raise Conflict("immutable receipt")
            self.commands[key] = command
        if score is not None:
            self.scores[game.game_id] = score
        for key, command in self.commands.items():
            if key[0] == game.game_id:
                self.commands[key] = replace(command, expires_at=game.finished_at + 90 * DAY)
        return game

    def for_recovery(self, game_id: str) -> Game:
        try:
            return self.rows[game_id]
        except KeyError:
            raise NotFound("game") from None

    def active_ids(self) -> tuple[str, ...]:
        return tuple(k for k, g in self.rows.items() if g.finished_at is None)

    def history(self, player_id: str, after_game_id: str | None, limit: int) -> tuple[Game, ...]:
        def key(g):
            return (-g.finished_at, g.game_id)

        anchor = self.owned(after_game_id, player_id) if after_game_id else None
        if anchor is not None and anchor.finished_at is None:
            raise Conflict("history cursor is not terminal")
        return tuple(
            sorted(
                (
                    g
                    for g in self.rows.values()
                    if g.player_id == player_id
                    and g.finished_at is not None
                    and (anchor is None or key(g) > key(anchor))
                ),
                key=key,
            )[:limit]
        )

    def board(
        self, cohort: Cohort, after: tuple[int, int, str] | None, limit: int
    ) -> tuple[Score, ...]:
        def key(s):
            return (-s.score, s.completed_at, s.game_id)

        threshold = (-after[0], after[1], after[2]) if after else None
        return tuple(
            sorted(
                (
                    s
                    for s in self.scores.values()
                    if s.cohort == cohort and (threshold is None or key(s) > threshold)
                ),
                key=key,
            )[:limit]
        )


class FakeMaintenance:
    def __init__(self, accounts: FakeAccounts, packs: FakePacks, games: FakeGames):
        self.accounts, self.packs, self.games = accounts, packs, games
        self.ledger: dict[str, Deletion] = {}

    def record_deletion(self, deletion: Deletion) -> None:
        if deletion.deletion_id in self.ledger and self.ledger[deletion.deletion_id] != deletion:
            raise Conflict("deletion identity")
        self.ledger[deletion.deletion_id] = deletion

    def deletions(self) -> tuple[Deletion, ...]:
        return tuple(sorted(self.ledger.values(), key=lambda d: (d.requested_at, d.deletion_id)))

    def erase_clues(self, account_id: str, through_ms: int) -> None:
        for key, attempt in self.games.attempts.items():
            if (
                self.games.rows[key[0]].player_id == account_id
                and attempt.received_at <= through_ms
            ):
                self.games.attempts[key] = replace(attempt, raw_clue=None)

    def erase_account(self, account_id: str, now_ms: int) -> None:
        ids = {k for k, g in self.games.rows.items() if g.player_id == account_id}
        if any(self.games.rows[k].finished_at is None for k in ids):
            raise Conflict("interrupt active games first")
        self.accounts.revoke_all(account_id)
        self.accounts.rows.pop(account_id, None)
        self.games.commands = {k: v for k, v in self.games.commands.items() if k[0] not in ids}
        self.games.attempts = {k: v for k, v in self.games.attempts.items() if k[0] not in ids}
        for gid in ids:
            self.games.rows[gid] = replace(self.games.rows[gid], player_id=None)
            if gid in self.games.scores:
                self.games.scores[gid] = replace(
                    self.games.scores[gid], player_id=None, display_name=None
                )
        self.packs.reservations = {
            k: v for k, v in self.packs.reservations.items() if v.owner_id != account_id
        }
        # owners retains namespace tombstones; fake has no credential-bearing tombstone object.

    def expire(self, now_ms: int) -> None:
        for key, attempt in self.games.attempts.items():
            if now_ms >= attempt.received_at + 30 * DAY:
                self.games.attempts[key] = replace(attempt, raw_clue=None)
        expired = [
            k
            for k, v in self.games.commands.items()
            if v.expires_at is not None and now_ms >= v.expires_at
        ]
        for key in expired:
            self.games.commands.pop(key)
            self.games.attempts.pop(key, None)

    def required_hmac_keys(self, now_ms: int) -> frozenset[str]:
        return frozenset(
            c.hmac_key_version
            for c in self.games.commands.values()
            if c.expires_at is None or now_ms < c.expires_at
        )


class FakeUnitOfWork:
    """Commit on clean exit, rollback all adapters on exceptions; no persistence."""

    def __init__(self):
        self.accounts = FakeAccounts()
        self.packs = FakePacks()
        self.games = FakeGames()
        self.maintenance = FakeMaintenance(self.accounts, self.packs, self.games)
        self._backup = None

    def __enter__(self):
        if self._backup is not None:
            raise RuntimeError("nested transaction")
        self._backup = deepcopy((self.accounts, self.packs, self.games, self.maintenance))
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is not None:
            self.accounts, self.packs, self.games, self.maintenance = self._backup
        self._backup = None


def smoke() -> dict[str, int]:
    """Exercise every port group using authored synthetic values, no network/model."""
    uow = FakeUnitOfWork()
    with uow:
        uow.accounts.create(Account("a", "alice", "Alice", "fake-hash"))
        uow.accounts.issue_session(Session("s", "a", "digest", "csrf", 0, 0, DAY))
        install = uow.packs.reserve(Installation("i", "a", "p", "1", "manifest"))
        uow.packs.publish(
            Publication(
                "v",
                install,
                b"{}",
                "semantic",
                "vector",
                (),
                "r",
                "{}",
                "fingerprint",
                "protocol",
                "rules",
                "a",
                "authored fixture",
                0,
            )
        )
        artifact = Artifact(
            "art", "v", "r", "casual", "fingerprint", "rules", "config", "{}", "artifact", "{}"
        )
        uow.packs.add_artifact(artifact)
        game = Game("g", "a", artifact, "{}", 0, "{}", 0)
        uow.games.create(game)
        command = Command("g", "c", "hmac", "key1", 0, "{}")
        attempt = Attempt("g", "c", "synthetic fixture", "target", 0)
        uow.games.admit("a", command, attempt)
        uow.games.resolve(
            "a",
            replace(game, revision=1),
            replace(command, final=True),
            replace(attempt, resolved_at=1, outcome="miss"),
        )
        cohort = Cohort("casual", "p", "1", "manifest", "fingerprint", "rules", "config", None)
        uow.games.finish(
            "a",
            replace(game, revision=2, finished_at=2, end_reason="pack_cleared"),
            Score("g", "a", "Alice", 0, 2, cohort),
            (),
        )
        uow.maintenance.record_deletion(Deletion("d", "a", "clues", 2, 30 * DAY))
        uow.maintenance.erase_clues("a", 2)
        assert uow.games.receipt("g", "c", "a").final
        assert uow.games.board(cohort, None, 10)[0].score == 0
    return {
        "accounts": len(uow.accounts.rows),
        "versions": len(uow.packs.versions),
        "games": len(uow.games.rows),
        "scores": len(uow.games.scores),
    }
