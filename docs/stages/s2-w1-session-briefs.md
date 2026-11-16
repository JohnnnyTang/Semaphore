# Stage 2 — Implementation dispatch briefs

Prepared during W1 on November 16, 2026. **W2/W3 are not dispatched.**
The coordinator records a full integrated baseline SHA in the W1 record after
review. Every worker in a wave uses that same commit in an isolated `.worktrees/`
checkout and its own locked environment. At most three workers run concurrently.
No worker begins from another worker's unmerged tree.

## Shared execution contract

Read `contracts/storage.md`, `contracts/durable-game.md`, the W1 account ADR,
`contracts/hub-runtime.md`, `contracts/repositories.md`, durable OpenAPI/schema and
`fixtures/durable/`. Existing experiment schemas remain authoritative for game
bodies/envelopes. Use `semaphore_hub.interfaces`, `repositories` and `policy`;
coordinator-owned schema/protocol changes return to the coordinator for review,
integration and a new shared baseline before dependent work resumes.

Services acquire the common per-game lock before a short repository transaction.
Repositories never commit. Perform model work and asset writes outside SQLite
write transactions. No success precedes commit. Recovery completes before traffic;
online maintenance uses the same locks as live play. Wall-clock UTC epoch ms is
for retention and persistence; monotonic elapsed ms is for gameplay ordering.
Never put participant clues, session tokens, passwords, private DBs or model
weights in source, logs or evidence. Synthetic fixtures are not real acceptance.

Worker setup: `uv sync --locked --group dev`. Before returning: targeted tests,
`uv run --no-sync ruff check .`, `uv run --no-sync ruff format --check .` and
`git diff --check`. Provide commits, owned changed files, exact commands/results,
evidence path and remaining issues. Only coordinator integration closes a session.
Concrete SQL adapters belong in each worker's domain directory and receive the
shared transaction connection; the coordinator composes the concrete UnitOfWork.
Root dependency/lock/CI, shared exports/composition, migrations/storage and contracts
remain coordinator-owned throughout W2/W3.

## W2-B — Accounts

Branch `codex/s2-w2-b-accounts`. Own `packages/semaphore_hub/auth/`,
`tests/hub/auth/`, `docs/evidence/s2-w2-accounts.md`.
Implement handlers/services for the frozen account routes and operator bootstrap/
reset callbacks for coordinator CLI wiring. Consume account repository and principal
interfaces; no SQL schema copies. Use a maintained Argon2id library; request the
coordinator's dependency/lock update before implementation. Measure pinned parameters
on the selected host and report concurrency/memory/latency, without claiming the
W1 contract chose measured host values. Deliver revoke/delete primitives for F.

Tests: case collision/normalization, disabled signup with working existing login,
generic failure, absolute/idle expiry, login rotation, logout/reset revocation,
Host/Origin/CSRF rejection before writes, bounded counters/hash work, tombstones and
public/private identity separation. No account-erasure orchestration or game service.

## W2-C — Trusted installed packs

Branch `codex/s2-w2-c-packs`. Own `packages/semaphore_hub/packs/`,
`tests/hub/packs/`, `docs/evidence/s2-w2-packs.md`.
Implement repository-backed operator installation and read routes. Require explicit
owner, rights provenance and acceptance; existing experiment measurements do not
publish content. Reuse manifest parser/hash/verifier/model identity APIs. Reserve
ownership before digest comparison, verify outside transactions, stage immutable
assets by atomic rename, and publish only after all pins/reports are validated.
Return operator handler callbacks for coordinator wiring; no upload jobs/API.

Tests: concurrent first claim, foreign owner even with matching bytes, exact retry,
byte conflict, missing/invalid report/model, interrupted staging and orphan cleanup,
immutable versions and published-only visibility. Supply a rights-cleared bounded
acceptance pack with provenance, separate from synthetic test content. No creator
portal, corpus expansion or protocol changes.

## W2-D — Browser against fixtures

