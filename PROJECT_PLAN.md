# Semaphore project plan

November 12, 2026 update: W5 was merged and pushed to `main` at `37c5090`.
Real-player feedback prompted a bounded correction: live play by default,
continuous countdown display, post-sweep/empty-board refill to five words,
and clearer clearing/falling motion. The pinned model is reachable; a live
browser smoke passed. Validation: 189 Python tests, seven JavaScript tests,
lint/format, mobile and reduced-motion checks. See the
[playtest session record](docs/evidence/w5-playtest.md#november-12-2026-playtest-correction-session).
Full human acceptance, real-model parity/load and contract/hardware gates remain
open. Earlier status paragraphs are historical.

November 11, 2026 update: W4 and the subsequent arcade refinements are merged in
`main` at `64e3a90`. The bounded Stage 1 W5 work is integrated locally after three isolated parallel
sessions using GPT-6.1 Sol at high reasoning effort, as requested by the owner. See the
[W5 record](docs/stages/s1-w5-acceptance.md) for scope and ownership. Stage 2 has
not been dispatched; human feel, real-model latency and release-hardware gates
remain open. The [Stage 1 report](docs/evidence/stage-1-report.md) recommends
bounded correction within Stage 1. Earlier status paragraphs below are historical.

November 9, 2026 update: direct LAN Ollama access and real query/entry embeddings
are verified. The owner authorized the next wave with parallel GPT-6.1 Sol agents
at medium effort. W3 model evidence and contract reconciliation started from
`fee011df94ce06afb5e207ac7017b436b6f9ea7c`; see the
[W3 record](docs/stages/s1-w3-contract-reconciliation.md). The historical status
below describes the preceding gate. Bounded experiment contracts and measurements
are now integrated. W3 is closed for the bounded W4 prototype following the
owner's explicit acceptance of that scope while retaining the unmet 100 ms
Stage 1 target. Actual-protocol synthetic measurements and Python/Node numeric
checks are retained; adaptive casual selection and general morphology are excluded
from the frozen experiment. See [decision 0004](docs/decisions/0004-w3-gate-closure.md).
W4 is ready but has not been dispatched. Historical status below is superseded.

Status: Stage 1 Wave 4 is integrated locally on `codex/s1-w4-integration`.
See [the W4 record](docs/stages/s1-w4-playable-experiment.md) for commits, validation
and remaining W5 acceptance gates. Later-stage gates remain in force.

Prepared: November 8, 2026.

Updated November 9, 2026: the owner selected `qwen3-embedding:4b` and LAN Ollama
on an NVIDIA GPU machine for development. The adapter, offline tests and selected
model evaluation runner are implemented without contacting that machine. This
supersedes the immediate three-model comparison/CPU development prerequisite;
earlier wave cards below remain historical planning. Quality, runtime identity,
thresholds and release hardware remain unvalidated. See
[decision 0002](docs/decisions/0002-lan-ollama-development.md) and
[runner commands](experiments/model_eval/README.md). W2's measurement gate stays open.

Source: [Semaphore — Handoff](Semaphore%20%E2%80%94%20Handoff.md), plus the owner's clarifications in this planning conversation.

## Product understanding

Semaphore is a shared room activity: someone publishes a themed vocabulary, people signal associations through clues, and the room competes on a common leaderboard. Its three connected products are the semantic arcade engine, the LAN hub, and the independent creator kit. The loop is **create → verify → publish → play → compete**, with feedback to creators added in v2.

The critical promise is that associations feel understandable while pressure builds. A technically correct cosine ranking can still make a bad game. The second promise is creator trust: a creator should be able to reproduce the hub's verification before uploading. The third is operational simplicity: one CPU server, thin browsers, and no runtime internet dependency or server-side LLM.

“Verified” means the hub recomputed the declared tests. It does not mean the test clues are independent, the pack is universally fun, or the provenance is authenticated. Keep those distinctions visible.

### Fixed scope and new decisions

- English, Arcade only; LAN-only Python server with server-side embeddings and authoritative game state.
- Versioned packs, per-version leaderboards, upload re-verification, creator skill plus CLI, no hosted generation.
- **Owner confirmed:** lightweight accounts, replacing the handoff's device-token suggestion and earlier exclusion of an accounts system. Interpret as local username/password accounts, without email, OAuth, or external identity services.
- **Owner confirmed:** target 6–8 concurrent players; CPU-only, 8 GB RAM is the initial benchmark envelope. Exact CPU and OS still need recording before measurements can establish a supported minimum.
- **Owner confirmed:** persist private clue logs for future pack feedback. Creator visibility is not authorized by that decision.
- Later-stage detail is deliberately deferred. This document schedules Stage 1 only. The owner's subsequent instruction authorized repository automation and first-wave implementation in parallel worktrees.

### Proposed decisions still open to adjustment

| Topic | Planning proposal | Decision point |
|---|---|---|
| Registration and publishing | Open local signup; every signed-in user can publish; only the pack owner can add versions | Stage 1 contract review |
| Admin | Initial admin created by an operator command; operator-controlled password reset; no web self-promotion | Stage 1 contract review |
| Private logs | Store accepted and rejected attempts with reason, target, outcome and pseudonymous session ID; 30-day default retention, configurable; no raw-clue API for creators in v1 | Stage 1 privacy contract; duration is a proposal |
| Identity in logs | Account association stays in the private session store; do not call pseudonymous logs anonymous | Stage 1 privacy contract |
| Seeded events | Admin-started events first; daily scheduling deferred | Stage 1 fairness contract |
| Leaderboards | Permanent histories, no ordinary reset; new pack versions and events create new boards | Stage 1 fairness contract |
| Offline creator installation | Ship an operator-prepared offline bundle containing CLI dependencies and the pinned model; hub-hosted downloads are optional | Stage 4 planning |
| Pack license | Required explicit license or rights statement; no automatic license grant/default; redistribution rights checked for bundled content | Stage 1 format contract |
| Development model | Owner selected Qwen3-Embedding 4B via LAN Ollama; calibrate and evaluate that model | Decision 0002; measurement gate remains open |

## How stages, waves and sessions work

**Stage:** a product outcome with evidence-based exit criteria. A stage can change scope based on evidence. Finishing its checklist without meeting its exit criteria does not complete it.

**Wave:** a dependency boundary inside a stage. Sessions within a wave start from one integrated baseline and can run concurrently. Advance only after their outputs are reviewed, integrated and verified. A one-session wave is appropriate for setup or integration.

**Session:** one bounded assignment to one agent in one branch/worktree, with declared inputs, owned paths, exclusions, outputs and acceptance evidence. A session is not an indefinitely running subsystem owner.

### Worktree and integration protocol

1. The planning baseline is committed as `ce05b9c`. W1 setup sessions start from that commit; later sessions start from their recorded integrated wave baseline.
2. A coordinator owns the integration branch, root dependency/lock files, migrations, shared contracts and the plan. Only the coordinator advances the wave baseline.
3. Use branch IDs such as `codex/s1-w2-b-model-evaluation`; create worktrees in an approved writable location. This workspace uses ignored `.worktrees/` directories because sibling directories are outside its writable scope.
4. Every session starts from the same recorded baseline commit for its wave. Dependencies must already be merged; a session must not import another running session's unmerged files.
5. Each session owns the paths listed below, including its own tests. Shared-interface changes go to the coordinator, who resolves and integrates them before dependent work resumes.
6. With four agent slots, use one coordinator plus at most three concurrent workers. Do not equate three sessions with a guaranteed threefold speedup.
7. Each session returns commit IDs, changed paths, checks and evidence, unresolved decisions, and a short handoff. Do not include model weights, secrets or raw participant clues in Git.
8. Coordinator reviews and merges sessions, runs cross-session checks, then records the next baseline. Integration failure keeps the wave open; later independent investigation may continue, but dependent sessions do not start.
9. Remove worktrees only after their commits are integrated and their working trees are clean. Failed experiments retain their evidence even when their code is discarded.

Session states: `ready → running → review → integrated`, with `blocked` recording a concrete dependency. Only integrated sessions count toward a completed wave.

## Stage map

| Stage | Outcome | Exit evidence / boundary |
|---|---|---|
| **1 — Prove the game and its contracts** | Small playable experiment, measured semantic model decision, reproducible verification and implementation-ready boundaries | Detailed below; no complete hub or full corpus |
| **2 — Build the durable playable foundation** | Local accounts, persistent pack versions, authoritative games, private clue capture and server-recorded results work as one product | A signed-in player finishes a real game and sees its durable score; ownership and restart behavior verified |
| **3 — Close the creator-to-hub loop** | CLI + skill, upload validation, publication, browsing, provenance and version history work end-to-end | An independent creator makes a themed pack; local and hub metrics agree; owner publishes a new version without altering old boards |
| **4 — Release LAN v1** | Several people can compete reliably offline with the default corpus, seeded events and moderation | 6–8 player acceptance run, offline installation/restart, packaged assets, admin hide/unhide, default 3,000–5,000-word pack and independent creator acceptance |
| **5 — Learn from play (v2)** | Per-word stats, privacy-reviewed feedback export, `packtool feedback`, batch re-verification | Creator revises a weak pack using feedback; model/metrics migration preserves audit history |
| **6 — Grow the community (v3)** | Likes, play counts, remix attribution and featured packs | Prioritize from observed use; no additional scope committed now |

Stages 2–6 intentionally have no waves, session assignments or calendar estimates yet. Stage 1 may reveal that corpus preparation or creator tooling should move earlier. Feature version and delivery stage are different: v1 spans Stages 1–4.

## Stage 1: prove the game and its contracts

### Objective and scope

Answer three questions before building the complete hub:

1. Does the association game feel understandable and enjoyable with real embeddings?
2. Can creator and hub verification produce equivalent decisions using one pinned implementation?
3. Can a small CPU server support the expected room without upload work ruining gameplay?

Build only enough code to answer those questions: a representative fixture, model benchmark, pure engine, thin browser experiment and integration harness. Account screens, production upload workflows, complete storage migrations, release packaging, the finished creator skill and the full default corpus are later work. Stage 1 nevertheless specifies their contracts so parallel implementation is possible.

### Wave dependency graph

```text
W1: A kickoff and baseline
              │
W2: B semantic/content evidence ─┬─ C game/fairness specification ─┬─ D platform/creator contracts
                                └───────────────────────────────┘
              │ all reviewed
W3: E freeze the experiment contracts
              │
W4: F shared core + engine ──────┬─ G browser experiment ─────────┬─ H independent parity/load probes
                               └───────────────────────────────┘
              │ all merged
W5: I integrate, playtest, decide and plan Stage 2
```

Wave 4 sessions consume Wave 3 contracts and fixtures, not each other's work in progress. G uses event fixtures; H builds probes against interfaces and a fake service. Real end-to-end evidence is collected in W5.

### Session cards

Estimates are focused worker-days, roughly 4–6 productive hours each, excluding model-download waits and arranging human playtests. They are planning ranges, not agent runtime promises.

#### W1 / S1-W1-A — Establish the experiment baseline

- **Owner:** coordinator. **Estimate:** 0.5–1 day.
- **Inputs:** handoff, this plan, owner answers.
- **Owns:** root Git/setup/configuration, dependency lock, `docs/decisions/`, `docs/stages/`, skeleton package metadata.
- **Work:** record confirmed versus provisional decisions; choose one supported Python/runtime baseline after compatibility checks; scaffold install/import and test commands; establish a fake ranker interface and fixture locations; record benchmark hardware or flag it unavailable.
- **Outputs:** integrated starting commit; decision log; session briefs; runnable minimal test entry point; benchmark data handling rules.
- **Acceptance:** a fresh worktree installs from the recorded dependency set and executes a smoke check; all W2 sessions have disjoint owned paths and sufficient inputs.
- **Excludes:** model selection, application features, finished root architecture.

#### W2 / S1-W2-B — Semantic evidence and corpus feasibility

- **Owner:** semantic/content agent. **Estimate:** 2–3 days.
- **Inputs:** W1 baseline, handoff candidates, preliminary fixture format.
- **Owns:** `experiments/model_eval/`, `fixtures/semantic/`, `docs/evidence/model-evaluation.md`, `docs/evidence/content-sources.md`.
- **Work:** assemble about 150–250 entries spanning general concrete words, geography, ambiguous labels, multiword phrases and a deliberately difficult theme. Separate calibration examples from at least 60 held-out target cases with multiple natural clues. Include hard decoys, forbidden-clue cases and weak packs. Benchmark the three candidates using documented encoding modes; do not tune on the held-out set.
- **Measure:** target top-3 rate and median rank at multiple stack sizes, confusing near-neighbors, label/context effects, warmed inference p50/p95, cold load, memory, asset size and verification throughput. Record CPU, OS, thread settings and package versions.
- **Content feasibility:** inspect candidate frequency/concreteness/noun sources and their redistribution terms; estimate how many words survive, how clues will be authored and reviewed, and whether 3,000–5,000 usable entries is realistic. Do not produce the full corpus.
- **Outputs:** reproducible benchmark commands, raw aggregate results, fixtures with provenance, recommended model/prefix policy and source-risk register.
- **Acceptance:** recommendation follows recorded quality/latency evidence; weak and good fixture packs separate meaningfully; no unsupported claim that 8 GB or sub-100 ms is already proven.
- **Excludes:** changes to shared contracts or production embedding code; download only what the experiment needs.

#### W2 / S1-W2-C — Gameplay, fairness and interaction specification

- **Owner:** game/design agent. **Estimate:** 1–2 days.
- **Inputs:** W1 baseline and handoff; use fake ranking while B is running.
- **Owns:** `docs/design/gameplay.md`, `docs/design/interaction.md`, `fixtures/game_traces/`.
- **Work:** specify state transitions, clue legality, target selection, ordering/ties, spawning, overflow, scoring, timer/queue order, disconnects and finite-pack behavior. Define casual versus seeded-event behavior explicitly. Produce fixture traces with expected state and score after every event.
- **Interaction:** sketch keyboard-first gameplay using real pack labels; specify pending/rejected clues, long entries, target visibility, re-sort/clear animation, reduced motion, reconnect and game-over. Include compact visual tokens and ASCII layouts.
- **Outputs:** state machine, fairness contract, initial tunables, event traces and visual direction.
- **Acceptance:** two implementers could derive identical traces; animated movement explains what changed; target status is not color-only; no game outcome depends on browser animation completion.
- **Excludes:** browser implementation and changing model thresholds based on guesses.

#### W2 / S1-W2-D — Pack, platform and creator contracts

- **Owner:** contracts/creator agent. **Estimate:** 1.5–2.5 days.
- **Inputs:** W1 baseline, account/logging decisions and handoff format.
- **Owns:** `docs/contracts-drafts/`, `docs/design/creator-kit.md`, `fixtures/manifests/`.
- **Work:** draft manifest JSON Schema and pass/fail examples, HTTP/event schemas, SQLite model, content hashing, model fingerprint, verification report format and error taxonomy. Specify account ownership, admin setup, private logs and retention. Draft the CLI command contracts and skill outline; no actual finished skill needed yet.
- **Outputs:** machine-readable draft schemas plus annotated storage/API proposal; valid and invalid manifests; creator journey from init to package to rejected-upload repair.
- **Acceptance:** packaged self-reported reports do not change decoy seeds; verification is bounded; unknown model vectors cannot be supplied; immutable version identity and owner enforcement are explicit; the example handoff manifest is recognized as illustrative rather than a complete passing pack.
- **Excludes:** migrations, account implementation, production CLI and upload server.

#### W3 / S1-W3-E — Reconcile evidence and freeze experiment interfaces

- **Owner:** coordinator. **Estimate:** 0.5–1 day.
- **Inputs:** integrated B/C/D outputs.
- **Owns:** `contracts/`, `docs/decisions/`, root dependencies and the approved API/storage/manifest references.
- **Work:** reconcile bottom-zone metrics with game rules, choose and pin the measured model, settle seeded fairness, set provisional thresholds from calibration data, and consolidate drafts. Promote shared fixtures; publish callable core interfaces and server event examples. Resolve owner-dependent decisions or explicitly block only affected work.
- **Outputs:** reviewed schema, model lock/fingerprint, game ruleset ID, verification protocol, API/event contract, SQLite draft and W4 baseline commit.
- **Acceptance:** no W4 worker needs to invent a public interface; no unresolved fairness or ranking policy remains hidden in implementation tickets. Contracts may evolve later through explicit versioned changes.
- **Failure path:** if no candidate gives promising quality/performance, run one bounded follow-up experiment or revise scope before proceeding. Do not freeze a failed assumption to keep the schedule.

#### W4 / S1-W4-F — Shared core and authoritative experiment engine

- **Owner:** core/game agent. **Estimate:** 2–3 days.
- **Inputs:** W3 contracts, selected model, semantic and game fixtures.
- **Owns:** `packages/semaphore_core/`, `experiments/game_server/`, `tests/core/`, `tests/game/`.
- **Work:** implement normalization, clue checks, embedding adapter, ranking, deterministic decoy sampling, verification metrics and pure game reducer. Add only the thin experimental server endpoints needed to play and exercise verification. Inject clock/RNG; separate HTTP from rules; use one in-memory model and bounded inference work.
- **Outputs:** real-ranker playable backend, core callable from a separate process, replayable traces and meaningful boundary tests.
- **Acceptance:** illegal clues, ties, overflow, repeated command IDs and simultaneous events follow fixtures; score is computed only by the server; protocol exposes state revisions; offline cached-model startup works.
- **Excludes:** complete authentication, production SQLite persistence, upload publication and hub pages.

#### W4 / S1-W4-G — Thin playable browser experiment

- **Owner:** frontend agent. **Estimate:** 1.5–2.5 days.
- **Inputs:** W3 event fixtures, API contract and interaction spec.
- **Owns:** `web/`, `tests/web/`.
- **Work:** build the stack, target, clue input, score, pending/error states and game-over/retry. Use a fixture transport first and the specified real transport later; bundle assets locally. Keep server revisions authoritative and ignore stale visual responses.
- **Outputs:** browser experiment, documented transport adapter and visual QA notes.
- **Acceptance:** keyboard-only play works; narrow viewports and long labels remain readable; reduced motion preserves game information; browser cannot supply a score or choose a favorable next word.
- **Excludes:** full hub navigation, account screens, upload screens and final visual polish.

#### W4 / S1-W4-H — Independent parity, robustness and load probes

- **Owner:** verification agent. **Estimate:** 1–2 days.
- **Inputs:** W3 interfaces and approved fixtures; a fake endpoint is sufficient for probe development.
- **Owns:** `experiments/acceptance/`, `tests/contracts/`, `docs/evidence/probe-method.md`.
- **Work:** create probes that invoke verification in two separate execution paths, replay fixtures, retry commands, send stale/out-of-order requests, reject oversized/invalid manifests and simulate 1/4/8 players with concurrent verification work. Independently review test-clue leakage and report trust boundaries.
- **Outputs:** runnable parity/load probes, expected contract outcomes and structured result format.
- **Acceptance:** probes expose failures rather than silently accepting fixture responses; queue time is measured separately from embedding time; no parity success is claimed before testing F's actual implementation in W5.
- **Excludes:** modifying F/G code or publishing load numbers from mocks.

#### W5 / S1-W5-I — Integrate, playtest and choose the next stage

- **Owner:** coordinator, with targeted fixes delegated back to the owning agent. **Estimate:** 1.5–2.5 days plus participant availability.
- **Inputs:** integrated F/G/H work and real model assets.
- **Owns:** integration changes, `docs/evidence/stage-1-report.md`, updated decisions and the next-stage plan.
- **Work:** connect the real browser and server; execute parity/replay/load probes on named hardware; repeat offline with network access removed; run several short sessions with at least three people where available. Observe whether players understand target selection, clue rejection, reordering and loss. Walk through the proposed creator journey with an independent agent; distinguish a walkthrough from the later real CLI acceptance.
- **Outputs:** recorded results, tuned defaults, remaining risks, reusable versus disposable prototype inventory, and detailed Stage 2 waves/sessions based on what was learned.
- **Acceptance:** all exit criteria below pass or a specific failed gate is reported. Human playtesting unavailable means the feel gate remains open; synthetic play does not substitute for it.
- **Excludes:** declaring v1 complete or silently starting Stage 2.

### Stage 1 estimates and exit gate

Total: approximately **12–19.5 worker-days**, with roughly **8–13 focused working days on the dependency path** before download delays, participant scheduling and substantial rework. Re-estimate at W3. These are rough scope estimates, not a delivery commitment.

Stage 1 is complete only when:

- A person can play a short browser game against real server-side embeddings, reach game over and see a server-computed score.
- The frozen fixtures replay deterministically; challenge scheduling is independent of player actions; score and state retries cannot double-apply.
- Separate local and server verification paths produce matching pass/fail and rank decisions on fixtures; numeric tolerance is documented and boundary disagreements are surfaced.
- Held-out clue results, human observations and confusing cases support continuing with the selected model. Propose at least 80% top-3 on the general fixture as a provisional screening target; do not conceal poor themed-pack performance in the average.
- End-to-end warmed clue latency is measured at 1/4/8 players, including background verification pressure. Target p95 ≤100 ms on the reference LAN hardware; a miss requires an explicit tuning/scope decision and another measurement, not a false pass.
- CPU/RAM behavior and a fully offline model/assets startup are recorded. Simulated 8-player load and actual human playtesting are labeled separately.
- Manifest schema, API/event definitions, storage draft, model pin, verification rules and account/logging decisions are sufficient to dispatch independent Stage 2 work.
- Default-corpus sources, licensing, clue-authoring cost and scale feasibility are understood well enough to plan that content work.
- A stage report states continue, revise or stop; only then is Stage 2 expanded into waves and sessions.

## Proposed technical shape

This is a planning layout; paths become real only when their stage needs them.

```text
contracts/                       manifest schema, event/API schemas, model lock
packages/semaphore_core/          normalization, legality, ranking, verification, pure game rules
apps/hub/                        FastAPI routes, auth, persistence, bounded jobs, assets
packages/packtool/                creator CLI using the same core
web/                             thin browser client; locally bundled static assets
skills/semaphore-pack-creator/    concise SKILL.md, schema/workflow references
content/                         source recipes and release pack manifests
fixtures/                        public/synthetic semantic, manifest and replay fixtures
tests/                           contract, core, game, API and browser tests
experiments/                     benchmark, prototype and acceptance harnesses
docs/                            decisions, evidence, stage plans and operating guide
```

Use one Python packaging/dependency strategy for core, hub and CLI; no microservices, Redis, vector database or separate inference server by default. A single application process owns the model. Use SQLite and disk assets for durable state; isolate expensive verification behind a bounded queue that gives game work priority. Prototype scheduling and contention before promising its latency.

Frontend proposal: a small TypeScript/Preact client compiled to static assets. Confirm the choice in W1; vanilla is acceptable if the interaction prototype stays simpler. WebSocket game events provide authoritative spawn/target updates; HTTP handles account, pack and upload operations; leaderboards poll every 3 seconds initially. Do not add WebSocket leaderboard infrastructure merely because games use it.

### Contract decisions Stage 1 must resolve

**Model fingerprint.** Pin repository and immutable revision, tokenizer/runtime versions, encoding instructions, normalization, precision, dimensions and truncation policy. Cache vectors by canonical entry content plus embedding fingerprint. Keep rules/metrics version separate so a scoring change does not necessarily require re-embedding.

**Hashes.** Define canonical encoding, normalized strings, key ordering and order-sensitive entry IDs. A semantic/test hash includes entry data and test clues but excludes `test_report`, display metadata and provenance. An entry-vector hash excludes test clues too. Package reports must not change their own decoy sampling seed. Store the immutable full manifest digest separately for audit/version conflict checks.

**Verification.** Only legal test clues count. Every entry must have sufficient clues. For each clue, evaluate against 19 seeded decoys, across five fixed samples where pack size permits; include a reproducible hard-decoy component. Define typical rank as median across samples, then median across an entry's clues. Reachable means rank ≤ bottom-zone size. Start with playability = 100 × reachable fraction and show mean rank separately; avoid unexplained composite weights. Validate the sampling scheme against actual gameplay in Stage 1.

**Numeric equivalence.** Start with cosine comparison tolerance 1e-5 for measured parity, plus a specified deterministic near-tie policy and stable entry-ID fallback. Confirm on supported runtimes; do not claim universal bitwise identity. Pack pass/fail disagreements near a threshold must be reported and resolved.

**Game rules.** Proposed first experiment clears only the highlighted target when it lands in the bottom zone. Multi-clear bonus is disabled pending playtesting; the handoff exposes a tunable but does not settle which non-target words clear. New targets are chosen deterministically from the surviving board. Clue rejection spends elapsed time but changes neither board nor score. Server timestamps and command IDs determine ordering; the browser cannot pause time. Specify spawn-before-clue behavior at an equal timestamp and whether inference time advances the clock consistently for all players.

**Seeded fairness.** A seed alone is insufficient when filters or target choices depend on player actions. Casual play may use adaptive target-near decoys. Event mode uses a precomputed, finite, non-repeating spawn sequence and schedule, with challenge duration capped to available entries. Difficulty comes from the scheduled semantic groups, not filters against each player's current board. Boards and selected targets may diverge through play; scheduled words and times do not. Pin pack content, model, ruleset and schedule in the challenge. Test this distinction in W2/W3 before implementation.

**Competition identity.** Expose one board per pack version and one per seeded event. Preserve pack-version history; scores also record model/ruleset identity. Once real competition begins, hold model and rules fixed for v1. Later migrations must explicitly separate comparable score cohorts rather than silently mix incompatible results.

### Initial experiment tunables

All numbers below are starting proposals, not validated product requirements.

| Parameter | Starting value / rule |
|---|---|
| Initial words / stack capacity / clear zone | 6 / 12 / bottom 3 |
| Level advancement | Every 5 target clears |
| Spawn interval | `max(2.0, 5.0 * 0.9^(level-1))` seconds |
| Clear score | 100 points; no time or multi-clear bonus initially |
| Casual diversity ceiling | 0.65 cosine; calibrate by model |
| Later-level decoys | Try similarity 0.45–0.70; maximum one intended close decoy per spawn decision |
| Spawn retry/fallback | At most 32 candidates, then deterministic least-similar eligible entry; never hang when a small themed pack exhausts options |
| Near-duplicate flag | 0.80 cosine initially; calibrate, do not treat as model-independent |
| Excess duplicate rejection | Initially >5% of entries involved in flagged pairs; report actual pairs |
| Publication threshold | Reachability ≥85%, after required schema/hygiene/clue checks; calibrate against held-out play |
| Manifest limit | 8 MiB UTF-8 JSON; 40–5,000 entries; no uploaded vectors |
| Entry / embedding text | 64 / 256 Unicode code points, with separate UI width testing |
| Test clues | 3–5 unique legal clues per entry, each ≤120 code points |
| Aliases / forbidden clues | At most 8 / 16 per entry, each ≤64 code points |
| Live clue | ≤120 code points; one in-flight request per game; bounded account and server rate limits |

Normalization must define Unicode normalization, case folding, punctuation, whitespace, alias matching and inflection/stem rules. Test false positives such as a target appearing inside an unrelated word; decide token/phrase containment explicitly rather than accidentally using naive substring matching.

### API and storage outline to formalize in S1-W2-D

These route names and records are proposed boundaries, not a finished production spec. W3 must provide request/response schemas, auth requirements, error responses and examples before implementation expands.

| Boundary | Proposed surface |
|---|---|
| Accounts | `POST /api/auth/register`, `/login`, `/logout`; `GET /api/me`; password hashing, server-managed sessions, CSRF/origin protections and operator reset policy |
| Discovery | `GET /api/packs?query=&tag=`; `GET /api/packs/{id}/versions/{version}` |
| Publication | `POST /api/uploads` → bounded job ID; `GET /api/uploads/{id}` → pending/rejected/published + verified report; owner-scoped, idempotent publication |
| Games | `POST /api/games`; `GET /api/games/{id}`; WebSocket `/api/games/{id}/events` with revision, command ID, timestamps and state/rejection/game-over events |
| Competition | `GET /api/packs/{id}/versions/{version}/leaderboard`; event board filter; admin event creation |
| Moderation | Admin hide/unhide pack operations; hidden packs cannot start new games; existing games finish under their pinned version |
| Optional creator scoring | Defer unless offline model distribution proves burdensome; never an implicit LLM service |

Storage proposal:

- `users`, `auth_sessions`: unique normalized login names, display names, password hashes, role, expiring hashed session tokens. Avoid putting credentials in application logs.
- `packs`: stable ID, owner, visibility and default-pack designation.
- `pack_versions`: unique `(pack_id, version)`, immutable manifest digest/path, semantic hash, metadata and publication state.
- `entries`: stable IDs within a version; display/embed text, aliases, forbidden clues, tiers.
- `verification_runs`: pack version, full embedding fingerprint, metrics version, fixture seed, status, verified metrics and diagnostics; self-reported data stays separate.
- `challenges`: immutable pack/model/ruleset/configuration, seed and spawn schedule identity.
- `games`: user, pinned version/challenge, seed, timestamps, status and final server score. Active state can remain in memory in v1; a restart marks unfinished games interrupted, never completed scores.
- `scores`: one finalized result per game, transactionally recorded once; indexes for version/event ordering, with a deterministic tie policy.
- `clue_attempts`: private game/target linkage, timestamps, clue, legal/rejected status, rank and clear outcome; retention cleanup. Never bundle these rows into public exports by default.
- `upload_jobs`: owner, bounded job state, manifest location and failure report; restart recovery and atomic publication semantics.

At publication, the manifest, entries and verification result become visible atomically. Same owner/id/version plus identical digest is an idempotent retry; differing content conflicts and requires a new version. Persist clue events and final results with stable IDs to prevent retries from duplicating records.

## Risks that can change the roadmap

| Risk | Early evidence / response |
|---|---|
| Good retrieval model, poor association game | Held-out natural clues and human playtests; change model or game rules before building the full hub |
| Verification can be optimized for authored clues | Label its scope honestly; use independent internal evaluation; v2 real-play feedback supplements it |
| Thousands of entries make validation expensive | Measure 5,000-entry vector comparison and 15,000–25,000 clue embeddings; bounded batches, cached vectors and game-priority queue |
| Default content is a large editorial project | Source/rights and yield probe in Stage 1; explicitly schedule corpus work in a later stage |
| `embed_text` makes associations surprising | Benchmark contextual labels; preserve creator context visibly on pack details; inspect extreme mismatch cases |
| Private clue logs become sensitive | Collect only required fields, disclose retention, restrict access and test deletion; creator exports require a separate design |
| Lightweight accounts expand scope | Local auth only; reuse maintained password/session primitives; no social features or external identity dependency |
| Parallel sessions drift | Frozen wave interfaces, disjoint ownership, integrated baseline commits and explicit contract changes |
| Prototype is mistaken for production | Stage report lists retained modules, shortcuts and required replacements; experimental server has no release claim |
| Model/rule changes invalidate comparisons | Pin each session/event/result and preserve verification history; plan migration before changing production behavior |

## Rolling planning rule

At each stage end, write a short report containing observed product behavior, measurements, owner decisions, unresolved risks and scope changes. Revisit later-stage outcomes, then expand **only the immediately next stage** into waves and session cards using the current repository layout and actual dependencies. A blocked gate triggers a bounded correction wave in the current stage, not speculative detailed planning of the rest of the project.

## Reference notes

The handoff is the product authority except where the owner has superseded it. Model cards inform benchmark setup, not a claim about gameplay performance:

- [BGE base English v1.5 model card](https://huggingface.co/BAAI/bge-base-en-v1.5) — initial benchmark baseline.
- [GTE base model card](https://huggingface.co/thenlper/gte-base) — alternative candidate.
- [Nomic embed text v1.5 model card](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5) — alternative; its documented examples include custom-code loading, which must be reviewed and pinned if selected.

Planning applied the local frontend-design skill to interaction/layout quality and the system skill-creator guidance to a small, self-contained creator skill with deterministic CLI support. No plugin, model, implementation dependency or skill was installed by this planning task.
