# W4 performance correction and resource follow-up

November 16, 2026. W4 remains open; the 100 ms p95 gate is unchanged.

## Latest correction — persistent model transport

November 16, 2026. **W4 acceptance remains open.** The owner requested completion;
no performance waiver or reversal of the offline-test deferral was inferred.

The Ollama adapter now uses a single bounded, serialized direct HTTP(S) connection
per embedder. It reuses keep-alive connections, avoids system proxy discovery,
retains default HTTPS certificate verification and request timeouts, bounds response
bytes, rejects redirects, and does not retry uncertain requests. Error paths discard
the connection; a later explicit request can open a new one. All pre/post frozen
identity checks remain in place. Isolated warm pinned-query observations reached
18-19 ms, but that is not verifier-overlap acceptance.

A stale-command rejection now preserves the browser's clue draft and explains that
the board changed. No command is automatically rebased or resubmitted. A deterministic
service test advances a scheduled spawn between the displayed snapshot and command:
the old revision is rejected without inference, exact retry keeps its original receipt,
and an explicit new command at the current revision is accepted. This establishes
correct rejection/recovery behavior; it does not remove stale outcomes from load counts.

Final isolated [run 6](s2-w4-correction-run-6.json), same five measured commands plus
one warmup per player, with real verifier overlap in every cohort:

| Players | Successful / planned | p50 | p95 | Failed outcomes |
| --- | --- | --- | --- | --- |
| 1 | 5 / 5 | 203 ms | 329 ms | 0 |
| 4 | 20 / 20 | 422 ms | 641 ms | 0 |
| 8 | 38 / 40 | 437 ms | 735 ms | 2 stale_revision |

All natural-result/history/one-score and active-interruption restart checks passed.
The runner correctly exited nonzero for incomplete load. Game embedding wrapper
calls ranged 18-375 ms (median 119 ms) under verification pressure; verifier calls
had median 235 ms. These wrapper timings are not pure GPU compute or isolated queue
measurements. The 100 ms end-to-end target remains failed. Peak sampled hub RSS was
248,520,704 bytes; ten process-read errors and restart sampling limits are retained.
Remote run-3 measurements are historical and not represented as run-6 measurements.

[Run 4](s2-w4-correction-run-4.json) is an intermediate per-request transport run;
source edits overlapped process execution, so it is excluded from final acceptance.
[Run 5](s2-w4-correction-run-5.json) is diagnostic only because local regression work
briefly overlapped early runtime. Neither is discarded or presented as a clean
acceptance pass. Run 6 had stable source and no concurrent regression workload;
all changed runtime file hashes and the base commit are retained.

Final checks: **487 Python tests, 27 Node tests, Ruff lint/format, source/wheel build,
and diff whitespace passed**. Regression ran after final model traffic stopped.
No remote firewall/startup changes or additional remote-host sampling were performed.
All acceptance subprocesses ended. Changes remain local and uncommitted.

### Remaining acceptance work

- Performance: shared-model contention still exceeds the unchanged 100 ms target.
  A follow-up needs explicit query/verification scheduling and queue-level timing,
  followed by the same unmodified success/failure accounting. Removing identity
  checks, hiding stale rejections, or reporting isolated warm timing is not closure.
- Stale revisions: safe rejection and explicit recovery are verified; scheduled-load
  cohorts still contain rejected commands and therefore do not pass the all-success gate.
- Remote offline startup: deferred by the owner's explicit instruction; not executed.
- Reference resources: GPU-host samples exist, but CPU-only/8 GB reference-host
  feasibility is not established by this machine or sampled peaks.
- Broader human/content review and source-yield study: inherited gates remain open;
  one owner round and automated review cannot substitute for the required observations.

No Stage 3 dispatch or release-readiness claim. These are concrete remaining gates,
not permission to silently close W4 as accepted.

## Earlier polling correction

## Change and validation

Clock-only game polling and scheduler advancement now update the live elapsed-time
projection without rewriting SQLite snapshots. Actual reducer transitions still
persist before acknowledgment, including terminal results and settled receipts.
Active games are interrupted on recovery, so elapsed-only updates do not need
restart replay. Exact expected-revision admission and immutable retries are unchanged.
A regression checks that clock-only GET/tick leaves the stored snapshot unchanged
and a terminal tick still commits exactly one score.

