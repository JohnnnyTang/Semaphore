import hashlib
import hmac
import json
import threading
from contextlib import contextmanager

import pytest

from semaphore_hub.games import GameError, GameService
from semaphore_hub.interfaces import InferenceCompletion
from semaphore_hub.results import ResultsService


class Clock:
    now = 0

    def utc_ms(self):
        return 100000 + self.now

    def monotonic_ms(self):
        return self.now


class Keys:
    def active_version(self):
        return "v1"

    def validate_versions(self, required):
        pass

    def digest(self, version, raw):
        assert version == "v1"
        return hmac.new(b"k" * 32, raw, hashlib.sha256).hexdigest()


class Locks:
    def __init__(self):
        self.lock = threading.RLock()

    def hold(self, gid):
        return self.lock


class Inference:
    def __init__(self):
        self.jobs = []
        self.accept = True
        self.cancelled = []

    def submit(self, request, callback):
        if not self.accept:
            return False
        self.jobs.append((request, callback))
        return True

    def cancel(self, gid, cid):
        self.cancelled.append((gid, cid))


@pytest.fixture
def hub(setup, raw, measured):
    tx, packs = setup
    publication = packs.install(
        raw,
        owner_id="owner",
        operator_id="admin",
        rights_reference="synthetic-unit-only",
        accept=True,
    )
    entries = [json.loads(x)["id"] for x in publication.entries_json]
    artifact = packs.accept_casual_artifact(
        publication.installation.pack_id,
        publication.installation.version,
        operator_id="admin",
        initial_board=entries[:5],
        schedule=[],
    )
    clock, inference, keys, locks = Clock(), Inference(), Keys(), Locks()
    service = GameService(tx, inference, keys, locks, clock=clock)
    return tx, service, inference, clock, artifact


def create(hub, player="owner"):
    return hub[1].create(player, dict(artifact_id=hub[4].artifact_id, mode="casual"))["snapshot"][
        "game_id"
    ]


def clue(cid="c1", revision=0):
    return dict(command_id=cid, expected_revision=revision, clue="mysterious association")


def test_admission_retry_removal_and_restart(hub):
    tx, service, inference, clock, artifact = hub
    gid = create(hub)
    response = service.command("owner", gid, clue())
    assert response["receipt"]["outcome"] == "pending"
    with tx() as db:
        db.execute("UPDATE clue_attempts SET raw_clue=NULL WHERE game_id=?", (gid,))
    assert service.command("owner", gid, clue())["receipt"] == response["receipt"]
    assert (
        service.command("owner", gid, {**clue(), "clue": "changed"})["receipt"]["outcome"]
        == "command_conflict"
    )
    with pytest.raises(LookupError):
        service.receipt("other", gid, "c1")
    assert len(inference.jobs) == 1
    restarted = GameService(tx, inference, Keys(), Locks(), clock=clock)
    restarted.interrupt(gid, clock.utc_ms())
    assert restarted.get("owner", gid)["snapshot"]["end_reason"] == "interrupted"
    assert restarted.command("owner", gid, clue())["receipt"]["outcome"] == "game_over"
    with tx() as db:
        assert db.execute("SELECT count(*) FROM scores").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM clue_attempts").fetchone()[0] == 1
    clock.now += 90 * 86400000
    with pytest.raises(GameError) as exc:
        restarted.receipt("owner", gid, "c1")
    assert exc.value.status == 410
    assert restarted.get("owner", gid)["snapshot"]["status"] == "over"


def test_completion_once_and_late_callback(hub):
    tx, service, inference, clock, artifact = hub
    gid = create(hub)
    service.command("owner", gid, clue())
    req, callback = inference.jobs[0]
    completion = InferenceCompletion(
        gid, req.command_id, req.fingerprint_hash, tuple([1.0] + [0.0] * 2559)
    )
    callback(completion)
    first = service.receipt("owner", gid, "c1")
    callback(completion)
    assert service.receipt("owner", gid, "c1")["receipt"] == first["receipt"]
    with tx() as db:
        assert db.execute("SELECT count(*) FROM commands").fetchone()[0] == 1
    service.quit("owner", gid)
    callback(completion)
    with tx() as db:
        assert db.execute("SELECT count(*) FROM scores").fetchone()[0] == 0


def test_due_natural_finish_wins_quit_zero_score(hub):
    tx, service, inference, clock, artifact = hub
    gid = create(hub)
    clock.now = 5000
    result = service.quit("owner", gid)
    assert result["snapshot"]["end_reason"] == "pack_exhausted"
    assert result["snapshot"]["score"] == 0
    assert service.quit("owner", gid) == result
    with tx() as db:
        assert [tuple(r) for r in db.execute("SELECT score FROM scores")] == [(0,)]
    results = ResultsService(tx)
    assert results.history("owner")["items"][0]["competitive"]
    assert results.board(artifact.artifact_id)["items"][0]["score"] == 0
    assert "player_id" not in results.board(artifact.artifact_id)["items"][0]


