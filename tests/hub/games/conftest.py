import json
from contextlib import contextmanager
from pathlib import Path

import pytest

from semaphore_core.verification import load, manifest_hashes
from semaphore_hub.packs import PackService
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
