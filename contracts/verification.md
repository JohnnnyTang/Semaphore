# Experimental verification, W3

This freezes interfaces for W4, not a publication or semantic-quality pass.
The Ollama connectivity check observes the selected 4B Q4_K_M artifact and 2,560
dimensions. Synthetic retrieval calibration and held-out results are recorded in
`docs/evidence/model-evaluation.md`. Actual-protocol synthetic measurements and
sampled Python/Node numeric parity are recorded in `docs/evidence/w3/README.md`;
independent publication calibration, creator parity and human play remain gates.
Reachability 0.85 is provisional; bottom zone
3 is the experimental ruleset choice.
Reports use `measured` or `rejected`; neither authorizes publication. Creator
self reports are untrusted and never substituted for recomputation.

## Input and normalization

Accept at most 8 MiB UTF-8 JSON, without BOM, duplicate keys, nonfinite numbers,
unpaired surrogates or nesting beyond 16 containers. Validate the manifest schema
before semantic checks. IDs and normalized casefolded labels must be unique;
test-set keys must equal entry IDs. Every entry needs 3–5 distinct legal clues.
Reject uploaded vectors and unknown fields. Do not partially verify a bad pack.

`N(text)` is Unicode NFKC, split on Unicode whitespace, join with one ASCII
space; reject empty results and remaining Unicode category C characters.
Lengths count code points, enforced before and after N. Preserve case and
punctuation for embedding. This cleanup is at the canonical pack/live-clue input
boundary; the adapter and the existing research evaluator preserve their supplied
text exactly. It does not retrospectively normalize measured research inputs.
Use Unicode 15.0 (Python 3.12) and casefold only for
equality/legality. Normalized aliases, forbidden clues and clues must be distinct
within each list after casefold. No changes inside the adapter: callers pass N.

Labels, aliases and forbidden phrases with no lexical tokens fail hygiene.
Legality policy `en-reviewed-subset-v1`: tokenize N(text).casefold() into maximal
Unicode letter/number sequences; punctuation separates tokens. Reject clues with
no tokens. Map car/cars to car and run/runs/running/ran to run; all other tokens
map to themselves. Reject when any target label, target alias or target forbidden
phrase's token sequence appears contiguously in the clue. Thus cars is illegal
for car, carpet is legal, and ran is illegal for run. No substring check, stemming,
synonym expansion or general English morphology is claimed. Aliases/forbidden
phrases provide explicit pack-local extensions. General reviewed morphology is
an open release gate. The rule checks the highlighted target only.

## Identity and hashing

Manifest digest is SHA-256 of the exact accepted upload bytes. Preserve those
bytes for immutable version conflicts. Whitespace edits change this digest.
Semantic/vector projection hashes retain the W2 algorithms in
`fixtures/manifests/check_examples.py::projected_hash` exactly, including the
`draft-w2` domain strings and canonicalization marker. This deliberate algorithm
reuse preserves `hash-vectors.json`; the manifest version change does not alter
these projections. Entries retain authored order. Defaults: embed_text=text,
aliases=[], forbidden_clues=[], tier=1. All projected strings use N. Alias and
forbidden lists sort by Unicode code point; test clues sort likewise. Do not
casefold projection text. Metadata, provenance and self reports are excluded.
Vector projections contain only ordered IDs and effective embed text; semantic
projections additionally contain text, aliases, forbidden clues, tier and tests.

Canonical projection encoding is UTF-8 JSON, unescaped Unicode, sorted object
keys, no whitespace, no floats, integers restricted to ±(2^53−1). Strings must
have no surrogates. This is the specified restricted encoding, not general JCS.
Fingerprint hashes intentionally use the existing adapter's distinct encoding:
`json.dumps(identity, sort_keys=True, separators=(",", ":"), allow_nan=False)`
with default ASCII escaping, UTF-8, SHA-256, prefixed with the exact bytes
`b"semaphore-ollama-experiment-v1\0"`, matching the adapter and retained reports. Preserve
raw service model_details. Local parent paths are identity data, not file reads.
Do not redact or normalize details and keep claiming the original hash.