def test_overload_timeout_and_atomic_commit_failure(hub):
    tx, service, inference, clock, artifact = hub
    gid = create(hub)
    inference.accept = False
    assert service.command("owner", gid, clue())["receipt"]["outcome"] == "overloaded"
    inference.accept = True
    service.command("owner", gid, clue("c2"))
    clock.now = 5000
    req, callback = inference.jobs[0]
    callback(
        InferenceCompletion(gid, req.command_id, req.fingerprint_hash, tuple([1.0] + [0.0] * 2559))
    )
    assert service.get("owner", gid)["snapshot"]["score"] == 0
    assert service.receipt("owner", gid, "c2")["receipt"]["outcome"] != "pending"


def test_commit_failure_cancels_without_memory_admission(hub):
    tx, service, inference, clock, artifact = hub
    gid = create(hub)

    @contextmanager
    def broken():
        with tx() as db:
            yield db
            if db.execute("SELECT count(*) FROM commands").fetchone()[0]:
                raise RuntimeError("injected before commit")

    service.transactions = broken
    with pytest.raises(RuntimeError):
        service.command("owner", gid, clue())
    assert (gid, "c1") in inference.cancelled
    with tx() as db:
        assert db.execute("SELECT count(*) FROM commands").fetchone()[0] == 0
    assert service.live[gid].state.pending is None


def test_corrupt_artifact_and_unpublished_rejected(hub):
    tx, service, inference, clock, artifact = hub
    with tx() as db:
        db.execute("DROP TRIGGER immutable_artifact")
        db.execute("UPDATE artifacts SET config_digest=?", ("b" * 64,))
    with pytest.raises(GameError):
        create(hub)
    with tx() as db:
        db.execute("UPDATE artifacts SET config_digest=?", (artifact.config_digest,))
        db.execute("PRAGMA defer_foreign_keys=ON")
        # Corrupt trust metadata instead of leaving dangling foreign keys.
        db.execute("DROP TRIGGER immutable_report")
        db.execute("UPDATE verification_reports SET trusted=0")
    with pytest.raises(GameError):
        create(hub)


def test_board_full_tie_pagination_and_cohort_isolation(hub, tmp_path):
    tx, service, inference, clock, artifact = hub
    players = ("owner", "other", "admin")
    ids = [create(hub, player) for player in players]
    clock.now = 5000
    for player, gid in zip(players, ids, strict=True):
        service.get(player, gid)
    ids.sort()
    results = ResultsService(tx)
    first = results.board(artifact.artifact_id, limit=1)
    second = results.board(artifact.artifact_id, cursor=first["next_cursor"], limit=1)
    third = results.board(artifact.artifact_id, cursor=second["next_cursor"], limit=1)
    assert [p["items"][0]["game_id"] for p in (first, second, third)] == ids
    assert third["next_cursor"] is None
    from semaphore_hub.results.service import cursor_encode

    history = dict(next_cursor=cursor_encode("history:owner", "anchor"))
    with pytest.raises(ValueError):
        results.history("other", cursor=history["next_cursor"])
    with pytest.raises(ValueError):
        results.board(artifact.artifact_id, cursor=history["next_cursor"])
    assert len(results.history("other")["items"]) == 1
    # A different valid artifact/config gets a distinct empty board.
    from semaphore_hub.packs import PackService

    packs = PackService(tx, tmp_path / "alternate-assets", None)
    body = json.loads(artifact.artifact_json)
    with tx() as db:
        row = db.execute(
            "SELECT pack_id,version FROM pack_versions WHERE version_id=?", (artifact.version_id,)
        ).fetchone()
    alternative = packs.accept_casual_artifact(
        *row, operator_id="admin", initial_board=list(reversed(body["initial_board"])), schedule=[]
    )
    assert results.board(alternative.artifact_id)["items"] == []
    with pytest.raises(ValueError):
        results.board(alternative.artifact_id, cursor=first["next_cursor"])


def test_http_routes_reject_foreign_and_bad_bodies(hub):
    from semaphore_hub.games.http import GamesHttp
    from semaphore_hub.interfaces import Principal

    tx, service, inference, clock, artifact = hub
    http = GamesHttp(service, ResultsService(tx))
    player = Principal("owner", "session")
    assert http.handle(None, "POST", "/api/v1/games", b"{}").status == 401
    assert (
        http.handle(player, "POST", "/api/v1/games", b'{"mode":"casual","mode":"event"}').status
        == 400
    )
    created = http.handle(
        player,
        "POST",
        "/api/v1/games",
        json.dumps(dict(mode="casual", artifact_id=artifact.artifact_id)).encode(),
    )
    assert created.status == 201
    gid = created.body["snapshot"]["game_id"]
    assert (
        http.handle(Principal("other", "other-session"), "GET", "/api/v1/games/" + gid).status
        == 404
    )
    assert http.handle(player, "GET", "/api/v1/games/current").status == 200
    assert http.handle(player, "GET", "/api/v1/history?limit=0").status == 400
    assert (
        http.handle(
            player, "POST", f"/api/v1/games/{gid}/commands", json.dumps(clue()).encode()
        ).status
        == 202
    )


