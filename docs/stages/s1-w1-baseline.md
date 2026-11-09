# Stage 1 / Wave 1 baseline record

Status: **integrated on `codex/s1-w1-baseline`; local acceptance passed**.
Date: November 8, 2026.
Starting commit: `ce05b9c7778d5a79681ede0318c36ee544fd6196`.

The owner requested GitHub Actions setup and the first wave with parallel agents
in worktrees. W1 remains the setup wave in the [project plan](../../PROJECT_PLAN.md),
split into three disjoint assignments; this does not start W2 model evaluation or
gameplay implementation.

| Worker | Branch / worktree | Owned output |
| --- | --- | --- |
| Runtime | `codex/s1-w1-runtime` / `.worktrees/w1-runtime` | Python metadata/lock, skeleton core package, smoke tests and fixture guidance |
| CI | `codex/s1-w1-actions` / `.worktrees/w1-actions` | `.github/` workflows and dependency update configuration; any dedicated workflow validation scripts |
| Decisions | `codex/s1-w1-decisions` / `.worktrees/w1-decisions` | `docs/decisions/`, `docs/stages/` |

The coordinator owns root README/plan updates, integration and the final baseline.
The runtime worker has the coordinator's explicit W1 delegation for root dependency
files. Worktrees live inside the ignored `.worktrees/` directory so all writes stay
inside the authorized repository workspace. Each worker starts at the recorded
commit and returns commits, owned paths, checks and unresolved issues.

## Integration acceptance

Before advancing the wave, the coordinator records evidence for:

- [x] Runtime, CI and documentation changes reviewed and integrated.
- [x] A fresh worktree installs the recorded dependency set with `uv sync --locked --group dev`.
- [x] Installed package import and meaningful fake-ranker smoke tests pass.
- [x] Ruff lint and format checks pass against the integrated baseline.
- [x] A package build succeeds using the recorded build dependency strategy.
- [x] Workflow syntax/action references checked; distinguish local validation from an actual GitHub run.
- [x] [Decision ledger](../decisions/0001-experiment-baseline.md) matches the selected runtime and observed checks.
- [x] [W2 briefs](s1-w2-session-briefs.md) have disjoint ownership and adequate inputs.
- [x] Integrated baseline commit and any remaining limitations recorded below.

Integrated code baseline: `a864232` (runtime, CI and decisions), followed by the
coordinator's documentation/line-ending commit on `codex/s1-w1-baseline`. Record
the final reviewed branch tip when dispatching W2; it has not been dispatched.

Local evidence on Windows / CPython 3.12.12 / uv 0.9.18:

- Locked sync, Ruff lint/format and all **8 pytest cases passed**.
- `uv build --no-build-isolation` produced the source distribution and wheel;
  the runtime worker separately installed the wheel and checked an isolated import.
- A clean detached worktree at `a864232` repeated locked install, all 8 tests,
  package build and actionlint 1.7.12. The install reused downloaded cache offline;
  this is scaffold evidence, not offline game acceptance.
- Local sandbox restrictions required an in-workspace `UV_CACHE_DIR` and elevated
  dependency access. A partially interrupted environment was replaced with a
  fresh verification environment using `--link-mode copy`.
- Hosted Linux/Windows checks are tracked in the branch's GitHub Actions runs;
  local success alone does not assert that hosted checks passed.

GitHub Actions is enabled with read-only default workflow permissions. `main`
currently has no branch protection. Dependabot becomes active when its configuration
lands on the default branch; no deployment or release publishing is configured.

W1 excludes model choice, model weights, full application scaffolding, auth,
production contracts and claimed benchmark results. The reference hardware gap is
recorded in the decision ledger and must be closed before performance conclusions.

## Handoff to the next wave

Once the checklist passes, create B/C/D worktrees from the same recorded integrated
commit. Do not depend on another W2 session's unmerged files. Root dependencies,
shared contracts and decisions stay with the coordinator. Changes needed by another
session go through integration, followed by an explicitly updated common baseline.
W3 reconciles the three outputs before any W4 implementation uses them.
