# Stage 1 / Wave 3: experiment contract reconciliation

Started November 9, 2026 (America/New_York), by owner authorization to check
LAN Ollama and start the next wave with parallel GPT-6.1 Sol agents at medium
reasoning effort.

## Verified prerequisite and common baseline

Direct access to the owner-provided Ollama endpoint succeeded. The system proxy
path returned HTTP 502; direct `/api/tags` returned HTTP 200. The existing
`ollama_eval check` then successfully validated real query and entry embeddings.
The development adapter already bypasses environment proxies.

- Model: `qwen3-embedding:4b`, GGUF Q4_K_M, 2,560 dimensions.
- Artifact digest: `df5bd2e3c74cd8d069d21dc038f1b359fcdc9458fce1c99bd43c9eb1518ff907`.
- Reported Ollama version: `0.40.15`.
- `/api/ps` reported 2,647,539,056 bytes for both model size and VRAM size.
  This is service-reported allocation, not independent GPU/driver validation.
- Owner-reported server: NVIDIA 5090, 32 GB VRAM, Windows, NVIDIA driver
  610.88. Exact Windows version/build and independent hardware inspection remain
  unavailable. This is distinct from the Windows client benchmark environment.
- Local diagnostic: ignored `data/ollama/check-20261109.json`; sample cosines
  are connectivity diagnostics, not a semantic-quality pass.
- Prepared adapter/evaluator baseline: `fee011df94ce06afb5e207ac7017b436b6f9ea7c`.
  All workers begin from this commit in isolated worktrees.

The baseline passes 56 pytest tests and Ruff lint/format checks. Tests require
loopback networking for their local HTTP stub; the restricted sandbox blocks
those connections, while the authorized run passes.

## Parallel assignments

| Session | Branch | Ownership |
| --- | --- | --- |
| Model evidence | `codex/s1-w3-model-evidence` | Evaluation harness, reviewed synthetic reports, model evidence |
| Gameplay contracts | `codex/s1-w3-game-contracts` | Event/HTTP/OpenAPI schemas, engine interface, protocol fixtures and tests |
| Pack contracts | `codex/s1-w3-pack-contracts` | Manifest/verification schemas, model lock, verification interface, storage reference and tests |

The coordinator owns integration, root dependencies, this record, project status,
cross-contract review and the final gate. Agents do not consume each other's
unmerged changes. This is a parallel reconciliation of W3 inputs; it does not
start W4 engine/browser implementation before review.

## Gate

W2's model measurement remains open until calibration and held-out reports are
reviewed. Encoding policy must be recorded before viewing held-out results.
W3 must reconcile the measured model identity, deterministic numeric ordering,
clue legality, sampling, receipts, revisions and terminal states. Thresholds
without supporting evidence remain explicitly provisional. Human play, actual
game round-trip load, release hardware and independent creator parity remain
later evidence requirements.

## Integrated outputs and checks

All three parallel assignments completed and were reviewed/integrated:

- Model evidence: worker commits `2d24ef5`, `5153c2b`, `b041fd6`; coordinator
  commits `c3e4ca2`, `423253c`, `0c60709`. Full 100-request serial and concurrent
  runs, calibration policy freeze and unchanged held-out fingerprint are retained.
- Game contracts: worker `b43ec0a`, integrated `2101017`. Concrete engine API,
  experimental HTTP polling routes, separate receipts/current snapshots and ten
  promoted trace fixtures. No production account or publication routes.
- Pack contracts: worker `4535cb1`, integrated `e7bbc4c`. Manifest/report schemas,
  typed verification API, pinned Ollama identity, canonical policy hash, numeric
  total order and deterministic sampling. Reports do not approve publication.

Coordinator review aligned legality/model-text handling, required labels in wire
snapshots, replaced prose-byte hashing with canonical policy hashing, updated the
lock to tracked measurement evidence and fixed formatting. A cross-artifact test
checks exact preserved calibration bytes, freeze ordering and fingerprint equality
across both reports and the model lock. Reports preserve their original CRLF bytes
through scoped Git attributes so hash bindings survive fresh checkouts.

Validation: the integrated 105-test suite passed with loopback access; the added
evidence-binding test also passed (106 total cases). Ruff lint and formatting pass.
Existing checks pass for ten game traces/84 states, seven negative trace tests,
150 semantic entries/450 legal clues, five arithmetic tests, four draft schemas,
seven manifests and 19 draft protocol cases. Source distribution and wheel build
pass using a workspace UV cache. Hosted CI was not run by this task.

## Outcome and next boundary

The synthetic retrieval measurement gap is resolved. Contextual entries reached
180/180 held-out top-three results; label-only 20-entry results were 161/180.
Weak-control reachability was 16.67%. Serial HTTP p95 was 201.9 ms, eight-worker
p95 338.7 ms. The proposed 100 ms full-game target remains unmet; these are
embedding HTTP measurements, not a game load test. See
[decision 0003](../decisions/0003-measured-ollama-experiment.md).

The bounded contract work is integrated, but **full W3 is not declared complete**
and W4 has not been dispatched. Concrete experimental interfaces are available
for a prebuilt-schedule prototype. Remaining gates are actual-verifier calibration
and numeric parity, adaptive casual selection, general lexical coverage and a
bounded latency investigation. Human play and full 1/4/8-player game load remain
W5 requirements. The reviewed morphology subset, provisional queue caps and
diagnostic thresholds must not be presented as production acceptance.
