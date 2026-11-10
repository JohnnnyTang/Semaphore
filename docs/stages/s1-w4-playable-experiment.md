# Stage 1 / Wave 4: bounded playable experiment

Integrated November 10, 2026 (Asia/Shanghai), after owner-requested parallel work
by three GPT-6.1-sol agents at high reasoning effort. Status: **integrated locally**.
Hosted CI and W5 acceptance have not been run.

## Baseline and ownership

All workers started from `bdfa190` (W3 closure), in isolated ignored worktrees.
Integration branch: `codex/s1-w4-integration`.

| Session | Worker commits | Owned paths |
| --- | --- | --- |
| F — core and server | `24a842a`, `f8a4b48`, `ebf1e24`, `8ae743a` | `packages/semaphore_core/`, `experiments/game_server/`, `tests/core/`, `tests/game/` |
| G — browser | `f6de37a` | `web/`, `tests/web/` |
| H — independent probes | `cda485f` | `experiments/acceptance/`, `tests/contracts/`, `docs/evidence/probe-method.md` |

Coordinator owned dependencies, integration, CI and this record. Workers were
instructed to load relevant skills/plugins; frontend-design and Playwright were
applied to G and coordinator review. No worker consumed another's unmerged files.

## Delivered behavior

The installable core provides frozen manifest validation, hashing, lexical checks,
numeric ranking, deterministic sampling and verification, plus a filesystem-free
immutable game reducer. Packaged schemas match the frozen contract sources.
The experimental server uses one bounded FIFO inference worker, deadlines,
idempotent command receipts and process-local sessions. Its pinned Ollama adapter
retains the selected fingerprint. The browser supports scripted practice and
same-origin HTTP play, keyboard controls, authoritative revisions, recovery,
long labels, narrow layouts and reduced motion.

Independent probes cover fresh-process verification parity, sealed expected trace
states, invalid inputs, HTTP trust boundaries, and concurrent gameplay/verifier
orchestration. Review fixed static-mount traversal, artifact validation, malformed
worker values, /web/ landing routing and Windows module MIME handling.

## Validation

- Final integrated pytest: **168 passed** (34.30 seconds).
- Browser Node tests: **6 passed**. Agent's two Chromium QA scripts passed.
- Ruff lint/format pass; **79 Python files** formatted. Git diff check passes.
- Source distribution and wheel build pass. Isolated installed wheel loads the
  callable verifier/game modules and bundled schemas, and parses an authored pack.
- All ten frozen traces replay through the actual reducer with expectations withheld.
- Six manifest rejection probes fail before embedding; independent reference/core
  fresh-process parity passes **900 sample/clue cases** with synthetic embeddings.
- Actual HTTP server passes seven independent robustness checks (revision, retry,
  conflict, client score, clue length, missing receipt, repeated quit).
- Actual server with synthetic embeddings completes 1/4/8-player HTTP smoke groups,
  one clue per player, with overlapping core-verification subprocess work. This
  proves orchestration only. Timing/target fields from this synthetic run are not
  real-model performance evidence and are deliberately not promoted here.
- Coordinator Chromium smoke against actual HTTP binding: create game, focused
  input, Enter submission, authoritative miss result, scheduled spawns and game
  end; no console errors. Agent visual QA is retained in `web/QA.md`.
- Existing gameplay/semantic/manifest fixture validators passed on the baseline;
  their source fixtures remain unchanged.

CI now includes the dependency-free Node state/transport tests. Hosted workflow
execution and actionlint were not available in this local validation.

## Run and next boundary

See [server launch](../../experiments/game_server/README.md),
[browser launch and QA](../../web/README.md), and
[independent probe method](../evidence/probe-method.md).

W4 implements decision 0004's bounded scope: both modes use finite schedules,
legality uses the reviewed English subset, and the 0.85 threshold is diagnostic.
No production accounts, persistence, publication, adaptive schedules or full
lexical coverage is claimed. The server calls a separately configured cached LAN
Ollama model; this task did not remeasure that service or validate release hardware.

W5 remains open for real-model 1/4/8-player round trips under verification pressure,
human play, and Stage 1 decisions. The 100 ms Stage 1 target remains unmet.
The commit containing this integration record is the next local baseline.
