# Stage 2 W4 — Product acceptance

November 16, 2026. State: running; Stage 2 acceptance is not complete.

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
