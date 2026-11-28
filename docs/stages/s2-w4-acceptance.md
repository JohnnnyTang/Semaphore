# Stage 2 W4 — Product acceptance

Latest November 16 correction: keep-alive model transport and stale-clue draft
recovery are implemented. Final isolated 1/4/8-player p95: **329/641/735 ms**,
with two eight-player stale rejections; all restart checks passed. Validation:
487 Python tests, 27 Node tests, lint/format/build/diff passed. **W4 remains open**:
100 ms target unmet; offline startup remains explicitly deferred; inherited
reference-resource and human/content gates remain unfulfilled. See the
[latest correction](../evidence/s2-w4-performance-correction.md#latest-correction--persistent-model-transport).
Earlier measurements below remain historical evidence.


November 16, 2026. State: revise within W4 after real-model measurement; Stage 2 acceptance is not complete.

The owner requested starting W4 using parallel subagents. W3's completed local
changes were preserved at common baseline
`871184892bfa6e4f9a007060394463a797b0097e`; the baseline regression passed 464 tests.
Coordinator branch: `codex/s2-w4-integration`.

## Parallel assignments

All workers start from the same baseline in isolated ignored worktrees.

| Worker | Owned paths | Assignment |
| --- | --- | --- |
| Browser | `web/`, `tests/web/`, `docs/evidence/s2-w4-browser.md` | Check real API compatibility, fix browser behavior and add regression evidence |
| Probes | `experiments/durable_acceptance/`, `tests/hub/acceptance/`, `docs/evidence/s2-w4-probes.md` | Runnable authenticated HTTP acceptance/load tooling with explicit sample/error reporting |
| Operations | `tests/hub/operations/`, `docs/operations/durable-hub.md`, `docs/evidence/s2-w4-operations.md` | Fresh installation, migration, recovery/deletion/restore acceptance and runbook |

Coordinator owns shared host/API composition, CLI, dependencies/contracts and
stage reporting. Model pressure runs are serialized and must be labeled separately
from synthetic inference. Workers do not import peers' unmerged code.

## First integration slice

The durable listener previously served only JSON APIs. An explicit
`serve-durable --web-root web` option now loads a bounded allowlist of browser
assets and serves `/web/durable.html` on the API's origin. `/` redirects there.
Loading the sign-in page requires no account; exact Host/Origin checks still apply.
Unknown paths never expose repository files, operator keys or runtime data.
Missing required assets fail before binding. API-only operation remains available
when the option is omitted. The listener continues to bind IPv4 loopback.

## Open acceptance

Signed-in human real-model browser completion and result retrieval after restart,
controlled real-model 1/4/8-player load with verifier overlap, resource/remote-host
offline evidence and independent content review remain open. Automated or synthetic
runs cannot close those gates. The inherited p95 <=100 ms target is unchanged.
No Stage 3 dispatch or release-readiness claim is authorized by this work.

## Integrated helpers

- Browser `b2d0ff6` plus `e117f79`: corrected authoritative clear-zone ranks,
  cryptographic command IDs on LAN HTTP, self-navigation and backup-retention
  disclosure; added actual-service browser acceptance flow.
- Probes `2afc214`: authenticated HTTP 1/4/8-player runner, bounded receipts,
  exact retries, sample/failure retention and p50/p95. It does not assert verified
  model execution, verifier overlap or resource acceptance.
- Operations `88a4de6`: subprocess CLI migration/upgrade, deletion-aware restore,
  overwrite/lock/missing-ledger checks and fresh operator setup instructions.

All helpers are reviewed and integrated locally. The actual-service browser flow
passed using synthetic inference; see [browser evidence](../evidence/s2-w4-browser.md).
The coordinator corrected runbook code-block formatting during integration.
W4 remains running until its real-model/human and inherited acceptance is resolved.

## Integration validation

- Full Python regression: **476 passed**.
- Node browser regression: **25 passed**.
- Ruff lint and formatting: passed (198 files checked for formatting).
- Source distribution and wheel build: passed.
- Actual-service Edge browser flow: passed with synthetic inference, including
  a successful `miss` receipt and natural zero-score history/board result.
- Diff whitespace: passed. No changes pushed.

This is completion of the first W4 integration slice, not closure of W4 or Stage 2.


## Continued acceptance — November 16

Three isolated helpers continued from `b7f686a`: real-model/load/restart orchestration,
fresh locked/installed-wheel verification, and human/restart browser evidence.
All are integrated locally. The owner supplied the model endpoint and completed
a real round (1,000 points, level 3, pack_exhausted), then confirmed the unchanged
result and board after process restart. Signup validation was corrected after
the owner encountered invalid_request. Polling is now guarded at 250 ms.

Fresh locked install, independent installed-wheel resources, supported migrations
and cached-offline checks passed. Real-model 1/4/8 cohorts with verifier overlap
produced successful-command p95 of 625/1,344/2,406 ms; the eight-player cohort
had 12 stale-revision rejections among 40 measured commands. Automated natural
result/one-score persistence and active-game interruption after restart passed.
The CPU/RSS samples captured a Windows launcher and are explicitly invalid for
hub resource claims. Remote model resources/offline operation remain unmeasured.

Decision: revise within W4; preserve the 100 ms target and correct revision
semantics. No Stage 3 dispatch. See [current report](../evidence/stage-2-report.md),
[human evidence](../evidence/s2-w4-human-playtest.md),
[installation evidence](../evidence/s2-w4-installation.md) and
[real-model results](../evidence/s2-w4-real-results.json).
Validation before the resource-sampler correction: 482 Python and 27 Node tests,
lint/format and wheel/source build passed.

The Windows resource sampler was corrected in `eed4531` to include interpreter
children; thirteen focused tests passed after integration, plus lint/format/diff.
Read-only idle process-tree validation confirms selection of the real interpreter.
No second load was run solely to replace that instrumentation failure; valid
load-time resources remain part of the next performance correction run.


## Performance/resource follow-up — November 16

Clock-only GET/tick no longer rewrites durable game snapshots. Full regression:
484 Python tests and 27 Node tests passed; lint/format/diff checks passed. Two
controlled reruns retained all failures; the repeat p95 was 610/906/1,484 ms for
1/4/8 players, with four eight-player stale-revision rejections. Restart checks
passed. Local and remote model process-tree/GPU measurements are now retained,
with sampling limitations; resource-envelope acceptance is not declared. The user
explicitly deferred remote offline startup. W4 remains open with the unchanged
100 ms target. See [correction evidence](../evidence/s2-w4-performance-correction.md)
for source hashes, results, resource scope, and next work.