Ollama identity is explicitly `ollama-artifact-runtime-v1`. The lock pins digest,
tag, quantization, dimensions, service version and encoding options. Compare the
entire fingerprint and hash for reuse; changed raw details invalidate caches.
Before/after service snapshots must match; a service frozen during verification
is an operational prerequisite. Snapshots cannot detect change-and-restore.
The retained `hfProductionFingerprint` definition preserves W2's HF revision,
assets/tokenizer/runtime, pooling and dtype requirements. Ollama does not fill
those fields or satisfy that production identity. A migration needs new evidence
and a separately versioned contract, never fabricated HF values.

## Sampling and metrics

Protocol ID `bottom3-median-v1`: embed effective entry text and each legal clue.
Use the numeric policy in core-verification-api.md. For each target, choose the
five closest non-target entries by entry-vector dot product with that total
order as hard decoys. For each clue and sample s in 0..4, include those five,
then choose 14 from the rest by ascending SHA-256 of canonical restricted JSON
`["decoy-v1", semantic_hash, target_id, s, candidate_id]`, breaking hash collisions
by ASCII ID. Clue text does not affect sample selection; no replacement, target
excluded. All manifests have at least 40 entries. Rank target against these 19
decoys, one-based. Five samples may overlap. Take median across five samples per
clue, then median across the entry's legal clues (even median averages middle
two). Reachable means entry median ≤3. mean_rank averages entry medians;
reachability=reachable_entries/entry_count; playability=100*reachability.
duplicate_entry_count=0 for accepted inputs. Invalid duplicates fail hygiene.
Flag unreachable IDs and entry-vector pairs whose raw dot product ≥0.95 as
diagnostics only; pair IDs sort ascending, pairs sort lexicographically. Cap
each diagnostic list at 1,000, setting diagnostics_truncated if any are dropped.

Protocol hash is SHA-256 of restricted canonical encoding of parsed
`verification-policy.json`, independent of checkout line endings and prose edits.
Decimals in that policy are exact string parameters, not canonical JSON floats.
The policy is normative alongside this prose; contradictions require a versioned
correction before implementation.

### Versioned gameplay binding

`ruleset-verification.json` defines `arcade-verification-binding-v1`. Both
`experiment-arcade-v1` and its playable extension `experiment-arcade-paced-v1`
use the unchanged `bottom3-median-v1` policy and protocol hash. The paced rules
change spawn timing and multi-clear scoring, not clue legality, vector ranking
or the bottom-three diagnostic. Verification measures static target reachability;
it does not certify pacing, sweep balance, latency, or score equivalence.

`verify_pack` accepts either exact playable ID and recomputes a report bearing
that ID. Unknown IDs fail with `invalid_ruleset` before embedding. Report
ruleset_id must equal the calling game's pinned ruleset: a base report cannot
be relabeled or substituted for a paced report. Cache reports by manifest digest,
semantic hash, full model fingerprint hash, protocol hash and playable ruleset ID;
entry vectors may still be shared by vector hash and fingerprint hash. The
relationship version is registry provenance, not a new metric or report format.
Existing base reports, policy hashes and the frozen W3 reference remain unchanged.
Changes to this relationship require a new relationship version; changes to
measurement require a new policy ID/hash; scoring changes require a new playable
ruleset/configuration and a separate score cohort. Report hash fields must be recomputed, not trusted from upload.
Reject malformed input before embedding; infrastructure failures produce a
typed operation error, never a fabricated rejection metric report.

The existing ollama_eval runner is research evidence, not this verifier: it uses
authored hard decoys, fixture seed strings, generic controls, and separate
label/context modes. Its reports cannot be relabeled as these reports or reused
as publication/cache authority. Threshold calibration must test this protocol
and fingerprint; unrelated retrieval percentages do not establish a pass.
