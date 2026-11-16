# W3 independent durable acceptance probes

This harness tests a trusted local adapter module in a persistent subprocess.
It does not implement a game, repository, authentication or recovery service.
`tests/hub/acceptance/fake_probe_adapter.py` is deliberately fake oracle self-test
material and must never be reported as integrated persistence acceptance.

Run after coordinator integration:

```powershell
uv run --no-sync python -m experiments.durable_acceptance --adapter YOUR_MODULE --workspace data/probes/FRESH_DIRECTORY
```

The workspace must be empty and contain only disposable synthetic data. Never
point this harness at a participant database. Each scenario receives a separate
subdirectory. The adapter is trusted executable Python, not an uploaded extension.
No participant clues, credentials, tokens, vectors or private digests belong in
returned observations. Harness stdout contains probe names and pass flags only;
worker stdout/stderr are discarded and exceptions become `adapter_failed`.

## Adapter API

Export `open_adapter(workspace: pathlib.Path, checkpoint: Callable[[str], None])`.
Return an object with `execute(operation: str, payload: dict) -> dict`.
The object and process persist across operations, so real reducer memory survives
normal calls. After an injected crash the next call constructs a new adapter;
construction must not automatically recover before the explicit `recover` call.
Use the workspace for SQLite, immutable assets, external keys and deletion ledger.
The adapter may call integrated E/F services only; never reimplement their decisions.
The adapter translates IDs/statuses into the safe projections below and must not
replace observed values with expected values. Startup/readiness errors propagate.

For `admission`, `completion`, and `terminal`, invoke the supplied checkpoint at
`PHASE.before_commit` immediately before the relevant SQLite commit and
`PHASE.after_commit` immediately after it. The callback returns normally except
for the selected fault point, where it emits an atomic signal and blocks. The
parent forcibly terminates the process; Python cleanup/rollback does not run.
Checkpoint hooks must wrap actual service transaction commits, not a fake adapter
transaction. Missing checkpoints fail the scenario. No success may precede commit.
Use `ProcessAdapter.close()` when embedding the harness in a longer-lived runner.

| Operation | Required behavior/projection |
| --- | --- |
| `fixture_setup` | `phase` is admission/completion/terminal/behavior. Create an owner and foreign account, a published synthetic-only acceptance fixture, one active zero-score game and appropriate prerequisites. For completion, admit one pending command. For terminal, complete one command while still active. Behavior starts before admission. No production publication. |
| `admission` | Submit one fixed valid clue command through the service, preserving exact original payload and command ID in adapter memory for retries. |
| `completion` | Deliver the queued completion using real reducer/service code, resolve the command with a non-clearing result without ending the fixture game. |
| `terminal` | Advance due work to natural `pack_exhausted` termination; the primary game must receive one score row, including when score is zero. |
| `recover` | Run actual pre-traffic recovery; return `{"ready":true}` only on success. |
| `observe` | Read primary-game projection described below from actual persisted state; no service state changes. |
| `retry` | `variant`: exact/clue_case/clue_whitespace/expected_revision. Reuse same ID; alter only named field. Return `status` and original clue-free receipt for success; omit current snapshot so equality compares immutable receipt. Changed payload returns HTTP 200 with `receipt.outcome=command_conflict`, as frozen durable OpenAPI specifies (not HTTP 409). |
| `foreign_receipt` | Foreign authenticated principal; `known_command` selects existing or nonexistent receipt. Return exactly `{"status":404}` for either. |
| `delete_clues` | Execute owner clue-only deletion through operations service. |
| `board` | Prepare two additional equal-score/equal-time naturally finalized fixture games named `tie-a` and `tie-b` in a dedicated accepted cohort. Return their actual ordered public IDs as `items` and real opaque `next_cursor`; primary-game observations exclude these extra fixtures. Support `cohort=other` with a single changed cohort pin and reject the original cursor with 400. `limit=1`. |
| `backup` | Create an actual encrypted backup using operations; retain newest ledger outside it. |
| `delete_account` | Execute account erasure, including external ledger entry. |
| `restore` | Restore the backup and run current-ledger replay, retention and interruption before reporting success. |

`observe` returns exactly these stable fields (extra unstable fields would break
idempotency comparison): `status`, `end_reason`, `command_count`, `pending_count`,
`score_count`, `receipt_outcome`, `raw_count`, `inference_calls`, `session_count`,
`display_name`, `published_count`, `namespace_reserved`.
Counts concern the primary account/game, except publication refers to its shared
fixture pack. `raw_count` includes all raw/derived private clue copies.
`receipt_outcome` normalizes a successfully completed receipt to `completed`,
and interrupted pending receipt to `game_over`; it must reflect the saved receipt.
`inference_calls` is the cumulative real injected-inference invocation counter,
not retry request count. Pack namespace stays reserved after account deletion.

The six crash scenarios verify admission visibility, completion immutability,
terminal-score atomicity, pending settlement, no restart score and repeat recovery
idempotence. The behavior scenario verifies exact/changed retry, foreign receipt
nondisclosure, clue deletion without rerunning inference, full tie-key pagination,
cohort-bound cursor and account erasure surviving backup restore.

## W4 load instrumentation

`LoadRecorder.measure(phase, batch_size=N)` wraps future model load, entry embedding
or query embedding calls. It records elapsed monotonic time, batch size and a
success flag; it never captures text, vectors or exception contents. `summary()`
returns successful p95 and measurements. No model is loaded or invoked by import
or this harness. This instrumentation is not a latency/throughput acceptance run.
