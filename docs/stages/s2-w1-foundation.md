# Stage 2 W1 — Initial storage and startup slice

November 16, 2026 (Asia/Shanghai). State: running, not integrated or frozen.
Owner instruction: “get started with stage 2 first wave”. Coordinator branch:
`codex/s2-w1-a-contracts`. Starting HEAD:
`67334c2c7fbc1b2840ff06f7141087f9a450490d`. Existing local changes to the project
plan, README and Stage 2 plan were preserved. No workers were dispatched, and no
reviewed commit has been issued as a common worker baseline.

## Implemented boundary

`semaphore_hub` is packaged alongside `semaphore_core`, without new dependencies.
`python -m semaphore_hub PATH` prepares a SQLite database only. It does not start
an HTTP server or claim that an initialized database is ready for play.

Connections enable foreign keys and a five-second busy timeout. Services own short
`BEGIN IMMEDIATE` transactions; repositories must not commit, nest transactions or
perform inference/filesystem operations while holding a write transaction. SQLite
connections are thread-confined. The migration runner verifies the ordered name
and SHA-256 ledger and applies DDL plus ledger updates atomically. It rejects
unversioned existing databases, edited history and future schema versions. There
is no import path from experiment state. Empty databases and exact known migration
prefixes are supported; future changes must append migrations, not edit applied SQL.

Migration 0001 establishes initial accounts/sessions, namespace ownership and
immutable pack bytes, pinned games, private commands/attempts, terminal scores and
a deletion ledger. It enforces FKs, namespace/version uniqueness, immutable pins,
final receipt immutability, once-only scores and natural-ending-only score writes.
A retained deleted owner is an account tombstone; game/score player links and name
snapshots can be cleared without changing result provenance.

This is an initial schema, **not the complete frozen storage contract**. SQL does
not validate full snapshot semantics, authorization, publication eligibility,
HMAC correctness or authoritative reducer scores. Those require the forthcoming
repositories/services and independent probes. Pack installation reservations,
publication state, entries, reports, vector caches, artifact identity, board indexes
and repository protocols still need coordinator-owned migrations/interfaces.

The composition skeleton exposes principal, UTC/monotonic clock and common game
lock interfaces. Startup runs migrations, deletion-ledger application, expiry,
active-game interruption and orphan cleanup before setting readiness. Any hook
failure leaves readiness false. Hooks are interfaces with fake test adapters;
production recovery is W3 work. Runtime maintenance must acquire the same per-game
lock as play **before** its short database transaction. Startup cannot run alongside
traffic; an eventual server must honor readiness and single-start lifecycle.

## Gate audit and dispatch disposition

Proceed with W1 preparation only. W2 remains blocked pending completed W1 contracts
and either Stage 1 closure evidence or an explicit bounded-work carryover decision.
The request to start W1 does not waive Stage 1 acceptance or launch W2.

The November 14 [refinement report](../evidence/feasibility-refinement-2026-11-14.md)
supersedes the earlier eight-player timeout finding: its longer run recorded zero
inference timeouts, but five stale revisions at eight players and successful-round
p95 of 1,633 / 2,420 / 3,148 ms at 1/4/8 players. The 100 ms target remains unmet.
Independent parity passed 900 cases; this does not prove latency or human acceptance.
Full human acceptance, remote-host offline/resource isolation, independent content
review and population sourcing yield remain unverified. Preserve these follow-ups
for controlled real-model measurements and human acceptance; no synthetic storage
test in this slice closes them. Ruleset/storage reconciliation in decision 0005
is adopted and should not be reported as the old unresolved contract mismatch.

## Remaining W1 work before a worker baseline

1. Account ADR: freeze signup/HTTP choices, normalization, hashing measurements,
   session/CSRF lifecycle, exact Host/Origin validation, reset and bounded throttling.
2. Separate durable OpenAPI plus schema-valid account/pack/game/history/board/error
   fixtures, including uncertain create handling; preserve the experiment API.
3. Complete installer/report/artifact schema and repository protocols, transaction
   ownership, inference admission/deadlines and rejection capture boundaries.
4. Freeze HMAC key lifecycle and deletion/backup recovery interfaces, trusted install
   rights/budget/acceptance workflow and exact casual cohort identity.
5. Exercise every completed interface with fake adapters; issue detailed W2/W3 briefs
   with exact ownership and a reviewed committed baseline. Only then close W1.

## Validation

Commands: `uv sync --locked --group dev`; `uv run --no-sync pytest`;
`uv run --no-sync ruff check .`; `uv run --no-sync ruff format --check .`;
`node --test tests/web/*.test.mjs`; `uv build --no-build-isolation`.

Targeted tests cover reopen/idempotent migration, future/edited history rejection,
atomic migration and terminal-write rollback, known-prefix upgrade, foreign keys,
namespace uniqueness, immutable pins/receipts, zero-score natural termination,
interrupted score rejection, and ordered fail-closed startup. These are foundation
checks, not durable service, independent process-crash or real-model acceptance.

Recorded results for this slice: 221 Python tests passed (16 new hub checks),
7 Node browser tests passed, repository Ruff lint/format and diff whitespace
checks passed. Locked dependency sync and sdist/wheel build passed. An isolated
wheel import and in-memory migration/reopen passed after refreshing the local
same-version uv package cache (`--refresh-package semaphore-core`). SQL resources
were verified inside the wheel. No real-model workload or human acceptance was
run, and no commit/push or worker dispatch is claimed.
