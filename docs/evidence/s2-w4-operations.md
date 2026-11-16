# Stage 2 W4 operator acceptance

November 16, 2026 (Asia/Shanghai). Baseline:
`871184892bfa6e4f9a007060394463a797b0097e`.
Worker branch: `codex/s2-w4-operations`.

## Implemented and observed

`tests/hub/operations/test_cli_acceptance.py` exercises the public module CLI with
fresh temporary databases and random temporary keys on Windows/Python 3.12:

- Empty database migration, real account bootstrap, encrypted backup, clue deletion,
  account deletion, cleanup and restore. The restored account remains anonymized,
  its credentials remain erased, sessions are absent, and SQLite integrity/FKs pass.
  A second restore into the same destination fails without changing its bytes.
- The shipped v1 migration upgrades to v2, preserving an account without publishing
  old content. Repeated migration is safe; altered migration checksums fail.
- A held live-host process lock rejects maintenance. A missing external ledger
  rejects backup without recreating the ledger or publishing a snapshot.

Migration and durable operator commands execute in separate Python processes.
Bootstrap executes the real CLI `main` in-process with only `getpass` replaced:
Windows `getpass` reads the console even with piped stdin, so the initial attempt
at piping a test password timed out. No production password-input behavior changed.
The bootstrap assertion checks that the supplied synthetic password is not printed.

Run from the repository root:

```powershell
uv run --no-sync pytest -q tests/hub/operations/test_cli_acceptance.py
```

Observed result: **3 passed** in 5.03 seconds. Ruff lint and formatting pass for
the new file. The worker used the existing root `.venv` interpreter with its own
worktree `packages` on `PYTHONPATH`; this is not a fresh dependency installation.
No model endpoint was contacted. No keys or databases are committed.

The [runbook](../operations/durable-hub.md#fresh-local-acceptance-setup-powershell)
now includes a no-overwrite secret provisioning example, common PowerShell CLI
arguments, operator bootstrap, supported upgrade boundary, pack/artifact prerequisites,
same-origin browser launch and a disposable-account restore drill. The `--web-root`
option is coordinator-owned W4 integration and must be merged before using that
launch command.

## Remaining gates

These empty/account-only CLI checks complement existing populated-game recovery,
asset-readiness and subprocess crash probes. They do not establish real-model
completed-score persistence, human signed-in acceptance, full locked fresh/offline
installation, LAN listener access, remote-host resources, or 1/4/8-player model
performance. Those W4 and inherited Stage 1 gates remain open. No Stage 3 dispatch
or release-readiness claim follows from this evidence.
