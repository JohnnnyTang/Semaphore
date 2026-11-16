"""Executable storage and fake-port boundaries; not production acceptance."""

import sqlite3
from contextlib import closing
from dataclasses import replace

import pytest

from semaphore_hub.repositories import Account, Conflict, Installation, NotFound, VectorCache
from semaphore_hub.storage import connect, migrate, transaction
from semaphore_hub.testing import FakeUnitOfWork, smoke


def seeded(db):
    db.execute("INSERT INTO accounts VALUES ('a','alice','Alice','hash',1,0,NULL)")
    db.execute("INSERT INTO packs VALUES ('p','a',0,NULL)")
    db.execute("INSERT INTO pack_versions VALUES ('v','p','1',X'00','m','s','vec',0)")
    db.execute("""INSERT INTO verification_reports VALUES
        ('r','v','m','s','fp','protocol','rules',1,1,'{}',0)""")


def test_installation_visibility_and_identity_constraints():
    with closing(connect(":memory:")) as db:
        assert migrate(db) == 2
        seeded(db)
        db.execute("INSERT INTO install_reservations VALUES ('i','p','1','m','pending',0,NULL)")
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("INSERT INTO install_reservations VALUES ('j','p','1','m','pending',0,NULL)")
        db.execute(
            "UPDATE install_reservations SET state='failed',finished_at=1 WHERE install_id='i'"
        )
        db.execute("INSERT INTO install_reservations VALUES ('j','p','1','m','pending',1,NULL)")
        assert db.execute("SELECT count(*) FROM published_versions").fetchone()[0] == 0
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("""INSERT INTO verification_reports VALUES
                ('bad','v','wrong','s','fp','protocol','rules',1,1,'{}',0)""")
        db.execute("""INSERT INTO verification_reports VALUES
            ('self','v','m','s','fp','protocol','rules',0,1,'{}',0)""")
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("INSERT INTO published_versions VALUES ('v','self','a','rights',0)")
        db.execute("INSERT INTO published_versions VALUES ('v','r','a','rights',0)")
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("""INSERT INTO artifacts VALUES
                ('bad','v','r','casual','wrong','rules','cfg','{}','digest','{}',NULL)""")
        db.execute("""INSERT INTO artifacts VALUES
            ('art','v','r','casual','fp','rules','cfg','{}','digest','{}',NULL)""")
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("UPDATE artifacts SET config_digest='changed'")


def test_publication_failure_is_atomic():
    with closing(connect(":memory:")) as db:
        migrate(db)
        seeded(db)
        with pytest.raises(sqlite3.IntegrityError):
            with transaction(db):
                db.execute("INSERT INTO pack_entries VALUES ('v',0,'e','{}')")
                db.execute("INSERT INTO published_versions VALUES ('v','r','a','',0)")
        assert db.execute("SELECT count(*) FROM pack_entries").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM published_versions").fetchone()[0] == 0


def test_fake_smoke_and_rollback():
    assert smoke() == {"accounts": 1, "versions": 1, "games": 1, "scores": 1}
    uow = FakeUnitOfWork()
    with pytest.raises(ValueError):
        with uow:
            uow.accounts.create(Account("a", "alice", "Alice", "hash"))
            raise ValueError("abort")
    assert uow.accounts.by_login("alice") is None
    with uow:
        uow.accounts.create(Account("a", "alice", "Alice", "hash"))
    assert uow.accounts.by_id("a").login_name == "alice"


def test_owner_before_digest_and_failed_install_keeps_namespace():
    uow = FakeUnitOfWork()
    pending = Installation("i", "a", "p", "1", "digest")
    with uow:
        assert uow.packs.reserve(pending) == pending
        assert uow.packs.reserve(replace(pending, install_id="retry")) == pending
        with pytest.raises(Conflict, match="owner"):
            uow.packs.reserve(replace(pending, owner_id="foreign"))
        uow.packs.release("i", "a")
        with pytest.raises(Conflict, match="owner"):
            uow.packs.reserve(replace(pending, owner_id="foreign"))
        assert uow.packs.reserve(replace(pending, install_id="retry")).install_id == "retry"
    with pytest.raises(NotFound):
        uow.packs.published("p", "1")


def test_vector_cache_mismatch_is_a_miss_and_not_identity_repair():
    uow = FakeUnitOfWork()
    cache = VectorCache("v", "fp", "digest", "assets/v", 4, 2)
    with uow:
        uow.packs.put_vectors(cache)
        assert uow.packs.vectors("v", "fp") == cache
        assert uow.packs.vectors("v", "different") is None
        with pytest.raises(Conflict):
            uow.packs.put_vectors(replace(cache, ordered_vectors_digest="changed"))


