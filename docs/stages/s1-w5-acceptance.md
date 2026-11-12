# Stage 1 / Wave 5: acceptance and gate review

Started November 11, 2026 (Asia/Shanghai), at the owner's request using three
parallel GPT-6.1 Sol agents with high reasoning effort. Status: bounded work integrated locally; Stage 1 acceptance remains open.

## Baseline and ownership

All sessions start from merged `64e3a90`, including the tutorial, visual feedback,
paced casual streak and cascade refinements. Coordinator branch:
`codex/s1-w5-integration`. Worker branches are isolated under ignored `.worktrees/`.

| Session | Branch | Owned paths |
| --- | --- | --- |
| A — real-model performance and parity | `codex/s1-w5-a-performance` | `experiments/acceptance/`, `tests/contracts/`, `docs/evidence/w5-performance.md` |
| B — browser acceptance and playtest preparation | `codex/s1-w5-b-playtest` | `web/`, `tests/web/`, `docs/evidence/w5-playtest.md` |
| C — contract readiness and independent creator walkthrough | `codex/s1-w5-c-gate-review` | `docs/evidence/w5-contract-readiness.md`, `docs/evidence/w5-creator-walkthrough.md` |

The coordinator owns shared contracts, dependencies, integration fixes, this record,
the project plan and Stage 1 report. Workers consume the shared baseline only.
Model-service pressure runs and browser checks must be coordinated to avoid
contaminating measurements. No Stage 2 implementation is dispatched.

## Acceptance boundary

W5 gathers real HTTP/model evidence, deterministic replay and verification parity,
browser behavior, contract readiness and a proposed creator-journey walkthrough.
Automated browser checks are not human playtesting; a shared-core walkthrough is
not finished creator CLI acceptance. GPU LAN results do not establish CPU-only
8 GB release support. Offline startup requires evidence rather than inference.
The p95 100 ms target and at least three-person feel review remain explicit gates.

## Integrated handoffs

| Session | Worker commit | Integration commit | Evidence |
| --- | --- | --- | --- |
| A | `cfe967e` | `5b4f993` | [Performance and parity](../evidence/w5-performance.md) |
| B | `d38be83` | `32ad298` | [Browser and human protocol](../evidence/w5-playtest.md) |
| C | `96cffd2` | `582288c` | [Readiness](../evidence/w5-contract-readiness.md), [creator walkthrough](../evidence/w5-creator-walkthrough.md) |

Session A also owns the probe-method documentation update. Coordinator commit
`fd07833` records dispatch and reconciles existing paced casual documentation.
No dependency or model lock changed. Worker commits are retained in their clean
worktrees; no merge into main or push is included in this wave.

## Findings and decision

The probe now requires overlapping pinned verifier adapter calls for real-model
pressure evidence, with explicit synthetic timing suppression and environment-based
model configuration. Browser fixes preserve completed warm-up state after failed
server creation, keep contextual typing notes stable across polls, and count swept
words correctly in the ending. Regression scripts explicitly select warm-up behavior.

Independent evidence passed 10 traces / 84 events, 900 synthetic rank comparisons,
six pre-embedding invalid-manifest checks, seven HTTP robustness checks, and
3/12/24 successful synthetic clue samples at 1/4/8 players with verifier subprocess
work. Chromium completed an actual HTTP/synthetic game with 800 authoritative points,
eight cleared words and a natural ending, plus recovery/mobile/reduced-motion checks.

The real model endpoint refused the bounded connection check. Live parity/load,
CPU/RAM and real offline startup remain unmeasured. Zero human playtest sessions
were recorded. The ruleset/verifier mismatch and storage namespace contradiction
are reproduced readiness issues. See the [Stage 1 report](../evidence/stage-1-report.md):
**revise within Stage 1**, retain the unmet 100 ms target, and do not dispatch Stage 2.

## Integrated validation

- Python: **187 passed** (25.41 seconds).
- Node browser state/transport/tutorial: **7 passed**.
- Ruff lint and formatting pass; Git diff check passes.
- Worker Chromium checks passed as detailed above; actual-model browser behavior
  and physical mobile/assistive technology remain unverified.

The coordinator formatted the creator walkthrough's Python snippet to satisfy the
repository formatter. Hosted CI has not been run for these local commits.
