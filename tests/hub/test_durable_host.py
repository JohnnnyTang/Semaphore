import base64
import json
from contextlib import closing

import pytest

from semaphore_hub.durable_host import DurableHost
from semaphore_hub.operations import ExternalLedger
from semaphore_hub.policy import CLEANUP_INTERVAL_MS, TransportPolicy
from semaphore_hub.runtime_testing import FakeClock
from semaphore_hub.storage import connect


@pytest.fixture
def host(tmp_path):
    for name in ("csrf", "ledger-key", "backup-key"):
        (tmp_path / name).write_bytes(b"k" * 32)
    (tmp_path / "keys").write_text(
        json.dumps({"active": "v1", "keys": {"v1": base64.b64encode(b"h" * 32).decode()}})
    )
    ExternalLedger(tmp_path / "ledger", b"k" * 32, create=True)
    result = DurableHost(
        tmp_path / "hub.db",
        tmp_path / "assets",
        TransportPolicy("http://localhost:8080"),
        tmp_path / "csrf",
        tmp_path / "keys",
        tmp_path / "ledger",
        tmp_path / "ledger-key",
        tmp_path / "backups",
        tmp_path / "backup-key",
        clock=FakeClock(),
    )
    yield result
    result.close()


def test_readiness_scheduler_and_failure_close(host, monkeypatch):
    assert host.handle("GET", "/api/v1/config", [("host", "localhost:8080")]).status == 503
    host.start()
    assert host.handle("GET", "/api/v1/config", [("host", "localhost:8080")]).status == 200
    host.maintenance()
    first = list(host.backups.root.glob("*.backup"))
    assert len(first) == 1
    host.maintenance()
    assert list(host.backups.root.glob("*.backup")) == first
    host.last_backup -= CLEANUP_INTERVAL_MS
    host.maintenance()
    assert len(list(host.backups.root.glob("*.backup"))) == 2

    def fail():
        raise OSError("maintenance failed")

    monkeypatch.setattr(host.games, "tick", fail)
    with pytest.raises(OSError):
        host.maintenance()
    assert not host.ready
    assert host.handle("GET", "/api/v1/config", []).status == 503


def test_restore_replays_newer_ledger_and_refuses_existing_destination(host, tmp_path):
    account = host.auth.bootstrap("operator", "Operator", "long test password")
    host.start()
    backup = host.backup()
    host.operations.delete_account(account)
    destination = tmp_path / "restored.db"
    host.restore(backup, destination)
    with closing(connect(destination)) as db:
        row = db.execute("SELECT deleted_at,display_name FROM accounts").fetchone()
        assert row[0] is not None and row[1] is None
    with pytest.raises(FileExistsError):
        host.restore(backup, destination)


def test_operator_only_host_cannot_serve(host):
    with pytest.raises(RuntimeError, match="pinned model"):
        host.serve(8080)
    assert not host.ready


def test_missing_ledger_never_recreated(host):
    host.ledger.path.unlink()
    with pytest.raises(FileNotFoundError):
        host.start()
    assert not host.ready


def test_populated_host_pending_recovery_and_missing_asset(host, monkeypatch):
    from pathlib import Path

    from semaphore_core.verification import load, manifest_hashes
    from semaphore_hub.runtime_testing import ManualInference

    def measured(value, embedder, ruleset):
        hashes = manifest_hashes(value)
        embedder.entry_vectors = [[1.0] + [0.0] * 2559 for _ in value.manifest["entries"]]
        return dict(
            manifest_digest=hashes.manifest_digest,
            semantic_hash=hashes.semantic_hash,
            vector_hash=hashes.vector_hash,
            fingerprint_hash=load("model-lock.json")["fingerprint_sha256"],
            protocol_hash="a" * 64,
            ruleset_id=ruleset,
            status="measured",
            metrics=dict(reachability=1.0),
        )

    monkeypatch.setattr("semaphore_hub.packs.service.verify_pack", measured)
    owner = host.auth.bootstrap("operator", "Operator", "long test password")
    manifest = json.loads(Path("packs/everyday.json").read_bytes())
    manifest["pack"]["tags"] = []
    published = host.packs.install(
        json.dumps(manifest).encode(),
        owner_id=owner,
        operator_id=owner,
        rights_reference="synthetic host test",
        accept=True,
    )
    ids = [json.loads(item)["id"] for item in published.entries_json]
    artifact = host.packs.accept_casual_artifact(
        published.installation.pack_id,
        published.installation.version,
        operator_id=owner,
        initial_board=ids[:5],
        schedule=[],
    )
    host.start()
    host.games.inference = ManualInference()
    gid = host.games.create(owner, {"mode": "casual", "artifact_id": artifact.artifact_id})[
        "snapshot"
    ]["game_id"]
    command = {"command_id": "pending", "expected_revision": 0, "clue": "association"}
    assert host.games.command(owner, gid, command)["receipt"]["outcome"] == "pending"
    host.backup()
    host.ready = False
    host.start()
    assert host.games.command(owner, gid, command)["receipt"]["outcome"] == "game_over"
    with host.transactions() as db:
        assert db.execute("SELECT count(*) FROM scores").fetchone()[0] == 0
    asset = next(host.assets.glob("*.vectors"))
    asset.unlink()
    host.ready = False
    with pytest.raises(ValueError):
        host.start()
    assert not host.ready


