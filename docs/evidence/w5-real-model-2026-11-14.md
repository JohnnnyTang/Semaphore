# November 14 real-model acceptance measurements

Measured November 14, 2026 (Asia/Shanghai), from baseline `5f38161` plus the
instrumentation and reporting changes in this checkout. Machine-readable metadata
includes exact Python source hashes for each run. Stage 1 remains open.

## Method and scope

- Game server and simulated clients: Windows 10 build 19045, Python 3.12.10,
  Intel Core i5-13490F (10 cores / 16 logical processors), 34,164,101,120 bytes RAM.
- Browser-to-server networking is represented by loopback HTTP, with 10 ms receipt
  polling. These are simulated clients, not physical LAN browsers or human sessions.
- Gameplay and pressure workers use the same operator-supplied remote Ollama origin.
  The full frozen fingerprint matched `657120305f464d0fb6a6006b9dbc8152af04ba30317dadcef1b41af0aa2941a4`.
  The selected Qwen3-Embedding 4B artifact returned 2,560 dimensions. Ollama reports
  2,647,539,056 model bytes and the same VRAM byte count, with context length 512.
  This is service-reported residency, not an independent GPU model/utilization audit.
- Preloaded game fixture: `fixtures/w3/calibration-authored.json`, default paced
  casual rules and 5-second base arrivals. Verification fixture:
  `fixtures/w3/held_out-authored.json`, frozen `experiment-arcade-v1` verifier policy.
  This run does not resolve the documented casual/verifier ruleset mismatch.
- Entry preparation and three excluded warm-up queries precede independent parity
  and load. No model unload, internet isolation, or cold-start acceptance is claimed.
- Each concurrency group requests 20 attempts per player, one outstanding per game,
  and a separate real verifier repeats until gameplay stops. Overlap requires
  successful gameplay intervals intersecting pinned verifier adapter intervals.

Queue headers measure enqueue-to-adapter-start. Embedding headers include pinned
identity checks, HTTP, remote waiting and adapter validation; ranking and client
polling are outside that component. Component percentiles are independent and must
not be added or subtracted to infer network time. No GPU-only execution timing or
hardware-utilization claim is made.

## Initial run and reporting correction

[Initial parity](w5-real-2026-11-14/parity.json) passed all 900 sampled clue cases
between fresh reference and core processes at absolute score tolerance `1e-5`,
with identical ordered ranks, sample membership and report fields.

The [initial load](w5-real-2026-11-14/load.json) completed 20/20 successful samples
at one player (p95 707.3 ms), and 77/80 at four players (p95 4,209.2 ms among
successful samples, with three stale-revision receipts). All eight-player tasks
errored before completing their requested rounds. The old harness discarded each
task's earlier samples on error, so its zero eight-player samples and absent overlap
must not be interpreted as zero successful work or zero actual contention.

The reporting correction preserves partial samples and adds recorded counts,
outcome counts and fixed probe failure reasons. A separate repeat uses the same
20-attempt workload. The original evidence is retained unchanged. A conflicting
retry was also corrected to omit the original command's timing headers; this has
no effect on the exact-payload retries used by the load probe.

## Repeat and gate disposition

[Repeat parity](w5-real-2026-11-14-repeat/parity.json) again passed all 900 cases.
The [repeat load report](w5-real-2026-11-14-repeat/load.json) retains the failures:

| Players | Requested / recorded / successful | Round-trip p50 / p95 | Queue p95 | Adapter p95 | Successful samples overlapping verification |
| --- | --- | --- | --- | --- | --- |
| 1 | 20 / 20 / 20 | 571.9 / 671.4 ms | 0.2 ms | 578.4 ms | 18 / 20 |
| 4 | 80 / 80 / 77 | 3,206.2 / 3,754.4 ms | 2,436.5 ms | 1,173.6 ms | 77 / 77 |
| 8 | 160 / 109 / 22 | 4,676.3 / 5,693.3 ms | 3,854.3 ms | 1,250.3 ms | 22 / 22 |

**All latency statistics above describe successful clear/miss receipts only.**
The eight-player numbers are survivor statistics, not a passing full-workload p95.
Four players produced three stale-revision receipts. Eight players produced 67
inference timeouts, 12 stale revisions, seven game-over receipts and one overload;
all eight tasks ended early, leaving 51 requested attempts unissued. Those are
failures, not removed samples. The one-player 100 ms check is false; four/eight
target checks remain null because the prerequisite failure-free workload did not
complete. Neither null result is a pass.

Measurement limitation: regression checks overlapped the repeat's early load phase.
Parity/load transition was 07:20:48 UTC and the build finished at 07:21:20 UTC.
Therefore the repeat's one/four-player figures are not isolated-host benchmark
claims. Those checks finished before the eight-player phase. The initial run had
no concurrent regression suite and independently showed 707.3 / 4,209.2 ms p95 at
one/four players. Both runs used an ordinary desktop host without controlling all
other applications or remote model clients. Remote utilization remains unmeasured.

**Disposition: real-model fixture parity passes; load/performance acceptance fails.**
Preserve the 100 ms target and remain within Stage 1. Queue wait is a major observed
component at concurrency, while even one-player adapter time exceeds the target.
These measurements do not identify how much adapter time comes from identity
checks, remote queueing, network or model execution. The next bounded performance
task should profile those pieces and evaluate game-priority verification scheduling
and FIFO contention, then repeat on a quiescent named host. Record an explicit
tuning/scope decision before claiming a revised target. Stale revisions also need
separate investigation around scheduled state changes; do not silently retry them
away from this acceptance denominator.

## Implementation and validation

- Added receipt-only queue/adapter headers, without changing frozen JSON or gameplay.
  Exact retries retain timings; pending/conflicting/rejected/skipped work does not
  acquire fabricated values. Timed-out work exposes measurements only after return.
- Added the real-model runner with pinned preflight, warmup, independent parity,
  shared-origin pressure, separate aggregate artifacts and server cleanup.
- Fixed partial-sample retention, safe early-exit reasons and outcome counts.
- Regression validation: **191 Python tests, six client JavaScript unit tests**,
  Ruff lint/format, package wheel/source build and whitespace checks passed.
  Tests cover FIFO delay, adapter time, exact and conflicting retries, rejected
  commands, active versus skipped timeout work, and sample retention after failure.

Evidence includes aggregate outcomes, hashes and timings; it contains no vectors,
private participant clues, raw worker streams or upstream error bodies. Test/source
counts are current-session results, not copied from earlier seven-test browser runs.

## Reproduction

Set `SEMAPHORE_OLLAMA_BASE_URL` to the operator-provided origin, then run:

```powershell
$env:PYTHONPATH = 'packages;.'
.venv/Scripts/python.exe -m experiments.acceptance.measure --output-dir output/acceptance-run --rounds 20
```

The runner starts and closes an isolated loopback server. Probe execution success
does not imply the latency target passed. Fixture semantic quality, human feel,
CPU-only 8 GB support, offline startup, production contracts and publication
acceptance remain separate gates.
