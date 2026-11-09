# Stage 1 / Wave 2 evidence and contract drafts

Status: **running**. Authorized and dispatched November 8, 2026
(America/New_York), after [PR #1](https://github.com/JohnnnyTang/Semaphore/pull/1)
merged with all hosted checks passing.

Common worker baseline: `80ebde2bec2289002f9bd58c6e131ad8627dc9d8`.
Coordinator branch: `codex/s1-w2-integration`.

| Session | Branch / local worktree | Owned outputs | State |
| --- | --- | --- | --- |
| B: semantic evidence | `codex/s1-w2-b-model-evaluation` / `.worktrees/w2-model-evaluation` | Model harness, semantic fixtures, model/content evidence | running |
| C: gameplay and interaction | `codex/s1-w2-c-gameplay` / `.worktrees/w2-gameplay` | Gameplay/interaction drafts, game traces | running |
| D: platform and creator | `codex/s1-w2-d-contracts` / `.worktrees/w2-contracts` | Draft schemas/storage/API, manifest fixtures, creator journey | running |

The coordinator owns root dependencies, CI, integration and this record. Workers
consume the same W1 baseline and cannot import one another's unmerged outputs.
See the [session briefs](s1-w2-session-briefs.md) for acceptance requirements.

## Dependency and measurement setup

- JSON Schema validation joins the development group. Real-model libraries use
  an opt-in `model-eval` group; PyTorch comes from its explicit CPU wheel index.
  The default development install does not download the model runtime or weights.
- The lock records exact package versions. Model repository revisions and
  encoding modes belong in B's experiment configuration, not a production pin.
- Host inventory obtained through Windows CIM: Intel Core Ultra 7 258V, 8 cores /
  8 logical processors; 33,796,481,024 bytes physical RAM (~31.48 GiB);
  Windows 11 Home Chinese, build 10.0.26300, x64. This is the development host,
  not validation of the proposed 8 GB server envelope.
- No remote model code is authorized by default. Model weights and download
  caches remain ignored. Measurements must distinguish offline fixture tests,
  actual model results, simulated load and human play evidence.

## Review gate

W3 has not started. Integrating draft code does not settle model selection,
quality thresholds, fairness reconciliation or owner-dependent policies.
Missing model runs must remain explicit; no benchmark result may be inferred
from a fake ranker. The coordinator records checks, commits and open gates here
when the three sessions return.
