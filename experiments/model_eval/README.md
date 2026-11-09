# Semantic evaluation

## Current development path: LAN Ollama, Qwen3-Embedding 4B

The owner fixed `qwen3-embedding:4b` as the development model on November 9,
2026. See the [decision](../../docs/decisions/0002-lan-ollama-development.md).
The ordinary locked development environment suffices; this path needs no local
model packages or weight downloads. Run commands from the repository root.

Validate the frozen fixture without contacting a server or requiring a LAN URL:

```sh
uv run --no-sync python -m experiments.model_eval.ollama_eval validate
uv run --no-sync pytest
```

Tests use scripted vectors and a localhost HTTP stub. They establish transport
and validation behavior, not model quality or GPU performance.

Once the server is ready, configure the operator-provided URL. PowerShell:

```powershell
$env:SEMAPHORE_OLLAMA_BASE_URL = "http://<LAN-IP>:11434"
uv run --no-sync python -m experiments.model_eval.ollama_eval check --output data/ollama/check.json
```

POSIX shells use `export SEMAPHORE_OLLAMA_BASE_URL="http://<LAN-IP>:11434"`.
Replace the placeholder before running. `.env.example` lists settings; this
project does not automatically load `.env`. The model is fixed in code.

`check` verifies inventory and 2,560-dimensional query/entry vectors, records
sample cosines and reads loaded-model inventory. It sets no semantic threshold.
Inspect GPU offload on the server with `ollama ps`; record GPU model, driver,
VRAM and OS separately. Successful HTTP requests alone do not certify offload.

Copy `fingerprint.digest` from the report to detect future model changes, then
run calibration:

```powershell
$env:SEMAPHORE_OLLAMA_MODEL_DIGEST = "<full-64-hex-digest>"
uv run --no-sync python -m experiments.model_eval.ollama_eval run --split calibration --output data/ollama/calibration.json
```

Defaults are 100 serial and 100 concurrent single-clue requests with up to eight
workers, followed by fixture evaluation in batches of 16. For a small initial
probe, use `--repeats 8 --concurrency 2`. HTTP p50/p95 include network/queuing and
validation; they are not full-game acceptance measurements. Failures abort the
run, never producing a semantic pass or fallback vectors.

When a digest pin is configured, each embedding operation checks inventory
first; that check is included in its reported HTTP latency. Compare measurements
with the same pin configuration. This prevents standalone adapter calls from
silently bypassing the configured pin.

Inspect category failures, label/context differences, weak/good pack separation
and confusing pairs. Freeze encoding settings using calibration only, then run:

```sh
uv run --no-sync python -m experiments.model_eval.ollama_eval run --split held_out --calibration-report data/ollama/calibration.json --output data/ollama/held-out.json
```

The runner rejects a mismatched calibration fingerprint or fixture. Both label
and context modes are preregistered; do not tune after inspecting held-out ranks.
Record a new policy and new calibration report for any earlier policy changes.
Keep the server's model tag/runtime unchanged throughout each run.

Reports include model digest/details, Ollama version, input formatting, fixture
hash, client environment, performance settings, ranks and IDs. They exclude raw
clues and vectors. `data/` is ignored; review synthetic reports before copying
them to tracked evidence. Output paths must be new; reports are not overwritten.

`SEMAPHORE_OLLAMA_TIMEOUT_SECONDS` sets the socket timeout (default 30 seconds);
`SEMAPHORE_OLLAMA_BATCH_SIZE` sets batches from 1 to 64 (default 16). The
synchronous adapter does not provide an overall game deadline, queue or
cancellation. It performs no retries, installation or model fallback.

## Historical CPU semantic comparison

These original W2 commands are retained for history. They are not prerequisites
for the owner-selected Ollama development model.

This experiment consumes fixed synthetic fixtures and does not implement the
production embedding API. Root dependencies/lock belong to the coordinator.
Use the coordinator's `model-eval` uv group after integration; the original W1
environment alone only runs validation and arithmetic tests.

From the repository root:

```sh
uv sync --locked --group dev --group model-eval
uv run --no-sync python experiments/model_eval/run.py validate
uv run --no-sync python -m unittest discover -s experiments/model_eval -p 'test_*.py'
uv run --no-sync python experiments/model_eval/run.py fetch --model bge
uv run --no-sync python experiments/model_eval/run.py run --model bge --threads 2 --split calibration --output experiments/model_eval/results/bge-calibration.json
```

Repeat fetch/run for `gte` and `nomic`, one process at a time. Models live in
ignored `model-cache/`; `--cache` selects another local directory. Fetch is the
only network step. The run uses pinned local snapshots, safetensors, CPU float32,
no remote Python, no uploaded vectors and offline model/tokenizer settings.
Failure to load native Nomic is a blocked measurement, not permission to enable
`trust_remote_code`. Capture the exception and dependency versions.

Run calibration first, then document any encoding-policy decision before running
the same commands with `--split held_out` and new output paths. Never tune after
examining held-out ranks. Current preregistered policies are unprefixed BGE/GTE
and query/document-prefixed Nomic, comparing label-only and contextual entries.
Nomic uses layer normalization then L2 at all 768 dimensions; every candidate
uses a 512-token cap, far above the short fixture texts. No dimensionality or
threshold search occurs. BGE retrieval instructions are a later calibration-only
alternative if the initial mode fails; they are not silently mixed into results.

Outputs preserve aggregate scores, ranks/top-three IDs for each synthetic case,
near-neighbor pairs, exact command, fixture hash, model pin, packages, core/thread
counts, RAM, and timing/memory fields. Warm latency is 100 serial batch-one clue
embeddings; throughput is one batch-16 pass over the selected clues. Cold load
means new-process load of cached assets after Python imports, not download time
or an uncached operating-system disk cache. Peak working set is recorded when the
platform exposes it; RSS-after is not peak memory. Asset bytes exclude local Hub
bookkeeping. No measurement here establishes game round-trip or 8-player latency.

Before a model decision, inspect per-category and contextual-label differences,
the weak/good pack separation, held-out ranks, and confusing pairs. Model weights
must not enter Git. Results contain synthetic clues by ID only and may be committed.
