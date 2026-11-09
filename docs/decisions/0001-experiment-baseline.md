# Experiment baseline decisions

Recorded November 8, 2026 for Stage 1 / Wave 1. This ledger supplements the
[project plan](../../PROJECT_PLAN.md); it does not freeze Wave 3 contracts.

## Authority and confirmed scope

The handoff defines the product, with the owner clarifications recorded in the
project plan taking precedence. The owner's subsequent request to set up GitHub
Actions and begin the first wave authorizes this setup work. The plan's earlier
statement that planning alone did not authorize implementation remains historical.

| Confirmed | Consequence |
| --- | --- |
| English Arcade game, LAN server, thin browser clients | The server owns ranking, time, state and score; runtime play requires no internet. |
| Embeddings only on the server; no server-side LLM | Creator agents remain separate from hosting and gameplay. |
| Lightweight local accounts | Use local username/password identity; device tokens alone do not satisfy the clarified scope. No email or OAuth. |
| Versioned packs and leaderboards; hub re-verification | Self-reported reports and provenance never establish verification or score authority. |
| Target 6–8 concurrent players, CPU-only, initial 8 GB envelope | These are benchmark targets, not demonstrated minimum requirements. |
| Persist private clue logs for later feedback | This does not authorize creator access or public exports of raw participant clues. |

## Engineering choices for the baseline

| Choice | Status and rationale |
| --- | --- |
| CPython 3.12, one uv-managed project and committed lock | W1 selection, pending integrated install/build verification. Keep the baseline small; confirm candidate model dependencies in W2 before expanding it. |
| pytest and Ruff | W1 checks for behavior, lint and formatting. The dependency lock records exact versions. |
| Fake ranker and synthetic fixtures | Setup tools only. Their outputs establish deterministic plumbing, not semantic quality, real-model parity or performance. Their interface remains provisional until W3. |
| Vanilla HTML/CSS/JavaScript for the first browser experiment | W1 scope choice: minimize setup for the small experiment. Reconsider Preact at W3 if W2 interaction requirements justify it; no frontend scaffold or dependency is needed in W1. |
| One coordinator and three bounded W1 workers | Runtime, CI and documentation start at the same commit in separate worktrees. Root dependencies are delegated to the runtime worker for W1 only. The coordinator reviews and integrates all outputs. |

Linux/Windows CI coverage, where configured, checks the scaffold on hosted
runners. It does not certify the eventual embedding stack or a supported server
operating system. Installing dependencies can require internet; offline runtime
and offline distribution are separate later acceptance checks.

## Proposals still requiring evidence or review

The following are working proposals from the plan, not additional owner approvals:

| Topic | Working proposal | Resolution |
| --- | --- | --- |
| Signup and publication | Open local signup; signed-in users publish; only the owner adds versions | W2-D draft, W3 review |
| Administration | Operator bootstrap and password reset; no web self-promotion | W2-D draft, W3 review |
| Private logs | Accepted/rejected attempts; configurable 30-day default; no creator raw-clue API in v1 | W2-D privacy contract, W3 review |
| Events and history | Admin-started events; permanent version/event histories | W2-C fairness draft, W3 review |
| Content rights | Explicit license/rights statement; no automatic default grant | W2-D format proposal plus W2-B source evidence |
| Model and encoding | Evaluate BGE base, GTE base and Nomic; none selected | W2-B evidence, W3 model pin |
| Rules and thresholds | Plan values are initial tunables, including target-only clear and numeric tie policy | W2-C traces plus W2-B calibration, W3 freeze |
| Offline creator delivery | Operator-prepared dependency/model bundle | Later distribution work; do not claim W1 provides it |

## Benchmark environment status

This checkout is being prepared on Windows with Git `2.52.0.windows.1` and uv
`0.9.18`, observed during W1. Attempts to inspect CPU, RAM and OS details with
`Get-CimInstance` were denied by the execution environment. The reference LAN
host is therefore **not recorded or validated**. No inference, load or gameplay
measurement was performed as part of this documentation session.

Each W2 benchmark must record CPU model, physical/logical cores, OS/version,
available RAM, thread counts, Python/runtime/package versions, model revision,
encoding mode and run command alongside results. Distinguish the actual measured
host from the initial 8 GB target. Report unavailable measurements explicitly;
neither fake-ranker timings nor hosted CI timings establish the game's latency.

## Data handling

- Commit only synthetic fixtures, redistributable public content with recorded
  provenance, benchmark code, and reviewed aggregate evidence. Public availability
  alone is not proof of redistribution rights.
- Keep model weights, downloaded datasets, vector caches and private runtime data
  outside tracked paths. Use the ignored model/cache/data directories or an
  explicitly documented external path; do not force-add ignored artifacts.
- Never commit credentials, account records or raw participant clue logs. Synthetic
  clues must be labeled as synthetic; pseudonymous participant data is not anonymous.
- Keep calibration and held-out examples separate before model/threshold tuning.
  Preserve their split and record any leakage or later changes.
- Record fixture source, authorship, rights, transformation and purpose. A small
  experiment fixture is not automatically a valid publication pack.
- Reports label measured, simulated and unmeasured claims separately. A failed
  gate remains open; missing human playtests cannot be replaced with synthetic play.