Validation: 484 Python tests, 27 Node tests, Ruff lint/format, and diff checks passed.
The measurements used base `f6a8a9bb3861b9363523f2068a3d0eab430527ca` plus this
uncommitted service change. Evidence records the service-file SHA256, rather than
claiming that the base commit alone produced these results. Nothing was pushed.

## Controlled reruns

Same manifest, configuration, clues, five measured commands per player, one warmup,
pinned model, and concurrent verifier as the original run. Separate fresh disposable
installations were used. Successful-command p95 excludes failed commands.

| Run | 1 player success / p95 | 4 players success / p95 | 8 players success / p95 |
| --- | --- | --- | --- |
| Original | 5/5 / 625 ms | 20/20 / 1,344 ms | 28/40 / 2,406 ms |
| Correction 2 | 5/5 / 578 ms | 19/20 / 1,047 ms | 37/40 / 1,500 ms |
| Correction 3 | 5/5 / 610 ms | 20/20 / 906 ms | 36/40 / 1,484 ms |

All failures in the new cohorts were stale_revision. These remain failures; the
runner did not rewrite expected revisions or silently retry them as new commands.
Scheduled board changes can invalidate a snapshot between GET and POST. This
optimization does not eliminate that race or establish a revision-semantics fix.
Both reruns observed real inference and verifier overlap in every cohort and passed
terminal snapshot/history preservation, exactly-one score, and active-game restart
interruption without a score. The CLI correctly returned failure for incomplete load.
The small diagnostic cohorts show improved multi-player latency, not certification.

Retained results: [run 2](s2-w4-correction-run-2.json),
[run 3](s2-w4-correction-run-3.json). Raw reports remain ignored with hashes retained.

## Latency breakdown

Five isolated synthetic-clue observations without verifier pressure found identity
checks at 48-70 ms, provider query calls at 68-122 ms, and pinned query calls at
168-273 ms. The worker additionally checks identity before and after the pinned
embedder. These are separate sequential measurements, not an additive breakdown
of the controlled run. See [diagnostics](s2-w4-latency-diagnostic.json).
The checks remain intact. Next correction should eliminate redundant checks through
an explicitly guarded embedding interface, with identity-drift regression coverage,
then measure queue/transport/storage separately. No cache or weaker model pin was
introduced to manufacture a sub-100 ms result.

## Resource evidence and limits

The remote host was inspected over authorized SSH: Windows 11 Pro, Ryzen 9 9950X
(32 logical processors), about 32 GB RAM, RTX 5090 (32,607 MiB reported GPU memory).
The model digest matched the frozen identity. Before the first rerun, /api/ps was
empty; this is not a restart/offline proof.

Run 3 collected 321 local process-tree samples, peak summed RSS 258,035,712 bytes
(246 MiB) and cumulative CPU increase 21.11 seconds across collection. Fourteen
process-read errors remain reported; process exit/restart can make collection
incomplete. Shared pages can be counted twice, and short-lived CPU is a lower bound.
These figures do not establish a strict resource-envelope pass.

Remote collection recursively included Ollama and llama-server children: 103 samples
from 07:38:41 to 07:40:31 UTC (15:38:41-15:40:31 Asia/Shanghai), peak summed working
set 888,684,544 bytes (848 MiB), cumulative CPU increase 24.69 seconds, GPU peak
memory 3,026 MiB and peak utilization 91%. There were 3/6/13 remote samples inside
the respective 1/4/8-player cohort intervals by wall-clock comparison. Clock skew
was not independently calibrated. One-second sampling can miss peaks; GPU metrics
are device-wide and CPU/RAM sums are sampled process-tree observations, not a bound.
[Remote raw samples](s2-w4-remote-resources.json) are retained. An initial sampler
omitted llama-server; its CPU/RAM observations are excluded from acceptance evidence.

The user explicitly requested keeping the offline-start test pending. No firewall,
network isolation, or Ollama restart was performed. The temporary resource job and
remote transfer file were removed, the SSH session closed, and disposable load
servers stopped. Cached local installation evidence remains separate.

## Disposition

Continue W4. Open items: 100 ms performance target, stale-revision behavior under
scheduled load, strict resource-envelope assessment, remote offline startup (deferred
by the user), broader human/content review and source-yield evidence. No Stage 3
or release-readiness claim.
