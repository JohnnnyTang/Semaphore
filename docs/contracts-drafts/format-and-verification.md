# Manifest, hashing and verification proposal

All identifiers here are `draft-w2`. W3 must freeze the algorithm and measured
parameters before they drive publication. A JSON Schema pass is only structural.

## Parse and validate in a fixed order

1. Accept a single uncompressed UTF-8 JSON object, at most 8 MiB (8,388,608 bytes).
   Reject archives, invalid UTF-8, BOM, duplicate object keys, non-finite numbers,
   unpaired surrogates, nesting deeper than 16 containers and trailing content.
   Stream the byte limit before parsing; JSON Schema alone cannot enforce it.
2. Validate `manifest.schema.json`. All objects are closed. `vectors`, model
   tensors, arbitrary runtime configuration, executable code and external resource
   references are not allowed. Never fetch URLs from metadata or provenance.
3. Normalize display strings with Unicode NFKC and collapsed Unicode whitespace.
   Reject empty or control-containing strings. Limits apply to both original and
   normalized strings, counted as Unicode code points, not UTF-8 bytes. Preserve
   punctuation in display/embed text; casefold only comparison/legality keys.
4. Require 40–5,000 entries, unique stable entry IDs, unique normalized/casefolded
   display labels, exact test-set coverage (no missing or foreign entry IDs),
   and 3–5 unique normalized/casefolded clues per entry. Defaults: aliases and
   forbidden clues `[]`, tier `1`, embed text equal to display text. Alias and
   forbidden lists must also be unique after normalization. IDs are never derived
   from mutable labels. IDs and entry order participate in semantic identity.
5. Apply the frozen shared legality policy to every clue against its entry and
   aliases/forbidden phrases. A rejected clue does not count toward the minimum.
   Proposed token/phrase matching prevents substring false positives; exact stem
   behavior belongs to C/W3 and is deliberately not implemented by this draft
   validator. The hub must not silently drop bad clues and verify the remainder.
6. Verify ownership and immutable version identity before expensive embedding.
   `pack.author` is attribution, never the authenticated owner. A new pack ID is
   reserved atomically for the authenticated uploader. Existing IDs require the
   same owner, including hidden packs and versions still being processed.

`spec_version: 1-draft-w2` differs deliberately from the handoff's illustrative
`1`. Test sets key by entry ID rather than label. The handoff's two-entry sample
also lacks a complete test set and cannot be published. Version strings use
three unsigned decimal components with no leading zero; prerelease syntax is
deferred. Versions are immutable identifiers, not a chronology inferred by sorting
strings. Publication timestamp chooses the current version unless moderation says
otherwise. A required nonempty license/rights statement does not itself establish
that the uploader owns those rights; no automatic license grant is supplied.

## Hashes and cache identity

Use SHA-256 with lowercase hex output. Domain prefixes are ASCII bytes followed by
one NUL byte. Every algorithm carries `semaphore-c14n-draft-w2`; W3 must version
any change. Do not use Python `hash()` or platform random seeds.

| Digest | Bytes | Uses |
| --- | --- | --- |
| `manifest_digest` | Exact accepted upload bytes | Audit and immutable `(pack_id, version)` retry identity |
| `semantic_hash` | `semaphore-semantic-draft-w2\0` + canonical semantic projection | Decoy seed input, test identity |
| `vector_hash` | `semaphore-vectors-draft-w2\0` + canonical entry projection | Entry-vector cache identity, with embedding fingerprint |
| `fingerprint_hash` | `semaphore-model-draft-w2\0` + canonical complete fingerprint | Exact model/runtime/encoding cache identity |

Exact-byte full digest means different whitespace or metadata is a version
conflict for an already published version; CLI packaging therefore emits stable
bytes and users retry the exact artifact. Preserve upload bytes, not a reserialized
copy, in the immutable manifest file. These distinctions are visible in error text.

Semantic projection is `{canonicalization, entries, test_set}`. Each normalized
entry includes `id`, `text`, effective `embed_text`, `aliases`, `forbidden_clues`,
and `tier` in original entry order. Alias/forbidden arrays are sorted by Unicode
code point after normalization because their order has no meaning. Test-set clues
are normalized and sorted by Unicode code point; their authoring order has no
meaning. Do not casefold embedding strings: changing case can change a model's
input. Display metadata, version, author, rights, provenance and `test_report`
are excluded. Thus editing a self-reported report cannot optimize decoy selection.

Vector projection is `{canonicalization, entries: [{id, embed_text}, ...]}` in
entry order. It excludes clues, aliases, forbidden rules, tier and metadata.
The entry ID maps cached rows; display-label changes affect vectors only if they
change the effective embedding text. A label change still changes semantic hash.

