# Stage 1 W5 report — acceptance review

November 11, 2026 (Asia/Shanghai). Baseline: `64e3a90`.

## November 14 timeout refinement

FIFO batching of queued clues and isolated session polling reduced eight-player
timeouts to zero in the bounded follow-ups; full identity checks, eight admission
slots and the five-second deadline remain unchanged. See the
[refinement evidence](feasibility-refinement-2026-11-14.md) for exact sample counts,
residual stale-revision observations and pressure repeats. The 100 ms target and
remote-host/human-review gates remain open. Validation: 199 Python and six client
tests, repository lint and formatting passed.

## November 14 hardware/content follow-up

The owner selected the current LAN GPU setup and local-machine measurements.
Restricted Python-process startup passed in 2.772 s; local peak working set was
111.414 MiB. A new 40-target / 120-clue authored pilot passed core hygiene and
real-model reachability (40/40). Eight-player probing still had 7/24 inference
timeouts. Full remote-host offline startup/resources, source-population yield
and independent timed human review remain open. See the
[feasibility report](feasibility-2026-11-14.md) for evidence and limits. These are
bounded closures, not Stage 1 acceptance; historical gate rows below predate them.

## November 14 real-model follow-up

Pinned real-model reference/core parity passed 900 sampled clue cases in each of
two runs. Instrumented 1/4/8-player load with real verifier overlap failed acceptance:
initial one/four-player p95 was 707 / 4,209 ms; the corrected repeat recorded 67
eight-player inference timeouts and only 22/160 requested successful samples.
The repeat preserves partial samples after early game endings. See the
[measurement report](w5-real-model-2026-11-14.md) for component timings, host and
contention caveats, evidence files and validation (191 Python / six client tests).
The 100 ms target remains unmet. Keep Stage 1 open; parity no longer depends on
restoring model connectivity, while performance tuning, human acceptance,
offline/hardware and contract gates remain. Older dispositions below are historical.

## November 12 follow-up

The pinned model is reachable and live browser smoke now passes. Owner-reported
player feedback led to live-mode defaults, countdown interpolation, refill after
sweeps/empty boards and clearing/falling effects. See the
[session evidence](w5-playtest.md#november-12-2026-playtest-correction-session).
Validation now passes 189 Python and seven JavaScript tests, lint/format, and
live browser/mobile/reduced-motion checks. These observations supersede the
model-unavailable status below but do not close full real-model acceptance,
three-person human testing, parity/load, contract or release-hardware gates.
The November 11 assessment below remains the historical baseline.

## Decision

**Revise within Stage 1.** Continue the bounded prototype and acceptance work;
do not declare Stage 1 complete or dispatch Stage 2. This is an engineering gate
disposition, not owner acceptance of changed performance, publication or hardware
targets. W5 work is divided across three GPT-6.1 Sol/high sessions; the [integration record](../stages/s1-w5-acceptance.md) lists their evidence and commits.
See [performance](w5-performance.md), [browser/playtest](w5-playtest.md),
[contract readiness](w5-contract-readiness.md) and
[creator walkthrough](w5-creator-walkthrough.md) for methods and limits.

The integrated wave passes 187 Python tests and seven JavaScript tests, plus
Ruff lint/format and worker Chromium checks. These establish
regression behavior, not real-model latency, human enjoyment or release support.
The previously configured LAN model endpoint refused a bounded connection check.
No real-model result from this wave can be inferred from prior W3 measurements.

## Gate disposition

| Gate | Current evidence and disposition |
| --- | --- |
| Real browser game to authoritative final score | Actual HTTP/synthetic browser run reached a natural end with 800 server points and eight cleared words; W5 live-model acceptance remains open while the model service is unavailable. |
| Deterministic replay, event schedules and retries | All 10 sealed traces (84 events), seven HTTP robustness checks and synthetic 1/4/8-player orchestration passed; see the performance evidence. |
| Independent verification parity | Creator walkthrough reproduced 900 synthetic sample/clue comparisons across fresh reference/core processes; real-model parity remains open. |
| Semantic quality and human feel | Historical synthetic authored/held-out results do not substitute for three-person observations or independent marginal packs. User feedback requested; no answer assumed. |
| Warmed 1/4/8-player p95 under verification pressure | Blocked on live model access. The 100 ms target remains unmet; no synthetic timing establishes acceptance. |
| CPU/RAM and offline startup | GPU LAN development does not establish CPU-only 8 GB support. Fully offline model/assets startup and reference-host utilization remain unproven. |
| Contracts ready for independent Stage 2 work | Not ready: default paced casual and verifier ruleset identities disagree; promoted and draft storage identities need reconciliation. See contract review for further gaps. |
| Content feasibility | Source risks and editorial estimates exist; rights-cleared yield and timed authoring pilot are not completed. No 3,000–5,000-entry yield claim is supported. |
| Creator journey | Shared-core walkthrough only. Finished CLI, independent installation, upload and publication acceptance are later deliverables. |

## Bounded correction work before reassessing the gate

1. Restore access to the already selected pinned model, then run real parity and
   browser acceptance plus 1/4/8-player load with genuine verifier inference
   overlap. Record sample counts, failures, polling, hardware and model identity.
2. Reconcile verification-policy identity with paced casual gameplay identity;
   decide and test the versioned relationship rather than relabel existing reports.
   Freeze one public pack-ID/ownership contract before writing storage migrations.
3. Run short human sessions with at least three people using the playtest protocol.
   Capture confusion and observed outcomes without committing private raw clues.
4. Record actual offline startup and resource measurements on the intended
   supported hardware. Preserve the explicit unmet target until new evidence or
   an owner-approved target/scope decision changes its disposition.
5. Complete the rights-cleared content yield/review-cost pilot and close the
   implementation-critical account, retention, error and scale contracts identified
   in the readiness review before dispatching dependent Stage 2 sessions.

Stage 2 is deliberately not expanded into implementation waves while these Stage 1
gates remain open. The existing stage map remains the longer-term product outline.
