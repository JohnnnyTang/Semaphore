import json
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

import pytest

from semaphore_core.verification import load, manifest_hashes, parse_manifest
from semaphore_hub.packs import PackService, SQLitePacks
from semaphore_hub.repositories import Conflict, Installation, NotFound, VectorCache
from semaphore_hub.storage import connect, migrate, transaction


@pytest.fixture
def setup(tmp_path):
    path = tmp_path / "packs.db"
    db = connect(path)
    migrate(db)
    with transaction(db):
        for ident, operator in [("owner", 0), ("other", 0), ("admin", 1)]:
            db.execute(
                "INSERT INTO accounts VALUES (?,?,?,?,?,0,NULL)",
                (ident, ident, ident, "unused", operator),
            )
    db.close()

    @contextmanager
    def tx():
        db = connect(path)
        try:
            with transaction(db):
                yield db
        finally:
            db.close()

    return tx, PackService(tx, tmp_path / "assets", None)


@pytest.fixture
def raw():
    p = json.loads(Path("packs/everyday.json").read_bytes())
    p["pack"]["tags"] = []
    return json.dumps(p).encode()


def install(service, raw):
    return service.install(
        raw, owner_id="owner", operator_id="admin", rights_reference="unit-test-only", accept=True
    )


@pytest.fixture
def measured(monkeypatch):
    def fake(value, embedder, ruleset):
        h = manifest_hashes(value)
        embedder.entry_vectors = [[1.0] + [0.0] * 2559 for _ in value.manifest["entries"]]
        return dict(
            manifest_digest=h.manifest_digest,
            semantic_hash=h.semantic_hash,
            vector_hash=h.vector_hash,
            fingerprint_hash=load("model-lock.json")["fingerprint_sha256"],
            protocol_hash="a" * 64,
            ruleset_id=ruleset,
            status="measured",
            metrics=dict(reachability=1.0),
        )

    monkeypatch.setattr("semaphore_hub.packs.service.verify_pack", fake)
    return fake


def test_namespace_owner_before_digest_and_release(setup):
    tx, _ = setup
    item = Installation("i", "owner", "pack", "1", "a" * 64)
    with tx() as db:
        repo = SQLitePacks(db)
        assert repo.reserve(item) == item
        assert repo.reserve(replace(item, install_id="j")) == item
        with pytest.raises(Conflict, match="owner"):
            repo.reserve(replace(item, owner_id="other"))
        with pytest.raises(Conflict, match="version"):
            repo.reserve(replace(item, manifest_digest="b" * 64))
        repo.release("i", "owner")
    with tx() as db:
        with pytest.raises(Conflict, match="owner"):
            SQLitePacks(db).reserve(replace(item, owner_id="other"))


def test_install_retry_conflict_and_visibility(setup, raw, measured):
    tx, service = setup
    assert service.list_packs() == dict(items=[], next_cursor=None)
    p = install(service, raw)
    assert install(service, raw) == p
    assert (
        service.get_pack(p.installation.pack_id, p.installation.version)["manifest_digest"]
        == p.installation.manifest_digest
    )
    with pytest.raises(Conflict):
        install(service, raw + b" ")
    with pytest.raises(Conflict, match="owner"):
        service.install(
            raw, owner_id="other", operator_id="admin", rights_reference="test", accept=True
        )
    with tx() as db:
        assert db.execute("SELECT count(*) FROM published_versions").fetchone()[0] == 1
        assert SQLitePacks(db).published(p.installation.pack_id, p.installation.version) == p


def test_no_accept_or_operator_or_synthetic(setup, raw):
    _, service = setup
    with pytest.raises(ValueError):
        service.install(
            raw, owner_id="owner", operator_id="admin", rights_reference="", accept=True
        )
    with pytest.raises(PermissionError):
        service.install(
            raw, owner_id="owner", operator_id="owner", rights_reference="test", accept=True
        )
    data = json.loads(raw)
    data["pack"]["tags"] = ["synthetic"]
    with pytest.raises(ValueError, match="noncompetitive"):
        install(service, json.dumps(data).encode())
    assert service.list_packs()["items"] == []


