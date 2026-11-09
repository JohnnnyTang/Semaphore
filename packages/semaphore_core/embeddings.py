"""Provisional LAN Ollama adapter for the selected development model.

No model downloads, fallback scores, automatic retries, or implicit text cleanup.
Call from a worker, not an async server's event loop. Each HTTP operation has a
socket timeout; this is not an overall gameplay deadline or cancellation API.
"""

import hashlib
import json
import math
import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

MODEL = "qwen3-embedding:4b"
DIMENSIONS = 2560
CONTEXT_LENGTH = 512
QUERY_PREFIX = (
    "Instruct: Given a word-association game clue, retrieve the words or phrases "
    "most closely associated with the clue.\nQuery: "
)
POLICY = "semaphore-qwen4b-association-v1"
MAX_RESPONSE_BYTES = 8 * 1024 * 1024


class EmbeddingError(RuntimeError):
    """A failed request must not be interpreted as a semantic result."""


class EmbeddingUnavailable(EmbeddingError):
    """Connection, timeout, or interrupted HTTP response."""


class EmbeddingResponseError(EmbeddingError):
    """The service returned incompatible or malformed data."""


class EmbeddingHTTPError(EmbeddingError):
    def __init__(self, status: int) -> None:
        self.status = status
        super().__init__(f"Ollama returned HTTP {status}; no embeddings accepted")


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass(frozen=True)
class OllamaConfig:
    base_url: str
    timeout_seconds: float = 30.0
    batch_size: int = 16
    expected_digest: str | None = None

    def __post_init__(self) -> None:
        parts = urlsplit(self.base_url)
        # Validate port eagerly, before any network operation.
        _ = parts.port
        if (
            parts.scheme not in {"http", "https"}
            or not parts.hostname
            or parts.username is not None
            or parts.password is not None
            or parts.path not in {"", "/"}
            or parts.query
            or parts.fragment
            or any(c.isspace() for c in self.base_url)
        ):
            raise ValueError("base URL must be an HTTP(S) origin without credentials or a path")
        if not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0:
            raise ValueError("timeout must be finite and positive")
        if type(self.batch_size) is not int or not 1 <= self.batch_size <= 64:
            raise ValueError("batch size must be an integer from 1 to 64")
        if self.expected_digest is not None and not re.fullmatch(
            r"[0-9a-f]{64}", self.expected_digest
        ):
            raise ValueError("expected digest must be the full lowercase 64-hex model digest")

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "OllamaConfig":
        env = os.environ if env is None else env
        base_url = env.get("SEMAPHORE_OLLAMA_BASE_URL")
        if not base_url:
            raise ValueError("set SEMAPHORE_OLLAMA_BASE_URL to the LAN Ollama origin")
        return cls(
            base_url=base_url,
            timeout_seconds=float(env.get("SEMAPHORE_OLLAMA_TIMEOUT_SECONDS", "30")),
            batch_size=int(env.get("SEMAPHORE_OLLAMA_BATCH_SIZE", "16")),
            expected_digest=env.get("SEMAPHORE_OLLAMA_MODEL_DIGEST") or None,
        )


