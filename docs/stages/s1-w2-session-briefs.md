# Stage 1 / Wave 2 session briefs

Status: **prepared; dispatch requires W1 integration acceptance**.
All sessions start from the coordinator's recorded W1 integrated commit, not the
original planning commit or another worker's branch. See the
[W1 record](s1-w1-baseline.md) and [decision ledger](../decisions/0001-experiment-baseline.md).

## Shared instructions

Inputs are the handoff, project plan, decision ledger, installed W1 scaffold and
fixture guidance. Read the actual fake-ranker interface in the baseline; do not
invent a separate shared interface. It supplies test plumbing only. No session
may change root dependencies, `contracts/`, core package APIs or another session's
owned paths. Send required changes to the coordinator with a concrete reason.

Use branches `codex/s1-w2-b-model-evaluation`, `codex/s1-w2-c-gameplay` and
`codex/s1-w2-d-contracts`. Each gets its own worktree. Deliver small commits with
changed paths, reproducible check commands/results, remaining gaps and a W3 handoff.
Do not mark a session integrated or choose the next baseline yourself.

### Preliminary fixture conventions

These are experiment conventions, not a publication schema or frozen game protocol:

- Use UTF-8 JSON, stable string entry/case IDs and explicit fixture format versions.
  Keep human-readable labels distinct from IDs. Document ordering and rank direction.
- Semantic cases identify target ID, clue, candidate IDs, split (`calibration` or
  `held_out`), category and provenance. Entry records include ID, label and optional
  embedding text/forbidden clues. No uploaded vectors or claimed verified reports.
- Game traces identify a scenario, seed, initial state, ordered timestamped commands
  and expected full state/score after every event. Include fake ranking inputs so
  the trace is reproducible without a model.
- Manifest examples name their draft schema and expected outcome/error category.
  Invalid examples isolate a named failure where possible.
- Each session owns its fixture README and local validation recipe. Cross-fixture
  transformations are proposals for W3; parallel sessions do not import unmerged data.

## B — Semantic evidence and corpus feasibility

Owns `experiments/model_eval/`, `fixtures/semantic/`,
`docs/evidence/model-evaluation.md`, `docs/evidence/content-sources.md`.

1. Prepare 150–250 redistributable or authored entries covering concrete words,
   geography, ambiguous labels, multiword phrases and a difficult theme. Freeze
   calibration and at least 60 held-out target cases with multiple natural clues
   before tuning. Add hard decoys, illegal clues and intentionally weak packs.
2. Propose experiment dependencies to the coordinator before adding them. Evaluate
   BGE base English v1.5, GTE base and Nomic embed text v1.5 using reviewed model-card
   encoding modes and immutable revisions. Review any custom-code requirement
   before execution; do not silently enable remote code.
3. Measure top-3/median rank at multiple stack sizes, label/context effects,
   confusing neighbors, cold load, warm p50/p95, memory, asset size and verification
   throughput. Record environment, seeds, versions and exact commands. Keep model
   assets out of Git. Report unavailable runs instead of estimating results.
4. Inspect candidate frequency, concreteness and noun sources. Record source links,
   rights evidence, likely usable yield and clue-authoring/review effort for a
   later 3,000–5,000-entry corpus; do not build that corpus now.

Acceptance: reproducible evidence supports a recommendation, good/weak packs are
distinguishable, and category-specific failures remain visible. No recommendation
may imply that the target hardware or sub-100 ms game latency has already passed.
If model runs are blocked, deliver the harness and fixture with the evidence gate
explicitly open. Excludes production embeddings and shared contract changes.

W3 handoff: candidate comparison, encoding/pinning proposal, calibration findings,
data/source risks, reproducible result locations and missing evidence.

## C — Gameplay, fairness and interaction

Owns `docs/design/gameplay.md`, `docs/design/interaction.md`, `fixtures/game_traces/`.

1. Specify state transitions, clue legality, sort/tie direction, target choice,
   spawn order, capacity overflow, scoring, disconnect/reconnect and finite-pack
   exhaustion. Explicitly settle equal-time spawn/clue order and inference-time
   treatment in the draft. Treat plan tunables as proposals.
2. Distinguish casual adaptive spawns from seeded events with a precomputed finite
   word sequence and times independent of player actions. Show two players taking
   different actions under the same event schedule.
3. Supply deterministic traces for success/rejection, tie handling, overflow,
   exhaustion, equal timestamps, duplicate command IDs and stale/reconnect state.
   Expected states include board ordering, target, score, revision and end reason.
4. Specify keyboard-first interaction, long labels, pending/rejected input, visible
   target cues beyond color, re-sort/clear explanation, reduced motion and game over.
   Use compact visual tokens and ASCII layouts; assess whether vanilla browser
   code is adequate for W4 without implementing it.

Acceptance: two implementers can derive the same traces. Browser animation
completion never changes outcome. Fake rankings are explicit and no real semantic
quality is inferred. Excludes browser code and guessed model-threshold tuning.

W3 handoff: rules proposal, unresolved choices, trace coverage, interaction needs
and any conflict between gameplay rank direction and verification metrics.

## D — Pack, platform and creator contracts

Owns `docs/contracts-drafts/`, `docs/design/creator-kit.md`, `fixtures/manifests/`.

1. Draft machine-readable manifest and HTTP/event schemas, annotated SQLite records,
   errors, bounded verification/upload behavior and model fingerprint fields.
   Produce valid and invalid manifests, including the handoff's illustrative
   two-entry example as an incomplete publication pack.
2. Define canonicalization and separate full-manifest, semantic/test and vector
   content hashes. Self-reported reports/provenance must not alter decoy seeds;
   uploaded vectors cannot establish trusted embeddings.
3. Specify immutable version identity, idempotent retry versus content conflict,
   owner enforcement, admin bootstrap/reset and account/session protections.
   Separate fixed account/logging requirements from proposed registration policy,
   retention duration and creator visibility. Define private-log access/deletion.
4. Draft CLI command contracts and creator journey from initialization through
   local verification, packaging, upload rejection and repair. Outline the future
   skill; do not create a production CLI or finished skill.

Acceptance: validate examples against the draft schema with a reproducible command;
reject unknown vectors, unbounded inputs and owner/version conflicts explicitly.
Explain how reports and storage preserve verified versus self-reported distinctions.
Use provisional IDs/placeholders for the unselected model and unresolved game
rules; no fabricated fingerprint. Excludes migrations, auth/server implementation
and editing `contracts/` before W3 review.

W3 handoff: schemas/examples, storage/API proposal, hash and trust-boundary rationale,
owner-dependent policy decisions, and conflicts needing reconciliation with B/C.
