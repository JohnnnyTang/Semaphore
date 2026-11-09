# CPU semantic comparison

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
