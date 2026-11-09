# Creator kit contract proposal

Status: W2-D design; no CLI or finished agent skill is implemented. The creator
uses their own agent locally. The hub offers no generation service and receives
one bounded JSON manifest, never uploaded embeddings or executable code.

## Commands and stable behavior

Every command supports `--json` for one machine-readable result, diagnostic codes
and JSON paths; human output is the default. Exit status: 0 success, 2 invalid
input/usage, 3 verification rejection, 4 missing model/runtime/I/O failure. Stdout
is result data; stderr is progress. Commands never overwrite a file unless an
explicit output path or in-place flag requests it. Model fetching is a separate,
explicit setup action; ordinary offline commands fail clearly if assets are absent.

| Command | Input → output / constraints |
| --- | --- |
| `packtool init --id ID --license TEXT --output PATH` | Scaffold draft manifest with explicit rights, empty entries/tests and current spec; clearly not publication-valid yet |
| `packtool validate PATH [--semantic] [--model-lock LOCK]` | Default: parse/schema/hygiene/coverage/legality only, no model. Semantic mode adds pinned-model near-duplicate checks; reports threshold/version identity |
| `packtool playtest PATH --model-lock LOCK --report-out REPORT` | Full deterministic shared verifier; reports semantic/vector/full digests, fingerprint/protocol and metrics; never claims hub authority |
| `packtool report REPORT [--json]` | Explain diagnostic entries, typical ranks and remediation; distinguish reported metrics from missing measurements |
| `packtool package PATH --report REPORT --output ARTIFACT` | Revalidate; require report semantic hash/fingerprint compatible with input and selected protocol; populate self-report/provenance, emit stable UTF-8 JSON with newline and exact-byte digest |

Local reports use an explicit `local-recomputed` authority outside the upload
manifest; the schema's hub report authority cannot be forged by attaching one.
Packaging extracts only the allowed self-report fields. Reports do not feed their
own decoy seeds. Repackaging metadata changes the full digest, so after publication
it requires a new pack version even if semantic metrics would stay the same.

`feedback` is v2 and absent from the v1 command surface. A hub scoring endpoint is
deferred, so offline local verification remains the defined path. Upload is through
the hub UI/API; a future CLI upload command must handle credentials privately and
is not needed for the initial kit. `--json` must not dump credentials or raw private
feedback. A license value is a creator statement, not automatic rights clearance.

## Creator journey and recovery

1. Install an operator-prepared dependency/model bundle or explicitly download
   pinned assets during setup. Check model-lock asset digests and runtime versions.
   Offline packaging and playtesting must never silently fetch assets.
2. Initialize with a meaningful pack ID and explicit license/rights statement.
   Write 40+ distinct entries with stable IDs, ordinary display labels and useful
   embedding context. Add 3–5 varied natural legal clues to every entry. Separate
   authored test clues from independent held-out evaluation; do not present the
   former as evidence of all player behavior.
3. Run validation. Repair each path-specific shape, duplicate, coverage or legality
   issue. Do not strip inconvenient tests until a pack appears to pass.
4. Run full playtest using the frozen model/protocol. Inspect weak words and hard
   neighbors, revise labels/context/clues, then repeat. A technically passing pack
   still needs human playtesting. Preserve old reports so changes are explainable.
5. Package once and retain the exact bytes. Sign in to the LAN hub and upload with
   an idempotency key. The hub enqueues its own verification; a 202 is not published.
6. Poll the owner's job. For rejection, inspect recomputed diagnostics, compare
   model/protocol fingerprints and semantic hash, then fix content. Same unpublished
   failed version can be retried according to reservation policy; published content
   requires a new version. For queue full, honor Retry-After; for transport loss,
   retry exact bytes/key, never create blind duplicate jobs.
7. On publication, review Verified and Self-reported sections separately. If the
   creator's report differs, explain model/runtime/protocol/content differences;
   never overwrite the hub result with supplied numbers. Later versions retain
   older boards and immutable content.

## Future skill outline

The eventual small `SKILL.md` should trigger on making/improving Semaphore packs,
not every word-game discussion. It should teach the loop above and call the CLI.
Keep command procedures in the main skill, schema/limits and diagnostic examples
in versioned references, and deterministic work in the CLI/shared library.

Required guidance: common concrete distinct entries; restrained context; aliases
and forbidden clues; varied legal tests; explainable associations; explicit rights
and provenance; self-report versus hub verification; exact-byte retry/version rules;
offline model setup and actionable missing-asset errors. Instruct agents to inspect
report diagnostics, not invent successful runs. No network credentials in examples,
no participant clues, and no claim that a pack is fun merely because it passes.

Distribution remains Stage 4 work. Proposed offline bundle contains pinned Python
dependencies, CLI wheel, model assets/lock, licenses and integrity manifest. The
hub need not host these downloads in v1. A real independent creator acceptance
must be performed later; this document is only a walkthrough contract.
