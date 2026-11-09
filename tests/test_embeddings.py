"""Offline contract tests: a loopback HTTP stub, never a real embedding service."""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from semaphore_core.embeddings import (
    DIMENSIONS,
    MODEL,
    QUERY_PREFIX,
    EmbeddingHTTPError,
    EmbeddingResponseError,
    EmbeddingUnavailable,
    OllamaConfig,
    OllamaEmbedder,
    fingerprint_hash,
)


def unit(index=0):
    return [float(i == index) for i in range(DIMENSIONS)]


@pytest.fixture
def service():
    state = {"requests": [], "status": 200, "delay": 0, "digest": "a" * 64}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            self.respond(None)

        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            self.respond(payload)

        def respond(self, payload):
            state["requests"].append((self.path, payload))
            if state["delay"]:
                time.sleep(state["delay"])
            if self.path == "/api/embed":
                body = {"model": MODEL, "embeddings": [unit() for _ in payload["input"]]}
            elif self.path == "/api/version":
                body = {"version": "test-ollama"}
            else:
                body = {"models": [{"name": MODEL, "digest": state["digest"], "details": {}}]}
            raw = state.get("raw", json.dumps(body).encode())
            self.send_response(state["status"])
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Location", "/redirected")
            self.end_headers()
            try:
                self.wfile.write(raw)
            except OSError:
                pass  # Expected when a timeout test closes its socket.

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True)
    thread.start()
    state["url"] = f"http://127.0.0.1:{server.server_port}"
    yield state
    server.shutdown()
    server.server_close()
    thread.join()


def test_http_batching_query_formatting_and_entry_order(service, monkeypatch):
    # Even a configured system proxy must not receive LAN embedding requests.
    monkeypatch.setenv("http_proxy", "http://127.0.0.1:1")
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
    client = OllamaEmbedder(OllamaConfig(service["url"], batch_size=2))
    queries = client.embed_queries(["ice", "Sea", "blue"])
    entries = client.embed_entries(["Ice", "Sea"])
    assert len(queries) == 3 and len(entries) == 2
    assert all(len(vector) == DIMENSIONS for vector in queries)
    requests = [body for path, body in service["requests"] if path == "/api/embed"]
    assert [body["input"] for body in requests] == [
        [QUERY_PREFIX + "ice", QUERY_PREFIX + "Sea"],
        [QUERY_PREFIX + "blue"],
        ["Ice", "Sea"],
    ]
    assert all(body["model"] == MODEL and body["truncate"] is False for body in requests)
    assert all(body["options"] == {"num_ctx": 512} for body in requests)


def test_batches_preserve_vector_order(monkeypatch):
    client = OllamaEmbedder(OllamaConfig("http://unused", batch_size=2))
    monkeypatch.setattr(
        client,
        "_request",
        lambda path, body: {"model": MODEL, "embeddings": [unit(int(t)) for t in body["input"]]},
    )
    vectors = client.embed_entries(["3", "1", "2"])
    assert [v.index(1.0) for v in vectors] == [3, 1, 2]


def test_empty_input_makes_no_http_request(service):
    assert OllamaEmbedder(OllamaConfig(service["url"])).embed_entries([]) == ()
    assert service["requests"] == []


@pytest.mark.parametrize("texts", ["ice", [""], [" \n"], [None], ["x" * 8193]])
def test_invalid_inputs_fail_before_contacting_service(service, texts):
    with pytest.raises(ValueError):
        OllamaEmbedder(OllamaConfig(service["url"])).embed_queries(texts)
    assert not service["requests"]


@pytest.mark.parametrize(
    "row",
    [
        [1.0],
        [0.0] * DIMENSIONS,
        [2.0] + [0.0] * (DIMENSIONS - 1),
        [float("nan")] * DIMENSIONS,
        [float("inf")] * DIMENSIONS,
        [True] * DIMENSIONS,
        ["0"] * DIMENSIONS,
        [10**400] * DIMENSIONS,
    ],
)
def test_invalid_vectors_are_rejected(monkeypatch, row):
    client = OllamaEmbedder(OllamaConfig("http://unused"))
    monkeypatch.setattr(client, "_request", lambda *args: {"model": MODEL, "embeddings": [row]})
    with pytest.raises(EmbeddingResponseError):
        client.embed_entries(["ocean"])