Branch `codex/s2-w2-d-browser`. Own `web/`, `tests/web/`,
`docs/evidence/s2-w2-browser.md`.
Build signup/login/logout, installed artifact selection, private-capture disclosure,
server-authoritative play, receipt polling, terminal history and exact cohort board
against frozen durable fixtures. Preserve the experiment entry path for regression.
Recover uncertain creates through the owner-only current-game lookup.
Never automatically retry uncertain creates. Preserve command IDs and original
payloads on uncertain command outcomes; reconnect must not rewind or double animate.

Tests: pending/final/rejected/expired auth, interruption without competitive score,
empty history/board, cursor and cohort isolation, escaped names, keyboard/mobile/
reduced-motion flows. Run `node --test tests/web/*.test.mjs` and relevant browser
checks. No backend endpoints, live credentials or human/real-service acceptance claims.

## W3-E — Durable games and results

Branch `codex/s2-w3-e-games`. Own `packages/semaphore_hub/games/`,
`packages/semaphore_hub/results/`, `tests/hub/games/`, `tests/hub/results/`,
`docs/evidence/s2-w3-games.md`.
Consume integrated W2 auth/pack adapters and frozen repositories/inference/keyring.
Implement game HTTP handlers, admission/rejection capture, HMAC equality, once-only
completion, transactional terminal records, private history and public exact-cohort
boards. Export lifecycle callbacks for F; never edit F's operations or shared SQL.

Tests: owner checks before receipt lookup, changed/exact retries including raw
removal, queue bounds/late results, due-work/quit races, zero natural score,
interrupted no-score, commit failure, restart persistence and full tie-key pagination.
Use real reducer outputs; no client-supplied scores/pins or practice publication.

## W3-F — Operations

Branch `codex/s2-w3-f-operations`. Own `packages/semaphore_hub/operations/`,
`tests/hub/operations/`, `docs/operations/durable-hub.md`,
`docs/evidence/s2-w3-operations.md`.
Use fake lifecycle adapters until E is integrated. Implement startup recovery,
read-time expiry plus daily cleanup, clue deletion, account erasure/tombstones,
external deletion ledger replay, encrypted backup rotation and restore preparation.
Expose host/operator callbacks; coordinator composes CLI/startup. No raw-clue web
API and no bypass of the common live-game locks. Key material remains outside DB.

Tests: 30-day raw deadline, 90-day terminal retry deadline, exact retry after clue
removal, account revocation/anonymization, shared pack retention, missing-key failure,
backup expiry within 30 days, deletion replay before traffic, pending interruption
without score and cleanup failure reporting. Retain ledger through affected backups.

## W3-G — Independent probes

Branch `codex/s2-w3-g-probes`. Own `experiments/durable_acceptance/`,
`tests/hub/acceptance/`, `docs/evidence/s2-w3-independent-probes.md`.
Build contract-driven subprocess crash probes around admission/completion/terminal
commits, restart, foreign ownership, altered retries, clue/account deletion, cohort
boundaries and restore. Consume integrated W2 and fixtures; never import E/F working
trees. Self-check that probes catch deliberately faulty fake services. Instrument
real-model load for later W4 use without running competing model pressure jobs.

Coordinator runs probes against integrated SQLite/service processes after E/F merge.
A fake harness pass alone does not close W3. No implementation of E/F behavior.

## Coordinator acceptance and retained gates

W1 requires fresh-checkout locked install, schema fixture/ref validation, migration
upgrade/constraints, fake interface smoke, full Python/Node regression, lint/format
and a packaged-resource import. Record the exact reviewed baseline before any W2
worker starts. W2 also requires Stage 1 closure or an explicit owner carryover
decision; W1 completion alone does not supply it.

Keep the 100 ms target, full human acceptance, remote-host offline/resource and
content-review/sourcing follow-ups open. No account/transport choice waives them.
W4 supplies signed-in real-model play, real persistence/deletion checks and final
stage disposition; these briefs do not claim that evidence already exists.