def test_failed_verification_keeps_namespace_and_cleans_slot(setup, raw, monkeypatch):
    tx, service = setup

    def fail(*args):
        raise ValueError("model missing")

    monkeypatch.setattr("semaphore_hub.packs.service.verify_pack", fail)
    with pytest.raises(ValueError, match="model missing"):
        install(service, raw)
    with tx() as db:
        assert db.execute("SELECT state FROM install_reservations").fetchone()[0] == "failed"
        assert db.execute("SELECT count(*) FROM published_versions").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM packs").fetchone()[0] == 1


def test_deadline_and_threshold_no_publish(setup, raw, measured, monkeypatch):
    _, service = setup
    times = iter([0, 600000])
    service.monotonic = lambda: next(times)
    with pytest.raises(TimeoutError):
        install(service, raw)
    service.monotonic = lambda: 0

    def low(*args):
        r = measured(*args)
        r["metrics"]["reachability"] = 0.84
        return r

    monkeypatch.setattr("semaphore_hub.packs.service.verify_pack", low)
    with pytest.raises(ValueError, match="threshold"):
        install(service, raw)
    assert service.list_packs()["items"] == []


def test_artifact_pins_and_public_projection(setup, raw, measured):
    tx, service = setup
    p = install(service, raw)
    entries = parse_manifest(raw).manifest["entries"]
    a = service.accept_casual_artifact(
        p.installation.pack_id,
        p.installation.version,
        operator_id="admin",
        initial_board=[e["id"] for e in entries[:6]],
        schedule=[dict(at_ms=5000, entry_id=entries[6]["id"])],
    )
    view = service.get_pack(p.installation.pack_id, p.installation.version)
    assert view["artifacts"][0]["cohort"]["config_digest"] == a.config_digest
    assert "owner" not in json.dumps(view)
    with tx() as db:
        assert SQLitePacks(db).artifact(a.artifact_id) == a
        with pytest.raises(Conflict):
            SQLitePacks(db).add_artifact(replace(a, artifact_id="bad", fingerprint_hash="b" * 64))


def test_orphan_cleanup_preserves_published_bytes(setup, raw, measured):
    tx, service = setup
    p = install(service, raw)
    (service.root / ("b" * 64 + ".manifest")).write_bytes(b"orphan")
    (service.root / ("c" * 32 + ".staging")).write_bytes(b"partial")
    service.clean_orphan_assets()
    assert (service.root / (p.installation.manifest_digest + ".manifest")).exists()
    assert len(list(service.root.iterdir())) == 2
    assert install(service, raw) == p


def test_vectors_immutable_and_tuple_identity(setup):
    tx, _ = setup
    v = VectorCache("a" * 64, "b" * 64, "c" * 64, "asset", 2560, 40)
    with tx() as db:
        repo = SQLitePacks(db)
        repo.put_vectors(v)
        repo.put_vectors(v)
        assert repo.vectors(v.vector_hash, v.fingerprint_hash) == v
        assert repo.vectors(v.vector_hash, "d" * 64) is None
        with pytest.raises(Conflict):
            repo.put_vectors(replace(v, asset_path="changed"))


def test_unknown_cursor_and_pack(setup):
    _, service = setup
    with pytest.raises(ValueError):
        service.list_packs(cursor="../../")
    with pytest.raises(NotFound):
        service.get_pack("unknown", "1")


def test_concurrent_first_claim_is_exclusive(setup):
    from concurrent.futures import ThreadPoolExecutor

    tx, _ = setup

    def claim(owner):
        try:
            with tx() as db:
                SQLitePacks(db).reserve(Installation(owner, owner, "race", "1", "a" * 64))
            return "won"
        except Conflict:
            return "lost"

    with ThreadPoolExecutor(2) as pool:
        assert sorted(pool.map(claim, ["owner", "other"])) == ["lost", "won"]


