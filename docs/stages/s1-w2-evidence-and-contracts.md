# Stage 1 / Wave 2 evidence and contract drafts

Status: **draft outputs integrated for review; model measurement gate open**.
W2 is not complete. Authorized and dispatched November 8, 2026
(America/New_York), after [PR #1](https://github.com/JohnnnyTang/Semaphore/pull/1)
merged with all hosted checks passing.

Common worker baseline: `80ebde2bec2289002f9bd58c6e131ad8627dc9d8`.
Coordinator branch: `codex/s1-w2-integration`.

| Session | Branch / local worktree | Owned outputs | State |
| --- | --- | --- | --- |
| B: semantic evidence | `codex/s1-w2-b-model-evaluation` / `.worktrees/w2-model-evaluation` | Model harness, semantic fixtures, model/content evidence | harness integrated; measurement gate open |
| C: gameplay and interaction | `codex/s1-w2-c-gameplay` / `.worktrees/w2-gameplay` | Gameplay/interaction drafts, game traces | integrated for W3 review |
| D: platform and creator | `codex/s1-w2-d-contracts` / `.worktrees/w2-contracts` | Draft schemas/storage/API, manifest fixtures, creator journey | integrated for W3 review |

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

B integrated commits: `4a03630`, `68c9d0e`. Coordinator repeated fixture
validation and five benchmark-arithmetic/integrity tests. There are 150 authored
entries, 450 legal clues, 150 illegal controls and 60 held-out targets. The
BGE weight download stalled, then its HTTP fallback disconnected after
84,283,322 of 437,955,512 bytes. No inference ran; GTE/Nomic downloads were
deferred. See [model evidence](../evidence/model-evaluation.md) and its linked
attempt record. This is an open evidence gate, not a failed semantic candidate.

C integrated commit: `dd5b3bbbb017f49a65a8efdb4c5fa74d3019e2e0`.
Coordinator repeated 10 static trace checks (84 expected event states and the
shared-schedule pair) and all seven negative validator tests successfully.
The baseline's eight pytest cases, Ruff checks and package build also passed
after the dependency update. CPU runtime imports succeeded for PyTorch 2.15.0+cpu,
Transformers 5.22.2 and Sentence Transformers 5.7.0; this is compatibility evidence,
not a model benchmark. Cold imports were slow on this host.

A fresh default development environment installed 15 locked packages from the
local cache without the optional model stack. It repeated all eight baseline
tests, 10 game traces, seven game-validator tests and five semantic tests.

Read-only C/D cross-review identified these explicit W3 reconciliation items:

- Wire pending-command state and structured receipts (outcome, original applied
  revision and target rank) must be separate from the current snapshot.
- Map draft status/board/target representations and converge terminal reason
  names; preserve cleared, exhausted, event-complete and interrupted distinctions.
- Freeze revision increments, immediate pending-receipt finalization on game end,
  reconnect/receipt retention and cleanup behavior.
- Reconcile C's capacity-reaching loss at 12 with D's draft board-size ceiling.
- Resolve production lexical expansion, numeric near-ties, calibrated sampling,
  model fingerprint, queue limits and the remaining proposed account/log policies.

These are visible draft differences, not frozen APIs for W4. D fixed the
cross-review finding before integration: schema conditionals reject contradictory
running/terminal states, and fixture semantic checks enforce unique board IDs
and target membership. D integrated commit: `2bce159559276e08e69366307852070ee001cdec`.
Its checker covers four schemas, seven manifest cases, 19 protocol cases,
strict parser boundaries, fixed hash vectors, report/seed isolation and
owner/version retry behavior. CI runs all three sessions' offline checks on
Linux and Windows; hosted results must be checked separately from local evidence.
The coordinator repeated D's complete checker in the clean development environment;
Ruff lint/format, actionlint, whitespace checks and source/wheel build passed on
the integrated tree.

W3 has not started. Integrating draft code does not settle model selection,
quality thresholds, fairness reconciliation or owner-dependent policies.
Missing model runs must remain explicit; no benchmark result may be inferred
from a fake ranker. The coordinator records checks, commits and open gates here
as their outputs are integrated. The next bounded work is to resume the pinned
model downloads and gather the preregistered comparison before W3 freezes a
model or thresholds. Human play and reference-server load remain W5 exit checks.
