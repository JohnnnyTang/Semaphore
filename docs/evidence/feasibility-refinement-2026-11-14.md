# Queue and polling refinement

November 14, 2026. Follow-up to the [feasibility pilot](feasibility-2026-11-14.md).
The owner requested refinement of its failures. The change targets eight-player
inference timeouts without increasing deadlines, changing the model, weakening
identity checks, or substituting cached/repeated-clue results.

## Changes

The one FIFO inference worker now collects up to eight already-waiting clues
into a single model request, with no wait to fill a batch. Every clue still uses
a physical admission slot. All returned vectors are checked before applying any
member, then each game scores its own vector against its current board. Expired
and quit games retain their terminal receipts. Wrong response counts or invalid
vectors fail the active batch rather than applying partial results.

Receipt reads advance and expire only the requested session. Creating a game
still sweeps all sessions for retention. Request schemas are loaded and their
validators constructed once per service instead of reading policy files for
each POST. The five-second inference deadline and eight-outstanding-request
bound are unchanged. Full model identity checks surround each batch.

Batch embedding headers report the full call duration for each member, not an
amortized per-clue duration. The worker does not cache or deduplicate clues.

## Comparable small-pack repeat

Same 40-entry content pilot, real pinned model, three rounds per player, 10 ms
polling and restricted Python network policy; no concurrent verifier.

| Players | Original p95 all receipts | Refined p95 all receipts | Refined outcomes |
| --- | --- | --- | --- |
| 1 | 353 ms | 387 ms | 3 semantic results |
| 4 | 2,174 ms | 1,406 ms | 12 semantic results |
| 8 | 5,418 ms | 2,586 ms | 23 semantic results, 1 stale revision, zero inference timeouts |

The original eight-player run had 7/24 inference timeouts. The refined run's
stale revision is retained as a real rejection when the board changes before
submission, not counted as a successful semantic result. Single-player latency
did not improve. These are small before/after observations, not controlled remote
host isolation or a reliable population p95 estimate.

[Refined raw results](feasibility-2026-11-14/refined-run/startup.json) and
[resources](feasibility-2026-11-14/refined-run/resources.json) preserve every receipt.
Peak local working set was 98.28 MiB (original 111.41 MiB). Pilot semantic
verification still reached all 40 targets. No threshold or content was tuned.

## Verification contention

The first pressure run used the existing 90-entry game artifact and 60-entry
held-out verifier manifest, five rounds per player, real verifier adapter overlap.
It passed 5/5, 20/20 and 40/40 semantic results at 1/4/8 players, without timeout,
stale-revision or transport failures. Round-trip p95 was 464 / 1,441 / 1,979 ms.
Independent fresh reference/core processes passed 900 rank cases. The Python
regression suite overlapped part of this initial run, so a longer repeat without
that competing local workload is recorded separately below. These pressure runs
use different content and counts from the small-pack before/after comparison.

Raw [pressure results](feasibility-2026-11-14/refined-pressure/load.json) and
[parity](feasibility-2026-11-14/refined-pressure/parity.json) retain the measurements.
Neither probe completion nor zero timeouts establishes the 100 ms target.

## Longer controlled repeat

After the Python suite finished, the same pressure runner was repeated with ten
rounds per player. No other test workload was launched during this run; external
model-host activity was not controlled. Independent parity again passed 900 cases.

| Players | Requested / recorded | Semantic results | Stale revision | Inference timeouts | p95 successful round trips |
| --- | --- | --- | --- | --- | --- |
| 1 | 10 / 10 | 10 | 0 | 0 | 1,633 ms |
| 4 | 40 / 40 | 38 | 2 | 0 | 2,420 ms |
| 8 | 80 / 80 | 75 | 5 | 0 | 3,148 ms |

Real verifier adapter calls overlapped 9/10, 37/38 and 75/75 successful samples.
The runner correctly reports `passed: false` because stale-revision commands
remain unsuccessful attempts. They are not silently retried or excluded from
requested/recorded counts. The reported p95 in this table includes successful
semantic results only, unlike the small-pack all-receipts comparison above.
The eight-player successful maximum was 3,318 ms; adapter batch p95 was 1,353 ms.
The higher latency than the first short pressure run demonstrates variability,
so the short-run values must not be treated as a stable performance guarantee.

[Repeat load report](feasibility-2026-11-14/refined-pressure-repeat/load.json),
[parity](feasibility-2026-11-14/refined-pressure-repeat/parity.json), and
[metadata/source hashes](feasibility-2026-11-14/refined-pressure-repeat/metadata.json)
retain the evidence. Bounded inference-timeout regression is resolved in these
runs; overall acceptance remains failed. Accepting a stale expected revision or
raising deadlines would alter the safety/behavior contract rather than resolve
inference latency, so neither was done.

## Validation and remaining boundary

199 Python tests and six client tests passed; repository Ruff lint and formatting
passed. New tests cover queued batch order and distinct vector mapping, truncated
batch response rejection, slot release, and unrelated-session polling isolation.
The existing timeout/retention test now waits for the first model call to enter
before queueing the remaining work, making its skipped-job assertion deterministic
under batching. Existing replay, immutable receipts, retry and timeout precedence
checks remain in the suite.

The 100 ms p95 target remains unmet. Model adapter batch times alone exceeded it
in the pressure run; local queue changes do not establish that target for this
pinned remote model. Full remote-host offline isolation/resources, independent
human content review and population sourcing yield remain unverified. Stage 1
stays open. No remote model/runtime configuration was changed.
