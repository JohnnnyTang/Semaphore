# Stage 1 W5 report — acceptance review

November 11, 2026 (Asia/Shanghai). Baseline: `64e3a90`.

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
