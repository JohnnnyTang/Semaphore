# S2-W3-G independent probes

November 16, 2026. Implemented from shared W3 dispatch baseline
`2a00a4334227274abfdf29ea9eb86c3571b95057` in isolated
`codex/s2-w3-g-probes`. No E/F working tree or service implementation was imported.

Delivered a persistent subprocess adapter harness, six forcibly terminated commit
windows, and an independent behavior oracle covering ownership, changed/exact
retry, clue deletion, inference non-reexecution, tied cohort pagination, account
erasure and deletion-ledger replay after restore. Signals and result files use
atomic rename. Lost/missing checkpoints, worker failures and bounded timeouts fail
closed. Worker output and exceptions are suppressed rather than copying secrets.
The runner requires fresh disposable workspaces.

[Adapter protocol and runner](../../experiments/durable_acceptance/README.md)
define the coordinator integration surface. A worker persists across operations
until killed so real in-memory reducer state is not reconstructed between commands.
After termination, a fresh worker runs actual recovery via the adapter.

## Validation

- `uv sync --locked --group dev`: passed in isolated checkout.
- `uv run --no-sync pytest tests/hub/acceptance -q`: 18 passed.
- `uv run --no-sync ruff check .`: passed.
- `uv run --no-sync ruff format --check .`: passed.
- `git diff --check`: passed.

Oracle self-checks use an explicitly fake, file-backed adapter with synthetic data.
Nine deliberate defects are detected: premature admission persistence, recovery
score invention, altered retry acceptance, foreign receipt disclosure, retained
raw clues, repeated inference, cross-cohort cursor acceptance, broken full tie-key
pagination and ignored external deletion ledger. Tests also reject missing fault
checkpoints and verify that load timing never records exception contents.

## Remaining acceptance

This is harness validation, not an integrated SQLite/service crash pass. Coordinator
must provide the actual E/F adapter, map real commit hooks and run all scenarios.
Fake adapter backup/restore is only an oracle self-check, not encryption evidence.
This slice does not cover retention-boundary dates, missing-key failure, physical
queue-slot retention, concurrent quit/completion or all transport validation; E/F
checks and later acceptance must cover those. The full synthetic adapter protocol
requires a terminal scenario controlled through the real reducer, not fabricated
scores or participant data. No model pressure job ran. W4 instrumentation is ready
but real-model/human acceptance and all named Stage 1 carryovers remain open.

Follow-up contract audit corrected the changed-retry oracle to require HTTP 200
and a `command_conflict` receipt, per durable OpenAPI, rather than an invented
HTTP 409 requirement. Defective fake retry acceptance remains detected.