def test_unpublished_legacy_version_hidden(setup):
    tx, service = setup
    with tx() as db:
        db.execute("INSERT INTO packs VALUES ('legacy','owner',0,NULL)")
        db.execute(
            "INSERT INTO pack_versions VALUES ('legacy','legacy','1',?,'a','b','c',0)", (b"{}",)
        )
    assert service.list_packs()["items"] == []
    with pytest.raises(NotFound):
        service.get_pack("legacy", "1")


def test_read_dtos_validate_and_artifact_config_distinguishes_rounds(setup, raw, measured):
    from jsonschema import Draft202012Validator

    _, service = setup
    p = install(service, raw)
    ids = [e["id"] for e in parse_manifest(raw).manifest["entries"]]
    args = dict(
        operator_id="admin", initial_board=ids[:6], schedule=[dict(at_ms=5000, entry_id=ids[6])]
    )
    a = service.accept_casual_artifact(p.installation.pack_id, p.installation.version, **args)
    args["initial_board"] = list(reversed(ids[:6]))
    b = service.accept_casual_artifact(p.installation.pack_id, p.installation.version, **args)
    assert a.config_digest != b.config_digest
    schema = json.loads(Path("contracts/durable-http.schema.json").read_text())
    for name, body in [
        ("packs", service.list_packs()),
        ("artifact", service.get_artifact(a.artifact_id)),
    ]:
        Draft202012Validator(dict(schema, **{"$ref": f"#/$defs/{name}"})).validate(body)


def test_real_verifier_rejects_missing_model(setup, raw):
    _, service = setup

    class WrongModel:
        def identity(self):
            return {}

    service.embedder = WrongModel()
    with pytest.raises(Exception, match="fingerprint"):
        install(service, raw)
    assert service.list_packs()["items"] == []


def test_busy_no_new_reservation(setup, raw):
    from semaphore_hub.packs.service import _INSTALL_LOCK

    tx, service = setup
    with _INSTALL_LOCK:
        with pytest.raises(Conflict, match="busy"):
            install(service, raw)
    with tx() as db:
        assert db.execute("SELECT count(*) FROM install_reservations").fetchone()[0] == 0


def test_invalid_artifact_is_not_stored(setup, raw, measured):
    tx, service = setup
    p = install(service, raw)
    with pytest.raises(ValueError):
        service.accept_casual_artifact(
            p.installation.pack_id,
            p.installation.version,
            operator_id="admin",
            initial_board=["unknown"],
            schedule=[],
        )
    with tx() as db:
        assert db.execute("SELECT count(*) FROM artifacts").fetchone()[0] == 0


def test_corrupt_existing_asset_fails_closed(setup, raw, measured):
    _, service = setup
    h = manifest_hashes(parse_manifest(raw))
    (service.root / (h.manifest_digest + ".manifest")).write_bytes(b"wrong")
    with pytest.raises(Conflict, match="asset"):
        install(service, raw)
    assert service.list_packs()["items"] == []


def test_artifact_limit_preserves_public_reads(setup, raw, measured):
    tx, service = setup
    p = install(service, raw)
    ids = [e["id"] for e in parse_manifest(raw).manifest["entries"]]
    a = service.accept_casual_artifact(
        p.installation.pack_id,
        p.installation.version,
        operator_id="admin",
        initial_board=ids[:6],
        schedule=[],
    )
    with tx() as db:
        repo = SQLitePacks(db)
        for n in range(99):
            repo.add_artifact(replace(a, artifact_id=f"artifact-{n}"))
        with pytest.raises(Conflict, match="limit"):
            repo.add_artifact(replace(a, artifact_id="too-many"))
    assert len(service.get_pack(p.installation.pack_id, p.installation.version)["artifacts"]) == 100


def test_retirement_during_verification_prevents_publish(setup, raw, measured, monkeypatch):
    tx, service = setup

    def retire(*args):
        with tx() as db:
            db.execute("UPDATE packs SET retired_at=1")
        return measured(*args)

    monkeypatch.setattr("semaphore_hub.packs.service.verify_pack", retire)
    with pytest.raises(Conflict, match="owner"):
        install(service, raw)
    assert service.list_packs()["items"] == []