@pytest.mark.parametrize(
    "response",
    [
        {"model": MODEL, "embeddings": []},
        {"model": MODEL, "embeddings": [unit(), unit()]},
        {"model": "wrong-model", "embeddings": [unit()]},
        {"model": MODEL},
    ],
)
def test_wrong_model_or_vector_count_is_rejected(monkeypatch, response):
    client = OllamaEmbedder(OllamaConfig("http://unused"))
    monkeypatch.setattr(client, "_request", lambda *args: response)
    with pytest.raises(EmbeddingResponseError):
        client.embed_entries(["ocean"])


@pytest.mark.parametrize("status", [302, 404, 429, 500])
def test_http_errors_are_not_retried_redirected_or_echoed(service, status):
    service.update(status=status, raw=b'{"error":"PRIVATE CLUE"}')
    with pytest.raises(EmbeddingHTTPError) as error:
        OllamaEmbedder(OllamaConfig(service["url"])).embed_entries(["ocean"])
    assert error.value.status == status
    assert "PRIVATE" not in str(error.value)
    assert len(service["requests"]) == 1


@pytest.mark.parametrize("raw", [b"not JSON", b"[]", b'{"error":"PRIVATE CLUE"}', b"\xff"])
def test_bad_json_and_service_error_bodies_are_rejected(service, raw):
    service["raw"] = raw
    with pytest.raises(EmbeddingResponseError) as error:
        OllamaEmbedder(OllamaConfig(service["url"])).embed_entries(["ocean"])
    assert "PRIVATE" not in str(error.value)


def test_timeout_is_explicit_and_not_retried(service):
    service["delay"] = 0.15
    with pytest.raises(EmbeddingUnavailable):
        OllamaEmbedder(OllamaConfig(service["url"], timeout_seconds=0.02)).embed_entries(["sea"])
    assert len(service["requests"]) == 1


def test_model_identity_pin_and_fingerprint(service):
    client = OllamaEmbedder(OllamaConfig(service["url"], expected_digest="a" * 64))
    identity = client.identity()
    assert identity["model"] == MODEL and identity["dimensions"] == DIMENSIONS
    assert fingerprint_hash(identity) == fingerprint_hash(dict(reversed(list(identity.items()))))
    changed = {**identity, "query_prefix": "different"}
    assert fingerprint_hash(identity) != fingerprint_hash(changed)
    service["digest"] = "b" * 64
    with pytest.raises(EmbeddingResponseError, match="pin"):
        client.identity()
    with pytest.raises(EmbeddingResponseError, match="pin"):
        client.embed_entries(["ocean"])
    assert not any(path == "/api/embed" for path, _ in service["requests"])


def test_smoke_check_exercises_both_encodings_and_loaded_identity(service):
    from experiments.model_eval.ollama_eval import smoke_check

    result = smoke_check(OllamaEmbedder(OllamaConfig(service["url"])))
    assert result["status"] == "connected"
    assert result["dimensions"] == DIMENSIONS
    assert result["running_model"]["digest"] == result["fingerprint"]["digest"]
    assert [path for path, _ in service["requests"]].count("/api/embed") == 2


def test_oversized_response_is_rejected_before_json_decode(service, monkeypatch):
    monkeypatch.setattr("semaphore_core.embeddings.MAX_RESPONSE_BYTES", 32)
    service["raw"] = b"x" * 33
    with pytest.raises(EmbeddingResponseError, match="size limit"):
        OllamaEmbedder(OllamaConfig(service["url"])).embed_entries(["ocean"])


@pytest.mark.parametrize(
    "url",
    [
        "ftp://host",
        "http://user:secret@host",
        "http://host/api",
        "http://host?q=1",
        "http://host#fragment",
        "http://",
        "http://host:bad",
        "http://host name",
    ],
)
def test_invalid_origins_are_rejected(url):
    with pytest.raises(ValueError):
        OllamaConfig(url)


def test_environment_configuration_has_no_implicit_host_or_model_override():
    with pytest.raises(ValueError, match="BASE_URL"):
        OllamaConfig.from_env({})
    config = OllamaConfig.from_env({"SEMAPHORE_OLLAMA_BASE_URL": "http://server:11434"})
    assert config.batch_size == 16 and config.timeout_seconds == 30
    for kwargs in (
        {"timeout_seconds": float("nan")},
        {"batch_size": 0},
        {"expected_digest": "abc"},
    ):
        with pytest.raises(ValueError):
            OllamaConfig("http://server", **kwargs)
