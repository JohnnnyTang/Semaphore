# Callable experimental core boundary

These are specified W4 interfaces, not implemented functions. Pure validation,
hashing, legality, sampling and metrics do not perform IO. Embeddings are injected
through the existing synchronous `EmbeddingProvider`-style query/entry methods
(`OllamaEmbedder.embed_queries` and `embed_entries`); do not invoke on an event loop.

The Python module target is `semaphore_core.verification`. The following frozen
types/signatures are normative; schema-defined mappings remain ordinary dicts.
All exceptions use `CoreValidationError.code: str` and `.path: tuple[str | int,
...]` (empty for global errors); their message contains no submitted content.
Adapter exceptions propagate with their existing sanitized shape.

```python
from dataclasses import dataclass
from typing import Any, Protocol
from collections.abc import Sequence


@dataclass(frozen=True)
class ManifestInput:
    raw: bytes
    manifest: dict[str, Any]  # N-normalized text fields; metadata preserved


@dataclass(frozen=True)
class ManifestHashes:
    manifest_digest: str
    semantic_hash: str
    vector_hash: str


@dataclass(frozen=True)
class ClueDecision:
    legal: bool
    reason: str | None  # None, empty_tokens, target_phrase


@dataclass(frozen=True)
class RankedEntry:
    entry_id: str
    score: float
    bucket: int
    rank: int  # one-based


class Embedder(Protocol):
    def identity(self) -> dict[str, Any]: ...
    def embed_queries(self, texts: Sequence[str]) -> list[list[float]]: ...
    def embed_entries(self, texts: Sequence[str]) -> list[list[float]]: ...


def parse_manifest(raw: bytes) -> ManifestInput: ...
def manifest_hashes(value: ManifestInput) -> ManifestHashes: ...
def check_clue(clue: str, target: dict[str, Any]) -> ClueDecision: ...
def rank_vectors(
    query: Sequence[float], candidates: Sequence[tuple[str, Sequence[float]]]
) -> tuple[RankedEntry, ...]: ...
def sample_decoys(
    semantic_hash: str, target_id: str, sample: int, entries: Sequence[tuple[str, Sequence[float]]]
) -> tuple[str, ...]: ...
def verify_pack(value: ManifestInput, embedder: Embedder, ruleset_id: str) -> dict[str, Any]: ...
```

`manifest_hashes` uses raw bytes only for manifest_digest and normalized mapping
for projections. `check_clue` applies N and throws hygiene_invalid for invalid
text/length, then returns a decision for well-formed text. `parse_manifest`
checks every supplied clue with that same function and rejects an illegal clue.
Reports must satisfy verification.schema.json plus cross-field invariants in
verification.md. Structural examples need not be legal packs or measured reports.

| Operation | Input | Result |
|---|---|---|
| parse_manifest | raw bytes | validated normalized manifest plus exact raw bytes, or typed error |
| manifest_hashes | validated manifest and raw bytes | manifest_digest, semantic_hash, vector_hash |
| check_clue | normalized clue, target entry | legal boolean and stable reason |
| rank_vectors | query vector, ordered (ID, vector) candidates | ordered (ID, raw score, bucket), one-based ranks |
| sample_decoys | semantic_hash, target ID, sample 0..4, entry vectors | 19 unique IDs |
| verify_pack | validated manifest, raw bytes, pinned embedder, ruleset ID | schema-conforming measured report or typed error |

Input rejection reasons: invalid_json, body_too_large, schema_invalid,
hygiene_invalid, duplicate_entry, test_coverage, duplicate_clue, illegal_clue.
Inference reasons retain EmbeddingUnavailable, EmbeddingHTTPError and
EmbeddingResponseError; identity mismatch is EmbeddingResponseError. No partial
vectors/reports escape on failure. Unknown targets/candidate IDs and duplicate
candidate IDs fail validation. Keep raw clues and raw upstream errors private.

Numeric policy `bucket-1e-5-id-v1`: validate all vector components are finite
binary64 values, dimensions exactly 2560, absolute L2 norm error ≤0.001. Reject
instead of renormalizing. Compute dot as dimension-ordered binary64 products and
left-to-right binary64 addition starting at 0.0, without FMA or reassociation.
Do not clamp the result; validated near-unit vectors can exceed 1 slightly.
Set integer bucket `floor(score / 0.00001 + 0.5)`; sort by descending bucket,
then ASCII entry ID ascending. IDs obey the manifest ASCII grammar. This is a
total order; pairwise epsilon equivalence is not transitive and is prohibited.
Display rounds never affect ranking. Negative scores follow the same floor
formula. Parity tolerance 1e-5 applies to comparing raw scores, not sorting.
Runtimes may cross a bucket boundary within tolerance: compare ordered IDs too;
any rank/pass disagreement must be reported and resolved, not hidden by tolerance.

Query text receives the lock's exact prefix; entry text receives no prefix.
num_ctx=512, truncate=false. The service normalizes; core validates norms.
Entry cache key is (vector_hash, fingerprint_hash); report identity additionally
includes semantic_hash, protocol_hash and ruleset_id. Model assets and vectors
come only from the configured trusted adapter, never a pack upload.