def test_close_drains_inference_before_return(host):
    import threading

    from semaphore_core.embeddings import fingerprint_hash
    from semaphore_hub.interfaces import InferenceRequest
    from semaphore_hub.runtime import QueuedInference

    entered, release, closed = threading.Event(), threading.Event(), threading.Event()

    class Embedder:
        def identity(self):
            return {"synthetic": True}

        def embed_queries(self, texts):
            entered.set()
            assert release.wait(5)
            return [[1.0] + [0.0] * 2559 for _ in texts]

    host.inference = QueuedInference(Embedder(), clock=host.clock)
    callbacks = []
    assert host.inference.submit(
        InferenceRequest("g", "c", "synthetic", fingerprint_hash({"synthetic": True}), 20000),
        callbacks.append,
    )
    assert entered.wait(3)

    def close():
        host.close()
        closed.set()

    thread = threading.Thread(target=close)
    thread.start()
    try:
        assert not closed.wait(0.05)
        release.set()
        assert closed.wait(3)
        assert not host.inference._thread.is_alive()
        assert callbacks == []
    finally:
        release.set()
        thread.join(5)


def test_concrete_listener_runs_scheduler_and_authenticated_dispatch(host, monkeypatch):
    import threading
    from http.client import HTTPConnection

    from semaphore_hub.durable_host import DurableServer

    listening, bound, failures = threading.Event(), [], []

    class ObservedServer(DurableServer):
        def __init__(self, address, dispatcher):
            super().__init__(address, dispatcher)
            assert host.ready
            assert list(host.backups.root.glob("*.backup"))
            bound.append(self.server_address[1])
            listening.set()

    class IdentityOnly:
        def identity(self):
            return {"synthetic": True}

    from semaphore_hub.browser_assets import BrowserAssets

    host.browser = BrowserAssets("web")
    host.embedder = IdentityOnly()
    monkeypatch.setattr("semaphore_hub.durable_host.DurableServer", ObservedServer)

    def serve():
        try:
            host.serve(0)
        except BaseException as exc:
            failures.append(exc)
            listening.set()

    worker = threading.Thread(target=serve)
    worker.start()
    try:
        assert listening.wait(5)
        assert not failures
        with closing(HTTPConnection("127.0.0.1", bound[0], timeout=3)) as client:
            client.request("GET", "/api/v1/history", headers={"Host": "localhost:8080"})
            assert client.getresponse().status == 401
        with closing(HTTPConnection("127.0.0.1", bound[0], timeout=3)) as client:
            client.request("GET", "/web/durable.html", headers={"Host": "localhost:8080"})
            response = client.getresponse()
            assert response.status == 200
            assert response.getheader("Content-Type") == "text/html; charset=utf-8"
            assert b"durable-app.mjs" in response.read()
        with closing(HTTPConnection("127.0.0.1", bound[0], timeout=3)) as client:
            client.request("GET", "/web/durable.html", headers={"Host": "attacker.invalid"})
            assert client.getresponse().status == 403
    finally:
        host.close()
        worker.join(5)
    assert not worker.is_alive()
    assert not failures
