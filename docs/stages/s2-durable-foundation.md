# Stage 2 — Durable playable foundation

Planned November 16, 2026 (Asia/Shanghai).
Status: W1-A integrated locally on November 16; executable boundaries frozen at
`92aaffb0594ea329489b3df1eeea6336312edda3`. W2 is complete under the owner's
explicit bounded-work instruction; named Stage 1 carryovers remain open in the
[W2 dispatch record](s2-w2-foundations.md).
Planning snapshot: `67334c2c7fbc1b2840ff06f7141087f9a450490d`.
This is an inspection baseline, not a dispatch commit. Each wave records its own
reviewed, committed baseline before workers start.

## Outcome and scope

A local player signs in, selects an installed immutable pack version, finishes a
real authoritative game, and sees its server-recorded result after a server restart.
Other accounts cannot operate that game or claim its pack. Private clue capture,
retention, deletion and recovery satisfy the adopted durable contracts.

Include local accounts, operator bootstrap/reset, a bounded operator installation
path for trusted packs, persistent versions and game pins, authenticated HTTP games,
private attempts, durable terminal results, exact-cohort boards and the browser flow.
Reuse the pure engine, shared verifier, model adapter and proven browser behavior.

Defer creator upload/publication jobs, the finished CLI/skill, broad discovery and
version-history UX to Stage 3. Defer event administration, moderation, the full
3,000–5,000-word corpus and release packaging to Stage 4. Persist the adopted cohort
fields now; Stage 2 acceptance uses casual play. Do not introduce WebSockets,
portable model identities, new game rules or a replacement embedding model here.

## Decisions and entry gates

Owner confirmed in this planning conversation:

- Open local signup; an operator can disable it. Existing accounts can still sign in.
- HTTP within the LAN only. HTTPS is not a Stage 2 prerequisite. Passwords and session
  traffic are unencrypted on this deployment; describe that accurately in operator
  setup. Do not expose the service to the public internet or advertise transport security.

These supplement local username/password accounts and private clue capture already
confirmed in the project plan. W1 records them in an account ADR and executable
contracts. Other numeric policies in the W2 platform draft remain proposals until
W1 freezes them; suggested starting points are its login normalization, password
bounds, operator reset, 24-hour absolute/8-hour idle sessions and bounded rate limits.
Cookies on this HTTP deployment cannot require Secure; preserve HttpOnly,
SameSite=Strict, exact Origin/Host checks and session-bound CSRF for mutations.
Specify login/signup Origin protection and CSRF issuance/renewal explicitly.

Adopted authority: [decision 0005](../decisions/0005-durable-game-contract.md),
[storage](../../contracts/storage.md), [durable games](../../contracts/durable-game.md)
and [ruleset binding](../../contracts/ruleset-verification.json). Conflicting W2
WebSocket/storage/privacy proposals are historical. Current `contracts/openapi.json`
still describes the experiment and must not be mistaken for a durable API.

Stage 1 remains open. Its [report](../evidence/stage-1-report.md) and
[latest recorded performance refinement](../evidence/feasibility-refinement-2026-11-14.md)
do not establish the 100 ms target, full human acceptance or remote-host offline
readiness. Planning is authorized now; W1 contract preparation may proceed when
scheduled. W2 implementation requires either evidence closing the Stage 1 gate or
an explicit owner decision allowing bounded Stage 2 work with named carryovers.
That decision must retain every unmet target and its follow-up; this plan is not
such a waiver. Account/transport choices above do not waive other gates.

| Item to settle before dependent implementation | W1 output |
| --- | --- |
| Stage 1 carryovers | Current evidence audit and proceed/revise disposition; preserve latency, human, offline/resource and content-review gaps without repeating superseded findings |
| Account boundary | Adopt signup/HTTP choices; freeze normalization, hashing measurement, expiry/reset/revocation, rate limits, CSRF, Origin/Host and operator access |
| Durable API | Separate durable OpenAPI/schema fixtures for accounts, installed packs, games, receipts, private history and boards; preserve `/experiment/v1` |
| Persistent interfaces | Schema/migration ledger, transactions, repository protocols, auth principal and service composition; no session invents its own database model |
| Trusted installed content | Define operator installation ownership, rights checks, verification/budget and explicit acceptance; a measured experiment artifact is not automatically published |
| Casual board identity | Bind randomized initial board and schedule/seed to config identity; different artifacts have different boards under the adopted contract |
| Bounded runtime | Freeze game/command limits, inference admission/deadlines, rejection capture boundary, HMAC key lifecycle, cleanup and recovery hooks |

