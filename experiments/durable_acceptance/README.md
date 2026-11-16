# W3 independent durable acceptance probes

This harness tests a trusted local adapter module in a persistent subprocess.
It does not implement a game, repository, authentication or recovery service.
`tests/hub/acceptance/fake_probe_adapter.py` is deliberately fake oracle self-test
material and must never be reported as integrated persistence acceptance.

Run after coordinator integration:

```powershell
uv run --no-sync python -m experiments.durable_acceptance --adapter experiments.durable_acceptance.real_adapter --workspace data/probes/FRESH_DIRECTORY
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
`receipt_outcome` is the persisted receipt outcome: the non-clearing synthetic
fixture yields `miss`, and interrupted pending receipts yield `game_over`.
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

## W4 opt-in authenticated HTTP load

`http_load` exercises the deployed durable HTTP boundary with independent cookies
and CSRF tokens. Prepare a **disposable test installation**, eight distinct test
accounts and an accepted immutable artifact. Natural endings can create durable
scores: never use a participant installation or real participant accounts. The
runner does not install or publish synthetic packs, create users or restart hosts.
Ensure no other model consumers run during the measurement window.

Keep credentials in an ignored operator-only JSON file containing objects with
`login_name` and `password`. Keep a separate JSON array of synthetic clue strings.
The clues must be legal for the selected artifact; rejection outcomes are failures,
not fast inference samples. No supplied credentials or clue strings enter output.

```powershell
uv run --no-sync python -m experiments.durable_acceptance.http_load --origin http://127.0.0.1:8080 --accounts data/probes/accounts.json --clues data/probes/clues.json --artifact ACCEPTED_ARTIFACT --server-revision FULL_40_CHARACTER_COMMIT_SHA --players 1 4 8 --commands 10 --output data/probes/FRESH_HTTP_REPORT.json --disposable-test-installation
```

The output file must not exist. Cohorts run sequentially. Each player's game is
created once; a lost create response is never retried. Players synchronize before
timed commands. Each player has at most one unresolved command; the runner polls
receipts, verifies exact retries and quits its own game on completion/failure.
A create with an uncertain response may leave an active test game; inspect the
installation before another run. Cleanup failures remain visible in the report.

Reported latency is command POST through the observed final receipt (20 ms poll
interval plus HTTP overhead), excluding login/create and exact-retry validation.
Only `clear`/`miss` count as successful inference-path outcomes. Rejections,
timeouts, partial samples, early game endings and errors remain visible. p50/p95
use nearest-rank successful samples; `complete` additionally requires every planned
command and no player error. Exit status is nonzero for incomplete runs. A complete
run can still miss the 100 ms target; inspect `latency_target_met`.

This first slice has **no concurrent verifier workload, remote resource collection,
queue/embedding breakdown, restart orchestration or proof of real model execution**.
Public artifact cohort pins are captured; the server commit is operator-declared,
not remotely verified. Host metadata describes the load generator. Do not call this
Stage 2 acceptance or compare its timings directly with embedding-only measurements.
No successful fake run establishes model latency. The independent subprocess crash
runner remains the existing restart/deletion proof; real browser/human acceptance
and controlled verifier-overlap measurements remain W4 work.

## Fresh real-model orchestration

`real_run` provisions a new disposable installation and independent random keys,
uses the real trusted installer/verifier, starts an actual `DurableHost` subprocess,
and runs HTTP load concurrently with repeated actual `verify_pack` calls against
the same pinned Ollama service. It never copies a live database or strips content
tags. Supply the exact rights-cleared manifest and an explicit accepted casual
configuration (`initial_board`, `schedule`, optional `seed`/`generator_policy`).
The configuration should last long enough for all planned commands. A separate
five-second artifact is accepted for the natural-ending/restart check.

Use only after obtaining an exclusive model-pressure window: it competes with
human play and other model users. `SEMAPHORE_OLLAMA_BASE_URL` must identify the intended
pinned model endpoint (see the adapter environment documentation). The workspace
and output paths must be new, inside an operator-restricted private directory.
Keys, SQLite data and generated disposable credentials must never enter Git.
Credentials remain in memory; generated keys and private test data remain on disk
for inspection. The runner stops all its subprocesses when finished.

```powershell
uv run --no-sync python -m experiments.durable_acceptance.real_run --workspace data/w4/FRESH_INSTALL --manifest packs/everyday.json --configuration data/w4/configuration.json --clues data/w4/synthetic-clues.json --rights-reference docs/evidence/s2-w2-installation.md --server-revision FULL_COMMIT_SHA --output data/w4/FRESH_REPORT.json --commands 10 --port 18084 --allow-model-traffic
```

Installation telemetry is stored beside the report; server and verifier telemetry
is inside the new workspace. Reports contain model identity, manifest digest,
artifact/cohort pins, per-cohort start/end timestamps, completed model-call intervals
and failures. `verified_overlap` requires an observed successful completed model
call intersecting the corresponding HTTP load interval. Starting a verifier process
alone cannot establish overlap. Calls interrupted by forced verifier termination
remain as unmatched start events; the exit status and forced-stop flag are retained.
This is direct verifier pressure on the same endpoint, not a production upload queue.

If `psutil` is available, timestamped hub subprocess RSS and cumulative CPU are
sampled every 100 ms. Remote model-server resources and queue-delay breakdown are
not measured. Do not mistake load-generator/hub metrics for remote GPU/CPU evidence.
No dependency is installed implicitly. After load, one short game ends naturally;
its terminal snapshot, history and exactly-one score are checked after process
termination/restart. A second active game must instead become interrupted with no
score. This is automated persistence evidence, not human play acceptance. Existing
crash probes cover the narrower SQL transaction fault boundaries.

The final report is written even on caught setup/run failures, with safe exception
class labels rather than private exception text. Review both `load` completeness
and latency, actual overlap, inference events and `restart.passed`; a successful
runner exit alone is never a Stage 2 acceptance or sub-100 ms claim.

Before timed load the runner waits up to 180 seconds for a successful verifier
query batch. It records verifier batches using the configured provider batch size;
the pinned identity is checked for each batch. Exit zero requires all three cohorts
complete, observed game inference, successful verifier-call overlap in every cohort,
and restart checks passing. The 100 ms target remains a separate reported gate.
