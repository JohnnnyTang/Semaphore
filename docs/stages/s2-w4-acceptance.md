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