Random casual rounds may yield boards with only one result. Use a deliberately
reused accepted artifact to test multi-player rankings; do not silently merge
randomized cohorts. Changing that product behavior requires a separate decision.

## Wave map

| Wave | Sessions | Exit boundary |
| --- | --- | --- |
| W1 — Freeze implementation boundaries | A coordinator: contracts, decisions, schema and runnable service skeleton | Durable fixtures and repository interfaces executable; Stage 1 dispatch disposition recorded |
| W2 — Build independent foundations | B accounts; C installed packs; D browser against frozen fixtures | All three reviewed and integrated; real auth/pack paths and fixture-driven client pass |
| W3 — Connect durable play and prove persistence | E durable game service; F privacy/recovery operations; G independent acceptance harness | Integrated real service, retention/recovery and independent fault probes pass |
| W4 — Product acceptance | H coordinator: wire client, run real end-to-end acceptance and gate review | Signed-in real game, durable result, ownership, restart and deletion evidence; Stage 2 decision |

W1 → (B || C || D) → integration → (E || F || G) → integration → W4.
F and G use W1 protocols and frozen fixtures, not E's unmerged implementation.
Any newly discovered shared-interface change returns to the coordinator; integrate
it and issue a new common baseline before resuming affected sessions.

## Session and worktree rules

Use one coordinator plus at most three workers. Sessions in a wave start from the
same full commit SHA in isolated ignored `.worktrees/` directories. Branches use
`codex/s2-wN-letter-topic`; coordinator uses `codex/s2-wN-integration`. Do not create
worktrees or launch workers merely by accepting this plan. Model/effort selection
is a dispatch choice, not inherited from historical Stage 1 runs.

Coordinator exclusively owns `PROJECT_PLAN.md`, this record, `contracts/`,
`docs/decisions/`, root dependency/lock/build/CI files, shared package exports,
`packages/semaphore_hub/migrations/`, `packages/semaphore_hub/storage/`,
`packages/semaphore_hub/interfaces.py` and application composition/entry points.
The `semaphore_hub` shared package is installed and verified by W1. Domain
implementation directories below remain W2/W3 work. W1 helpers drafted disjoint
coordinator-owned files in isolated worktrees; the coordinator reviewed/integrated
them before freezing this boundary. No W2 worker ownership was delegated early.
Core engine/model changes and schema copies are coordinator-owned integration work.
Workers request shared changes rather than editing those files concurrently.

Each brief includes inputs, owned paths, exclusions, output contract and acceptance.
Each worker returns commits, changed paths, commands/results, evidence location,
remaining decisions and a short handoff. No participant clues, credentials, model
weights or private databases enter Git. Session states are
`blocked → ready → running → review → integrated`; only integrated work closes a
wave. Remove worktrees only after integration and a clean working-tree check.

## Session cards

### S2-W1-A — Contracts and integration skeleton

- Owner: coordinator. Branch: `codex/s2-w1-a-contracts`.
- Inputs: planning snapshot, adopted durable contracts, current experiment code,
  owner account/HTTP decisions, Stage 1 gate evidence.
- Owns: coordinator paths above, `fixtures/durable/`, `tests/hub/contracts/` and
  `docs/stages/s2-w1-session-briefs.md`.
- Work: audit current Stage 1 evidence; record dispatch disposition; publish account
  ADR and durable HTTP schemas/examples, including errors and uncertain create.
  Freeze SQLite migrations, storage protocols/transaction ownership, auth principal,
  clocks, inference boundary, recovery/deletion hooks and trusted install workflow.
  Provide installable package skeleton, fake adapters and schema-valid fixtures.
  Specify recovery runs before traffic and operations cannot bypass the live game lock.
- Outputs: executable shared baseline and detailed W2/W3 briefs with exact file
  ownership. Plan empty-database and supported upgrade behavior; keep migrations
  coordinator-owned throughout.
- Acceptance: fresh worktree installs using locked dependencies; schema fixtures
  validate; migrations establish constraints/FKs; fake repository/service smoke
  demonstrates each interface. No unresolved shared boundary is delegated.
- Excludes: production auth/game implementation, Stage 1 completion by declaration,
  changes to score eligibility or the 100 ms target.

### S2-W2-B — Local accounts and session security

- Inputs: integrated W1 schema, principal/repository interfaces and account fixtures.
- Owns: `packages/semaphore_hub/auth/`, `tests/hub/auth/`,
  `docs/evidence/s2-w2-accounts.md`.