class OllamaEmbedder:
    """Batch inputs in order and validate every vector before returning any result."""

    def __init__(self, config: OllamaConfig) -> None:
        self.config = config

    def _request(self, path: str, payload: dict | None = None) -> dict:
        request = Request(
            self.config.base_url.rstrip("/") + path,
            data=None if payload is None else json.dumps(payload, allow_nan=False).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        # LAN traffic must not accidentally follow machine-wide proxy settings.
        opener = build_opener(ProxyHandler({}), _NoRedirect())
        try:
            with opener.open(request, timeout=self.config.timeout_seconds) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        except HTTPError as exc:
            exc.close()
            # Service bodies can contain input text; never echo them in errors.
            raise EmbeddingHTTPError(exc.code) from None
        except (URLError, OSError, HTTPException):
            raise EmbeddingUnavailable("Ollama unavailable or request timed out") from None
        if len(raw) > MAX_RESPONSE_BYTES:
            raise EmbeddingResponseError("Ollama response exceeds the size limit")
        try:
            result = json.loads(raw)
        except (ValueError, UnicodeError, RecursionError):
            raise EmbeddingResponseError("Ollama returned invalid JSON") from None
        if not isinstance(result, dict) or "error" in result:
            raise EmbeddingResponseError("Ollama returned an error or a non-object response")
        return result

    def identity(self) -> dict:
        """Snapshot installed tag identity. This is an experiment fingerprint only."""
        version = self._request("/api/version").get("version")
        models = self._request("/api/tags").get("models")
        if not isinstance(version, str) or not version or not isinstance(models, list):
            raise EmbeddingResponseError("Ollama version or model inventory is malformed")
        matches = [m for m in models if isinstance(m, dict) and m.get("name") == MODEL]
        if len(matches) != 1:
            raise EmbeddingResponseError(f"exact model tag {MODEL} is not installed uniquely")
        model = matches[0]
        digest = model.get("digest")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise EmbeddingResponseError("Ollama did not report a complete model digest")
        if self.config.expected_digest and digest != self.config.expected_digest:
            raise EmbeddingResponseError("installed model digest differs from the configured pin")
        details = model.get("details")
        if not isinstance(details, dict):
            raise EmbeddingResponseError("Ollama did not report model details")
        return {
            "provider": "ollama",
            "model": MODEL,
            "digest": digest,
            "ollama_version": version,
            "model_details": details,
            "dimensions": DIMENSIONS,
            "encoding_policy": POLICY,
            "query_prefix": QUERY_PREFIX,
            "entry_prefix": "",
            "num_ctx": CONTEXT_LENGTH,
            "truncate": False,
            "normalization": "ollama-l2-validated",
        }

    def running_model(self) -> dict:
        models = self._request("/api/ps").get("models")
        if not isinstance(models, list):
            raise EmbeddingResponseError("Ollama running-model inventory is malformed")
        matches = [m for m in models if isinstance(m, dict) and m.get("name") == MODEL]
        if len(matches) != 1:
            raise EmbeddingResponseError("selected model is not reported as loaded")
        return matches[0]

    def embed_queries(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        return self._embed(texts, QUERY_PREFIX)

    def embed_entries(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        return self._embed(texts, "")

    def _embed(self, texts: Sequence[str], prefix: str) -> tuple[tuple[float, ...], ...]:
        if isinstance(texts, (str, bytes)):
            raise ValueError("pass a sequence of texts, not a single string")
        texts = tuple(texts)
        if any(not isinstance(t, str) or not t.strip() or len(t) > 8192 for t in texts):
            raise ValueError("texts must be nonblank strings of at most 8192 characters")
        if texts and self.config.expected_digest:
            # Enforce the operator's pin even outside the experiment runner.
            self.identity()
        vectors = []
        for offset in range(0, len(texts), self.config.batch_size):
            batch = texts[offset : offset + self.config.batch_size]
            result = self._request(
                "/api/embed",
                {
                    "model": MODEL,
                    "input": [prefix + text for text in batch],
                    "dimensions": DIMENSIONS,
                    "truncate": False,
                    "keep_alive": "30m",
                    "options": {"num_ctx": CONTEXT_LENGTH},
                },
            )
            if result.get("model") != MODEL:
                raise EmbeddingResponseError("embedding response model differs from requested tag")
            rows = result.get("embeddings")
            if not isinstance(rows, list) or len(rows) != len(batch):
                raise EmbeddingResponseError("embedding count differs from input count")
            for row in rows:
                if not isinstance(row, list) or len(row) != DIMENSIONS:
                    raise EmbeddingResponseError("embedding dimensions differ from 2560")
                if any(type(v) not in (int, float) for v in row):
                    raise EmbeddingResponseError("embedding components must be finite numbers")
                try:
                    vector = tuple(float(v) for v in row)
                    norm = math.sqrt(sum(v * v for v in vector))
                except (OverflowError, ValueError):
                    raise EmbeddingResponseError("embedding components are out of range") from None
                if not math.isfinite(norm) or not math.isclose(norm, 1.0, abs_tol=1e-3):
                    raise EmbeddingResponseError("embedding must be finite and L2-normalized")
                vectors.append(vector)
        return tuple(vectors)


def fingerprint_hash(identity: dict) -> str:
    """Experiment namespace; not the draft production verification fingerprint."""
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(b"semaphore-ollama-experiment-v1\0" + encoded.encode()).hexdigest()
