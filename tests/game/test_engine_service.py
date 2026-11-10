import json
import threading
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest
from experiments.game_server.__main__ import make_server
from experiments.game_server.artifacts import prepare_artifact
from experiments.game_server.service import GameService, ProtocolError
from jsonschema import Draft202012Validator
from tests.core.test_verification import FakeEmbedder

from semaphore_core.game import ClueCommand, complete, initial_state, snapshot, submit
from semaphore_core.verification import CoreValidationError, load

ROOT = Path(__file__).resolve().parents[2]


def binding(mode="event"):
    return prepare_artifact(
        (ROOT / "fixtures/w3/calibration-authored.json").read_bytes(), FakeEmbedder(), mode=mode
    )


def test_timeout_precedence_retry_and_immutable_state():
    artifact, _ = binding()
    state = initial_state(artifact, game_id="test")
    cmd = ClueCommand("a", 0, "private test association")
    admitted = submit(state, cmd, now_ms=0, inference_slot_available=True)
    assert state.pending is None and state.revision == 0
    assert admitted.effects[0].text == "private test association"
    t = complete(
        admitted.state, command_id="a", now_ms=5000, scores={i: 1.0 for i in admitted.state.board}
    )
    assert t.state.receipts["a"]["outcome"] == "inference_timeout"
    # Same-time spawn advances first; a timed-out worker cannot clear it.
    assert t.state.score == 0 and len(t.state.board) == 7
    again = submit(t.state, cmd, now_ms=5000, inference_slot_available=True)
    assert again.receipt["outcome"] == "inference_timeout" and not again.effects
    with pytest.raises(TypeError):
        again.state.receipts["a"]["outcome"] = "clear"
    with pytest.raises(CoreValidationError):
        snapshot(t.state, now_ms=4999)


def test_rejected_retry_and_bad_completion_are_cached():
    artifact, _ = binding()
    s = initial_state(artifact, game_id="x")
    rejected = submit(s, ClueCommand("bad", 9, "one"), now_ms=0, inference_slot_available=True)
    assert rejected.receipt["outcome"] == "stale_revision"
    retry = submit(
        rejected.state, ClueCommand("bad", 9, "one"), now_ms=1, inference_slot_available=True
    )
    assert retry.receipt == rejected.receipt and not retry.changed
    t = submit(retry.state, ClueCommand("ok", 0, "one"), now_ms=1, inference_slot_available=True)
    result = complete(t.state, command_id="ok", now_ms=2, scores={"wrong": 1.0})
    assert result.receipt["outcome"] == "inference_failed"
    assert result.state.pending is None


def test_bounded_physical_queue_and_retention():
    release = threading.Event()
    entered = threading.Event()

    class Blocked(FakeEmbedder):
        def embed_queries(self, texts):
            entered.set()
            release.wait(5)
            return super().embed_queries(texts)

    clock = [0.0]
    svc = GameService({"default": binding()}, Blocked(), clock=lambda: clock[0])
    try:
        ids = []
        for n in range(9):
            _, envelope = svc.request(
                "POST", "/experiment/v1/games", b'{"artifact_id":"default","mode":"event"}'
            )
            ids.append(envelope["snapshot"]["game_id"])
            status, env = svc.request(
                "POST",
                f"/experiment/v1/games/{ids[-1]}/commands",
                json.dumps(dict(command_id="c", expected_revision=0, clue="association")).encode(),
            )
            assert env["receipt"]["outcome"] == ("pending" if n < 8 else "overloaded")
        assert entered.wait(1)
        clock[0] = 5.0
        _, env = svc.request("GET", f"/experiment/v1/games/{ids[0]}/receipts/c")
        assert env["receipt"]["outcome"] == "inference_timeout"
        assert not svc.slots.acquire(blocking=False)
        clock[0] = 1000
        with pytest.raises(ProtocolError) as caught:
            svc.request("GET", f"/experiment/v1/games/{ids[0]}")
        assert caught.value.code == "game_expired" and caught.value.status == 410
        with pytest.raises(ProtocolError):
            svc.request("POST", "/experiment/v1/games", b" " * 16385)
    finally:
        release.set()
        svc.close()


def test_real_http_frozen_envelopes_and_static_mount(tmp_path):
    svc = GameService({"default": binding()}, FakeEmbedder())
    (tmp_path / "web").mkdir()
    (tmp_path / "web/index.html").write_text("<h1>local</h1>")
    server = make_server(svc, port=0, web_root=tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    try:
        request = Request(
            origin + "/experiment/v1/games",
            data=b'{"artifact_id":"default","mode":"event"}',
            headers={"Content-Type": "application/json"},
        )
        with urlopen(request) as response:
            assert response.status == 201
            env = json.load(response)
        Draft202012Validator(load("events.schema.json")).validate(env)
        ident = env["snapshot"]["game_id"]
        with urlopen(origin + f"/experiment/v1/games/{ident}") as response:
            assert json.load(response)["sequence"] == 1
        with urlopen(origin + "/web/index.html") as response:
            assert response.read() == b"<h1>local</h1>"
        with pytest.raises(HTTPError) as caught:
            urlopen(origin + "/web/../pyproject.toml")
        assert caught.value.code == 404
        with pytest.raises(HTTPError) as caught:
            urlopen(
                Request(
                    origin + "/experiment/v1/games", data=b"{}", headers={"Content-Length": "16385"}
                )
            )
        assert caught.value.code == 400
    finally:
        server.shutdown()
        server.server_close()
        svc.close()
        thread.join(1)
