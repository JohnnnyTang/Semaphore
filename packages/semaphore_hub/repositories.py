"""Frozen W1 transaction-scoped ports; production implementations belong to W2/W3.

All JSON strings are already schema-validated canonical documents. Services own
locks and commits. No repository may perform inference, commit, or return secrets
through public projections. Missing and foreign private objects both raise NotFound.
"""

from dataclasses import dataclass
from types import TracebackType
from typing import Literal, Protocol


class NotFound(LookupError):
    pass


class Conflict(ValueError):
    pass


@dataclass(frozen=True)
class Account:
    account_id: str
    login_name: str
    display_name: str
    password_hash: str
    is_operator: bool = False
    created_at: int = 0


@dataclass(frozen=True)
class Session:
    session_id: str
    account_id: str
    token_digest: str
    csrf_digest: str
    created_at: int
    last_seen_at: int
    absolute_expires_at: int


@dataclass(frozen=True)
class Installation:
    install_id: str
    owner_id: str
    pack_id: str
    version: str
    manifest_digest: str


@dataclass(frozen=True)
class Publication:
    version_id: str
    installation: Installation
    manifest_bytes: bytes
    semantic_hash: str
    vector_hash: str
    entries_json: tuple[str, ...]
    report_id: str
    report_json: str
    fingerprint_hash: str
    protocol_hash: str
    ruleset_id: str
    accepted_by: str
    rights_reference: str
    accepted_at: int


@dataclass(frozen=True)
class Artifact:
    artifact_id: str
    version_id: str
    report_id: str
    mode: Literal["casual", "event"]
    fingerprint_hash: str
    ruleset_id: str
    config_digest: str
    config_json: str
    artifact_digest: str
    artifact_json: str
    challenge_digest: str | None = None


@dataclass(frozen=True)
class Cohort:
    mode: str
    pack_id: str
    version: str
    manifest_digest: str
    fingerprint_hash: str
    ruleset_id: str
    config_digest: str
    challenge_digest: str | None


@dataclass(frozen=True)
class Game:
    game_id: str
    player_id: str | None
    artifact: Artifact
    model_identity_json: str
    revision: int
    snapshot_json: str
    started_at: int
    finished_at: int | None = None
    end_reason: str | None = None


@dataclass(frozen=True)
class Command:
    game_id: str
    command_id: str
    payload_hmac: str
    hmac_key_version: str
    received_at: int
    receipt_json: str
    final: bool = False
    expires_at: int | None = None


@dataclass(frozen=True)
class Attempt:
    game_id: str
    command_id: str
    raw_clue: str | None
    target_id: str | None
    received_at: int
    resolved_at: int | None = None
    outcome: str | None = None
    target_rank: int | None = None


@dataclass(frozen=True)
class Score:
    game_id: str
    player_id: str | None
    display_name: str | None
    score: int
    completed_at: int
    cohort: Cohort


@dataclass(frozen=True)
class Deletion:
    deletion_id: str
    account_id: str
    scope: Literal["clues", "account"]
    requested_at: int
    retain_until: int


@dataclass(frozen=True)
class VectorCache:
    vector_hash: str
    fingerprint_hash: str
    ordered_vectors_digest: str
    asset_path: str
    dimensions: int
    entry_count: int


class Accounts(Protocol):
    def create(self, account: Account) -> None: ...
    def by_id(self, account_id: str) -> Account: ...
    def by_login(self, normalized_login: str) -> Account | None: ...
    def issue_session(self, session: Session) -> None: ...
    def session(self, token_digest: str, now_ms: int, idle_ms: int) -> Session | None: ...
    def touch_session(self, session_id: str, now_ms: int) -> None: ...
    def revoke_session(self, session_id: str) -> None: ...
    def revoke_all(self, account_id: str) -> None: ...
    def reset_password(self, account_id: str, password_hash: str) -> None: ...


class Packs(Protocol):
    def reserve(self, installation: Installation) -> Installation: ...
    def release(self, install_id: str, owner_id: str) -> None: ...
    def publish(self, publication: Publication) -> Publication: ...
    def published(self, pack_id: str, version: str) -> Publication: ...
    def list_published(
        self, after_version_id: str | None, limit: int
    ) -> tuple[Publication, ...]: ...
    def add_artifact(self, artifact: Artifact) -> None: ...
    def artifact(self, artifact_id: str) -> Artifact: ...
    def artifacts_for_version(self, version_id: str) -> tuple[Artifact, ...]: ...
    def put_vectors(self, cache: VectorCache) -> None: ...
    def vectors(self, vector_hash: str, fingerprint_hash: str) -> VectorCache | None: ...


class Games(Protocol):
    def create(self, game: Game) -> None: ...
    def current(self, player_id: str) -> Game | None: ...
    def owned(self, game_id: str, player_id: str) -> Game: ...
    def receipt(self, game_id: str, command_id: str, player_id: str) -> Command: ...
    def admit(self, player_id: str, command: Command, attempt: Attempt) -> Command: ...
    def resolve(self, player_id: str, game: Game, command: Command, attempt: Attempt) -> None: ...
    def save_transition(self, player_id: str, game: Game) -> None: ...
    def finish(
        self, player_id: str, game: Game, score: Score | None, pending: tuple[Command, ...]
    ) -> Game: ...
    def active_ids(self) -> tuple[str, ...]: ...
    def for_recovery(self, game_id: str) -> Game: ...
    def history(
        self, player_id: str, after_game_id: str | None, limit: int
    ) -> tuple[Game, ...]: ...
    def board(
        self, cohort: Cohort, after: tuple[int, int, str] | None, limit: int
    ) -> tuple[Score, ...]: ...


class Maintenance(Protocol):
    def record_deletion(self, deletion: Deletion) -> None: ...
    def deletions(self) -> tuple[Deletion, ...]: ...
    def erase_clues(self, account_id: str, through_ms: int) -> None: ...
    def erase_account(self, account_id: str, now_ms: int) -> None: ...
    def expire(self, now_ms: int) -> None: ...
    def required_hmac_keys(self, now_ms: int) -> frozenset[str]: ...


class UnitOfWork(Protocol):
    accounts: Accounts
    packs: Packs
    games: Games
    maintenance: Maintenance

    def __enter__(self) -> "UnitOfWork": ...
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...