def test_completion_commit_failure_does_not_advance_live_state(hub):
    tx, service, inference, clock, artifact = hub
    gid = create(hub)
    service.command("owner", gid, clue())

    @contextmanager
    def broken():
        with tx() as db:
            yield db
            if db.execute("SELECT 1 FROM commands WHERE state='final'").fetchone():
                raise RuntimeError("completion commit failure")

    service.transactions = broken
    req, callback = inference.jobs[0]
    with pytest.raises(RuntimeError):
        callback(
            InferenceCompletion(
                gid, req.command_id, req.fingerprint_hash, tuple([1.0] + [0.0] * 2559)
            )
        )
    assert service.live[gid].state.pending is not None
    with tx() as db:
        assert db.execute("SELECT state FROM commands").fetchone()[0] == "pending"


def test_deleted_account_cannot_create_after_asset_loading(hub):
    tx, service, inference, clock, artifact = hub
    loader = service.artifact_loader

    def erase(artifact):
        rows = loader(artifact)
        with tx() as db:
            db.execute(
                "UPDATE accounts SET deleted_at=1,login_name=NULL,display_name=NULL,"
                "password_hash=NULL,is_operator=0 WHERE account_id='owner'"
            )
        return rows

    service.artifact_loader = erase
    with pytest.raises(LookupError):
        create(hub)
    with tx() as db:
        assert db.execute("SELECT count(*) FROM games").fetchone()[0] == 0


def test_route_malformed_url_and_out_of_range_cursor(hub):
    from semaphore_core.verification import canonical
    from semaphore_hub.games.http import GamesHttp
    from semaphore_hub.interfaces import Principal

    tx, service, inference, clock, artifact = hub
    results = ResultsService(tx)
    http = GamesHttp(service, results)
    principal = Principal("owner", "session")
    assert http.handle(principal, "GET", "http://[invalid").status == 400
    scope = canonical(results.board(artifact.artifact_id)["cohort"]).decode()
    import base64

    cursor = (
        base64.urlsafe_b64encode(
            json.dumps(
                [hashlib.sha256(scope.encode()).hexdigest()[:32], [10**30, 0, "game"]]
            ).encode()
        )
        .decode()
        .rstrip("=")
    )
    assert (
        http.handle(
            principal, "GET", f"/api/v1/boards/{artifact.artifact_id}?cursor={cursor}"
        ).status
        == 400
    )
    gid = create(hub)
    assert http.handle(principal, "POST", f"/api/v1/games/{gid}/quit", b" { } ").status == 200


def test_clock_only_poll_does_not_write_but_terminal_tick_does(hub):
    tx, service, inference, clock, artifact = hub
    gid = create(hub)
    with tx() as db:
        before = db.execute("SELECT snapshot_json FROM games WHERE game_id=?", (gid,)).fetchone()[0]
    clock.now = 100
    response = service.get("owner", gid)
    service.tick()
    assert service.live[gid].state.elapsed_ms == 100
    assert response["snapshot"]["revision"] == 0
    with tx() as db:
        assert (
            db.execute("SELECT snapshot_json FROM games WHERE game_id=?", (gid,)).fetchone()[0]
            == before
        )
    clock.now = 5000
    service.tick()
    with tx() as db:
        assert (
            db.execute("SELECT status FROM games WHERE game_id=?", (gid,)).fetchone()[0] == "over"
        )
        assert db.execute("SELECT count(*) FROM scores WHERE game_id=?", (gid,)).fetchone()[0] == 1


def test_scheduled_board_change_rejects_stale_command_without_inference(hub, tmp_path):
    from semaphore_hub.packs import PackService

    tx, service, inference, clock, artifact = hub
    body = json.loads(artifact.artifact_json)
    with tx() as db:
        row = db.execute(
            "SELECT pack_id,version FROM pack_versions WHERE version_id=?", (artifact.version_id,)
        ).fetchone()
    scheduled = PackService(tx, tmp_path / "unused-assets", None).accept_casual_artifact(
        *row,
        operator_id="admin",
        initial_board=body["initial_board"][:4],
        schedule=[{"at_ms": 100, "entry_id": body["initial_board"][4]}],
    )
    initial = service.create("owner", dict(artifact_id=scheduled.artifact_id, mode="casual"))
    gid = initial["snapshot"]["game_id"]
    command = clue(revision=initial["snapshot"]["revision"])
    clock.now = 100
    rejected = service.command("owner", gid, command)
    assert rejected["receipt"]["outcome"] == "stale_revision"
    assert inference.jobs == []
    assert service.command("owner", gid, command)["receipt"] == rejected["receipt"]
    accepted = service.command("owner", gid, clue("new-command", rejected["snapshot"]["revision"]))
    assert accepted["receipt"]["outcome"] == "pending"
    assert len(inference.jobs) == 1