def test_all_repository_port_lifecycles():
    from semaphore_hub.repositories import (
        Artifact,
        Attempt,
        Cohort,
        Command,
        Deletion,
        Game,
        Publication,
        Score,
        Session,
    )
    from semaphore_hub.testing import DAY

    uow = FakeUnitOfWork()
    with uow:
        uow.accounts.create(Account("a", "alice", "Alice", "hash"))
        session = Session("s", "a", "token", "csrf", 0, 0, DAY)
        uow.accounts.issue_session(session)
        assert uow.accounts.session("token", 5, 100) == session
        uow.accounts.touch_session("s", 50)
        assert uow.accounts.session("token", 149, 100).last_seen_at == 50
        assert uow.accounts.session("token", 150, 100) is None
        uow.accounts.revoke_session("s")
        assert uow.accounts.session("token", 1, 100) is None
        uow.accounts.issue_session(session)
        uow.accounts.reset_password("a", "newhash")
        assert uow.accounts.session("token", 1, 100) is None
        install = uow.packs.reserve(Installation("i", "a", "p", "1", "manifest"))
        publication = Publication(
            "v",
            install,
            b"{}",
            "semantic",
            "vector",
            (),
            "r",
            "{}",
            "fp",
            "protocol",
            "rules",
            "a",
            "rights",
            0,
        )
        uow.packs.publish(publication)
        assert uow.packs.list_published(None, 1) == (publication,)
        assert uow.packs.list_published("v", 1) == ()
        artifact = Artifact("art", "v", "r", "casual", "fp", "rules", "cfg", "{}", "d", "{}")
        uow.packs.add_artifact(artifact)
        assert uow.packs.artifact("art") == artifact
        assert uow.packs.artifacts_for_version("v") == (artifact,)
        game = Game("g", "a", artifact, "{}", 0, "{}", 0)
        uow.games.create(game)
        assert uow.games.active_ids() == ("g",)
        assert uow.games.current("a") == game
        assert uow.games.current("foreign") is None
        assert uow.games.history("a", None, 5) == ()
        assert uow.games.for_recovery("g") == game
        with pytest.raises(NotFound):
            uow.games.owned("g", "foreign")
        command = Command("g", "c", "hmac", "key1", 0, "{}")
        attempt = Attempt("g", "c", "synthetic", "target", 0)
        uow.games.admit("a", command, attempt)
        assert uow.games.admit("a", command, attempt) == command
        with pytest.raises(Conflict):
            uow.games.admit("a", replace(command, payload_hmac="other"), attempt)
        uow.games.resolve(
            "a",
            replace(game, revision=1),
            replace(command, final=True),
            replace(attempt, resolved_at=1, outcome="miss"),
        )
        terminal = replace(game, revision=2, finished_at=2, end_reason="pack_cleared")
        cohort = Cohort("casual", "p", "1", "manifest", "fp", "rules", "cfg", None)
        score = Score("g", "a", "Alice", 0, 2, cohort)
        uow.games.finish("a", terminal, score, ())
        assert uow.games.finish("a", terminal, score, ()) == terminal
        assert uow.games.current("a") is None
        assert uow.games.history("a", None, 5) == (terminal,)
        assert uow.games.board(cohort, None, 5) == (score,)
        assert uow.games.board(cohort, (0, 2, "g"), 5) == ()
        assert uow.games.board(replace(cohort, config_digest="other"), None, 5) == ()
        assert uow.maintenance.required_hmac_keys(30 * DAY) == frozenset({"key1"})
        uow.maintenance.expire(30 * DAY)
        assert uow.games.attempts["g", "c"].raw_clue is None
        assert uow.games.receipt("g", "c", "a").final
        deletion = Deletion("d", "a", "account", 30 * DAY, 60 * DAY)
        uow.maintenance.record_deletion(deletion)
        assert uow.maintenance.deletions() == (deletion,)
        uow.maintenance.erase_account("a", 30 * DAY)
        assert uow.games.board(cohort, None, 5)[0].display_name is None
        assert uow.packs.owners["p"] == "a"
        assert uow.accounts.by_login("alice") is None
        assert uow.maintenance.required_hmac_keys(30 * DAY) == frozenset()
        assert uow.games.commands == {}
