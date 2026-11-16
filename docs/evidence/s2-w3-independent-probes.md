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

## Original handoff (superseded by integration below)

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

Terminal fault fixtures use real casual deadline `pack_exhausted`, following one
non-clearing completed clue, to permit an isolated terminal transaction and a
natural zero score. `pack_cleared` belongs to completion itself and cannot be
fabricated as a later due-work transition.


## Real-service integration — November 16, 2026

The real adapter now composes GameService, ResultsService, AuthService,
Operations, ExternalLedger and EncryptedBackups over SQLite. Each fault hook
brackets the actual service transaction commit, selected by the corresponding
command-admission, receipt-finalization or terminal-game SQL change. The harness
forcibly kills the worker at each hook and starts a fresh worker for Application
recovery. No reducer, receipt, recovery, score, deletion or backup decisions are
reimplemented by the adapter.

All six commit-window probes and the ownership/retry/cohort/deletion/encrypted
restore probe passed. The [sanitized report](s2-w3-real-probes.json) records the
seven outcomes. Regression command `python -m pytest tests/hub/acceptance -q`
passed **25 tests**, including the existing deliberate-defect oracle checks.
Ruff lint and formatting passed for both probe directories.

Reproduce with a new disposable directory:

```powershell
.venv/Scripts/python.exe -m experiments.durable_acceptance --adapter experiments.durable_acceptance.real_adapter --workspace data/FRESH-W3-PROBES
```

The fixture installer alone substitutes synthetic verification measurements and
vectors. The injected inference queue returns a deterministic non-clearing result,
so the persisted receipt is `miss` and natural terminal score is zero. The oracle
now checks this actual frozen receipt outcome instead of requiring adapter
normalization to the invented `completed` value. Inference invocations are counted
at the injected queue's submit method, including unexpected retry submissions.
The tie records use real reducer deadline completion with equal timestamps and
scores. The CLI closes each subprocess in `finally`, including failed probes.

These are real local SQLite/service-process crash and privacy results, using
synthetic clocks, model outputs and public fixture keys. They do not establish
network transport/browser integration, real model performance, human acceptance,
remote-host deployment or independent content quality. Those W4 and Stage 1 gates
remain open; concrete host readiness/key/asset validation is separately tested.
