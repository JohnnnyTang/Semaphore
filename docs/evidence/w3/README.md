# W3 actual-protocol evidence

Measured November 9, 2026. The owner accepted bounded W4 continuation with the
100 ms Stage 1 target retained and unmet. W3 closes the dependency boundary for
that prototype only. See [decision 0004](../../decisions/0004-w3-gate-closure.md).

## Verification results

All six reports use the actual `bottom3-median-v1` protocol, not the earlier
research evaluator's authored decoys. Every manifest passes promoted-schema and
legality checks before embedding. The full model/runtime fingerprint matched the
lock before and after each verification. All measured reports satisfy the report
schema. They carry no publication authority.

| Input | Entries / legal clues | Reachable | Mean entry median rank |
| --- | --- | --- | --- |
| [Calibration authored](calibration-authored.json) | 90 / 270 | 90/90 (100%) | 1.078 |
| [Calibration weak](calibration-weak.json) | 90 / 270 | 8/90 (8.89%) | 10.944 |
| [Calibration mixed](calibration-mixed.json) | 90 / 270 | 64/90 (71.11%) | 4.222 |
| [Held-out authored](held_out-authored.json) | 60 / 180 | 60/60 (100%) | 1.050 |
| [Held-out weak](held_out-weak.json) | 60 / 180 | 5/60 (8.33%) | 10.733 |
| [Held-out mixed](held_out-mixed.json) | 60 / 180 | 43/60 (71.67%) | 4.583 |

The unchanged 0.85 diagnostic separates these deliberately constructed views.
This does not locate a defensible publication boundary. These synthetic packs
reuse previously inspected vocabulary/clues; their split names refer to the
original fixture partition. No independent human authoring, marginal-pack labels,
fresh unseen holdout or human enjoyment is claimed. General and specialist entries
are pooled here; this is not an independent category-quality result.

The [input plan](../../../fixtures/w3/plan.json) fixes all six manifest byte hashes,
the original fixture, full fingerprint and protocol hash. The
[freeze](freeze.json) binds the calibration reports before the held-out phase.
[Binding](binding.json) covers all measured reports, parity summaries, latency,
freeze and executable probe sources. The byte hashes survive checkout under the
existing LF attributes; `parity.cjs` is explicitly LF as well.

## Numeric checks

Six `*-parity.json` summaries record ten queries per pack: **60 representative
real-vector query/pool comparisons**, each with all entry IDs in that pack.
Python 3.12.12 and Node v24.12.0 agreed on every ordered ID and raw score (maximum
observed score difference 0). Separate offline tests cover positive and negative
bucket boundaries and ASCII ties. Only numeric ranking is implemented independently
in JavaScript; manifest parsing, decoy sampling and medians are not independently
reimplemented. This is bounded numeric evidence, not complete creator/hub parity.

## Bounded latency investigation

The [retained final probe](latency.json) uses 100 operations per concurrency,
unchanged digest enforcement, the same synthetic clue, and warm model requests.
There is no running game server yet, so these are adapter operations, not players.

| Concurrent operations | Adapter p50 / p95 (ms) | Embedding HTTP p95 (ms) | Service-reported total p95 (ms) |
| --- | --- | --- | --- |
| 1 | 117 / 160 | 83 | 36 |
| 4 | 200 / 287 | 157 | 21 |
| 8 | 324 / 475 | 224 | 37 |

The earlier bounded probe shown to the owner measured 167 / 186 / 304 ms p95;
the final repeat confirms the miss and shows substantial variability. No speedup
or supported-load improvement is claimed. Separate inventory requests contribute
material cost. HTTP residual includes transport, JSON and client work, not pure
LAN latency; component percentiles cannot be added. Inference duration was absent
in all 300 responses and is recorded as null, never as a zero-cost inference claim.
Service times do not independently verify GPU execution or hardware.

The 100 ms full-game target **has not passed**. W4 must retain model-change
detection, bounded FIFO work, admission limits, timeouts and current-board ranking.
W5 must measure actual game round trips at 1/4/8 players with background pressure.
Independent creator parity, publication calibration, human play and supported
release hardware remain later acceptance requirements.

## Validation

Validation: **121 pytest tests pass**, including 15 new closure-probe tests.
Ruff lint and formatting pass; source distribution and wheel builds pass.
The closure adds protocol failure-boundary, exact-metric, sampling-order,
numeric-boundary, lexical-scope and evidence-binding tests. The complete pytest
suite requires loopback access for its local HTTP stubs. Restricted-sandbox
network failures are not model or implementation failures. Lint, format, fixture
validation, source distribution and wheel build were also checked. Hosted CI was
not run by this task. See [probe instructions](../../../experiments/w3/README.md)
for reproduction.