Canonical encoding: reject floats; accept null, booleans, strings, safe integers
within ±(2^53−1), arrays and string-keyed objects. Object keys sort by Unicode
code point; arrays preserve order. Encode compact JSON (`separators=(',', ':')`),
UTF-8, literal Unicode, escaping quote, backslash and control characters, no BOM
or trailing newline. No normalization occurs inside the serializer: projections
normalize explicitly. This is a constrained Python-shared protocol, **not JCS**;
the distinction avoids pretending Python number/key serialization matches JCS.
The sample runner includes fixed digest vectors and metamorphic hash checks.

Fingerprint includes repository ID, immutable 40-hex revision, weight/tokenizer
asset SHA-256 digests, runtime package/version map, query and document instructions,
pooling, dimensions, normalization, dtype, max tokens, truncation policy and any
reviewed custom-code digest. All are required for a real report. A candidate name,
floating branch revision or a creator's `provenance.embedding_model` is insufficient.
Numeric threshold configuration is separate from the fingerprint and is hashed in
the verification protocol identity. W3 may select a runtime without custom code;
then `custom_code_sha256` is null. No arbitrary code is loaded from a manifest.

## Bounded hub verification

Initial proposals: ≤5,000 entries, ≤25,000 clues, 19 decoys per clue, five samples
per clue, bottom zone 3, duplicate cosine 0.80, failure when >5% of entries occur
in flagged pairs, reachability threshold 85%. All require B calibration and C
reconciliation. These are configured server values, never uploader inputs.

- Embed entries once using the effective embed text and pinned document encoding.
  Embed legal clues using the pinned query encoding; normalize as fingerprinted.
- Compute duplicate comparisons in bounded blocks; do not retain a full 5,000²
  matrix. Count involved entries, not pair percentage. Report total count plus a
  capped diagnostic list (1,000 pairs), with `diagnostics_truncated` when necessary.
- Derive sample seeds from domain-separated semantic hash, metrics version,
  target entry ID and sample index. Uniform sampling without replacement excludes
  target; use a deterministic hard-decoy component from entry similarity. W3 must
  choose the exact sampler, fraction and tie policy before results are comparable.
- Rank 1 means most similar and corresponds to the bottom of the displayed stack.
  Compute median rank across five samples per clue, then median across that
  entry's legal clues. Reachable means typical rank ≤3. Playability is exactly
  `100 * reachable_entries / total_entries`; mean rank is reported separately.
  Even-sample median is arithmetic mean of the two central ranks. Comparison
  tolerance begins at 1e-5; W3 must settle near-ties and threshold disagreement.
- Use one model process and bounded batches (proposed 32 texts). Gameplay gets
  priority between batches; no concurrent unrestricted upload workers. Propose
  one running verification, four waiting globally, one active job per account,
  10-minute wall-time budget and 64 MiB temporary metadata budget per job.
  Failure to complete within the budget yields `verification_timeout`, never a
  pass. These limits are proposals to measure, not proven capacity claims.
- Upload body cap applies before enqueue; disk quota and global pending-byte cap
  (proposed 64 MiB) apply before durable staging. When full return 429 with bounded
  `Retry-After`, no reservation leak. Check cancellation between batches.

Hub reports in `verification.schema.json` separate computed metrics from the
manifest's optional self-report. Store rejected and failed runs for diagnostics;
neither is a publication. A technical failure is not a poor-quality score. A report
states exact fingerprint/protocol/hash and sample count, numeric tolerance and
truncation; `verified` means declared tests recomputed, not independent test clues,
content rights authentication, universal fun or production performance acceptance.

## Stable error categories

| Code | Layer / HTTP | Repair |
| --- | --- | --- |
| `body_too_large`, `invalid_json` | ingestion / 413, 400 | Reduce bytes or repair encoding/structure |
| `schema_invalid` | schema / 422 | Fix path-specific shape or limit violations |
| `duplicate_entry`, `test_coverage`, `duplicate_clue`, `illegal_clue` | hygiene / 422 | Fix normalized content; do not remove required coverage |
| `unauthenticated`, `forbidden`, `owner_conflict` | identity / 401, 403, 409 | Authenticate as owner; no credential details in response |
| `version_conflict`, `command_conflict` | immutable identity / 409 | New version/command ID; same ID may not change payload |
| `queue_full`, `rate_limited` | admission / 429 | Retry after indicated time |
| `model_unavailable`, `verification_timeout`, `verification_failed` | job / terminal failed state | Operator repairs runtime, then explicit retry |
| `near_duplicates`, `low_reachability` | semantic / terminal rejected state | Revise entries/clues; keep diagnostic counts |
| `stale_revision`, `game_busy`, `game_over`, `illegal_clue` | game / command rejection | Follow authoritative snapshot; rules reconciled in W3 |

All errors carry request ID, code, safe message and at most 100 path issues. Never
echo passwords/session tokens. Clue diagnostics are owner-only job data, not logs
or public leaderboard payloads. Public pack test clues are authored content and
distinct from private real-player attempt logs.
