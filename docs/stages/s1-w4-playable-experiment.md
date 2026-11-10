# Stage 1 / Wave 4: bounded playable experiment

Started November 10, 2026 (Asia/Shanghai), by owner request with three parallel
GPT-6.1-sol workers at high reasoning effort. Status: **running**.

## Baseline and ownership

All workers start from `bdfa190` (W3 closure). The integration branch is
`codex/s1-w4-integration`. Isolated worktrees are under ignored `.worktrees/`.

| Session | Branch | Owned paths |
| --- | --- | --- |
| F — core and server | `codex/s1-w4-f-core` | `packages/semaphore_core/`, `experiments/game_server/`, `tests/core/`, `tests/game/` |
| G — browser | `codex/s1-w4-g-browser` | `web/`, `tests/web/` |
| H — independent probes | `codex/s1-w4-h-probes` | `experiments/acceptance/`, `tests/contracts/`, `docs/evidence/probe-method.md` |

The coordinator owns root dependencies, shared contracts, integration and this
record. Workers load relevant skills/plugins as needed; G must load the frontend
design skill before implementation. No worker consumes another worker's unmerged
files. Shared-interface changes require coordinator review.

## Scope and acceptance

Follow decision 0004 and the frozen contracts. Both game modes use immutable
finite schedules; legality uses the reviewed English subset. Verification's 0.85
threshold remains diagnostic. This wave adds the callable core, authoritative
reducer, bounded experimental HTTP service, thin browser and independent probe
harnesses. Production accounts, persistence, publishing, adaptive schedules and
full lexical coverage remain outside this wave.

Review each worker commit, run the existing Python quality/fixture checks plus
new component checks, build the package, and exercise cross-component boundaries.
Record actual results below before declaring this wave integrated. Fake-provider
checks prove plumbing, not semantic quality or supported performance. W5 retains
human play and real 1/4/8-player acceptance under verification pressure. The
100 ms Stage 1 target remains unmet.

## Integration evidence

Pending worker delivery and coordinator review.