- Work: signup/disable switch, login/logout, password hashing, opaque session tokens,
  expiry/rotation/revocation, CSRF/Origin checks and bounded login throttling.
  Supply operator bootstrap/reset handlers for coordinator CLI composition.
- Outputs: account routes/services and documented Argon2id parameter measurements
  on the selected host; no homemade password hashing.
- Acceptance: case-collision signup, disabled registration, wrong-password responses,
  logout/expiry/reset revocation, cookie/Origin/CSRF rejection and public/private
  identity separation. Bound both counters and expensive password verification work.
- Excludes: migrations, game authorization implementation, client UI and account
  erasure orchestration (F consumes B's revoke/delete primitives).

### S2-W2-C — Immutable installed packs

- Inputs: W1 repository/installer contracts and existing manifest/hash/verifier APIs.
- Owns: `packages/semaphore_hub/packs/`, `tests/hub/packs/`,
  `docs/evidence/s2-w2-packs.md`.
- Work: bounded operator installer and installed-version reads; use declared account
  ownership, exact bytes, trusted report and model/config pins. Verify outside short
  transactions; stage assets atomically and expose only accepted published versions.
- Outputs: installer service/handlers, bounded rights-cleared acceptance fixture and
  manifest/report/artifact provenance for W4. No synthetic public competition.
- Acceptance: concurrent namespace reservation, owner-before-digest checks, exact
  retry versus byte conflict, immutable versions, interrupted installation, orphan
  recovery and invalid/missing model/report rejection. A verification measurement
  alone never marks an experiment pack publishable.
- Excludes: creator upload API/jobs, full corpus, migrations, broad discovery UI.

### S2-W2-D — Signed-in browser flow against fixtures

- Inputs: frozen durable HTTP fixtures and current browser/reconnect behavior.
- Owns: `web/`, `tests/web/`, `docs/evidence/s2-w2-browser.md`.
- Work: signup/login/logout, installed-pack selection, private-capture disclosure,
  authoritative game/receipt transport, terminal result/history and exact board view.
  Show session expiry and interruption; preserve command IDs on uncertain responses.
  Do not automatically retry uncertain game creation.
- Outputs: browser flow tested against contract fixtures, ready for W4 real wiring.
- Acceptance: pending/rejected states, reconnect without rewind/double animation,
  expired session, interrupted game with no competitive result, empty board/history,
  keyboard/mobile/reduced-motion behavior and escaped public names.
- Excludes: backend endpoints, live credentials in fixtures, final real-service or
  human acceptance claims. Route/transport changes go through the coordinator.

### S2-W3-E — Authenticated durable games and results

- Inputs: integrated W2 accounts/packs, shared transaction API, durable game contract,
  existing pure reducer and bounded inference adapter.
- Owns: `packages/semaphore_hub/games/`, `packages/semaphore_hub/results/`,
  `tests/hub/games/`, `tests/hub/results/`, `docs/evidence/s2-w3-games.md`.
- Work: authenticated HTTP snapshots/commands/receipts/quit, admission persistence,
  private attempt/outcome writes, HMAC equality, once-only completion, transactional
  finalization, private history and cohort-filtered boards. Export frozen lifecycle
  hooks for F and application startup; only server pins/scores are authoritative.
- Outputs: durable game/result service and handlers. Coordinate shared entry-point
  integration without editing F's operations or coordinator migrations.
- Acceptance: cross-account 404, duplicate/changed retries, late completions,
  quit/finish races, zero-score natural endings, interrupted no-score endings,
  no success before commit, unique score rows, exact cohort/tie pagination and
  score/receipt persistence after restart.
- Excludes: browser changes, schema redesign, publication jobs, privacy maintenance CLI.

### S2-W3-F — Retention, recovery and operator maintenance

- Inputs: W1 storage/lifecycle contracts and W2 account/pack primitives. Use fake
  lifecycle adapters until E is integrated.
- Owns: `packages/semaphore_hub/operations/`, `tests/hub/operations/`,
  `docs/operations/durable-hub.md`, `docs/evidence/s2-w3-operations.md`.
- Work: startup interruption orchestration, at-least-daily cleanup plus read-time
  expiry, clue-only deletion, account erasure/anonymization, deletion ledger,
  encrypted backup rotation and pre-traffic restore cleanup. Expose operator
  handlers; coordinator composes startup and CLI. Preserve HMAC keys outside DB
  and key versions through receipt expiry; specify missing-key failure behavior.
- Acceptance: 30-day raw expiry, 90-day post-terminal receipt expiry, clue deletion
  preserving exact retry, account deletion revoking retries, deleted-owner tombstones,
  backup expiry within 30 days and restore applying deletions before serving traffic.
  Verify recovery settles pending receipts, creates no score and cannot race new play.
- Excludes: raw-clue web/admin API, creator feedback, changes to adopted retention.

### S2-W3-G — Independent durability and boundary probes

- Inputs: frozen contracts/fixtures and integrated W2; never import E/F working trees.
- Owns: `experiments/durable_acceptance/`, `tests/hub/acceptance/`,
  `docs/evidence/s2-w3-independent-probes.md`.
- Work: contract-driven probe harness with subprocess crash injection around admission,
  completion and terminal commits; restart, ownership, retry/deletion, cohort, privacy
  leakage and backup-restore cases. Add real-model load instrumentation for W4.
- Outputs: fake-service harness self-checks and reproducible commands targeting the
  integrated service. Distinguish fixture results from implementation evidence.
- Acceptance: probes detect duplicate score, foreign-account access, altered retry,
  wrong cohort and deleted-data resurrection faults. After E/F integration the
  coordinator runs them against real SQLite/service processes before W3 closes.
- Excludes: implementing E/F behavior or recording synthetic timing as real-model evidence.

### S2-W4-H — Integrate, exercise and decide

- Owner: coordinator. Inputs: fully integrated W3 and browser fixture-tested in W2.
- Owns: final shared wiring/client integration fixes, `docs/evidence/stage-2-report.md`
  and this plan's wave ledger. No concurrent workers editing those paths.
- Work: wire the browser to real accounts/packs/games/results; execute fresh-install,
  upgrade, recovery/deletion and operator runbook checks. Run the full regression suite
  and actual browser flows. Collect signed-in human real-model acceptance, then
  controlled 1/4/8-player load with real verifier overlap and resource measurements.
  Schedule model pressure probes separately from other model consumers.
- Outputs: evidence with exact commit, host/model/config identity, sample/error counts,
  p50/p95, restart outcomes, privacy checks and unresolved gates. Record proceed/revise
  disposition and only then plan Stage 3 dispatch.
- Excludes: weakening performance targets, declaring automated play a human test,
  full creator-loop or release acceptance.

## Stage 2 exit evidence

1. A signed-in person completes a real-model browser game on an explicitly accepted
   immutable version, sees its authoritative result, and retrieves it after restart.
2. Two accounts cannot access each other's private games/receipts/history or claim
   each other's namespace; rejected auth/CSRF/Origin operations have no side effects.
3. Crash/retry/quit races yield one natural score or an interrupted game without a
   competitive score. Terminal snapshots persist, active games do not silently resume.
4. Same-cohort results order deterministically; other versions/models/configs/random
   artifacts stay separate. No practice/test results enter public competition.
5. Raw clue expiry, clue-only deletion, account anonymization, backup rotation and
   restore cleanup pass with no participant content leaking to public responses/logs.
6. Fresh install and supported migrations work from locked dependencies. Existing
   engine replay, verification parity and browser regression checks stay green.
7. Real 1/4/8-player measurements and human observations are reported separately
   from synthetic checks. Any unmet inherited gate remains explicitly open unless
   the owner changes its disposition; durability alone does not prove LAN v1 readiness.

Use repository lint/format/Python tests, all relevant Node browser tests and package
build as integration checks; W1 adds hub-specific commands to its runnable briefs.
A planning-only edit requires link/consistency and diff checks, not runtime tests.

## Dispatch ledger

| Wave | Baseline SHA | State | Handoff |
| --- | --- | --- | --- |
| W1 | `92aaffb0594ea329489b3df1eeea6336312edda3` | Integrated locally | [Evidence and contract baseline](s2-w1-foundation.md); [worker briefs](s2-w1-session-briefs.md) |
| W2 | `8ac07292ed469be28f755edd28dd4e711ed79c75` | Complete; Stage 1/W4 gates retained | [Owner authorization, parallel dispatch and retained carryovers](s2-w2-foundations.md) |
| W3 | `2a00a4334227274abfdf29ea9eb86c3571b95057` | Complete locally; W4 gates retained | [Parallel dispatch and handoff](s2-w3-durability.md) |
| W4 | `871184892bfa6e4f9a007060394463a797b0097e` | Revise: human/restart pass; real load target failed | [Dispatch and retained gates](s2-w4-acceptance.md) |
