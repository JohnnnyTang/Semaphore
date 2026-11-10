# LAN Ollama development baseline

Recorded November 9, 2026 (America/New_York).

## Owner decision

The owner selected Qwen3-Embedding 4B for now and is preparing an NVIDIA GPU
machine reachable on the LAN. Development will call Ollama's HTTP API directly
from the Semaphore backend. Work that does not need that endpoint is authorized.

The initial tag is `qwen3-embedding:4b`, with native 2,560-dimensional vectors.
The earlier assistant suggestion of a separate Q8 tag is not applied implicitly.
Capture the installed digest and quantization from the server before measurement.
No digest, GPU capability, latency or semantic result has been observed yet.

This supersedes the three-way BGE/GTE/Nomic selection experiment as the immediate
development prerequisite. Preserve its failed-download record as history. The
selected model still needs calibration, held-out evaluation and human playtests;
owner selection is not evidence of a quality pass. No further model comparison
or downloads are required by this work.

The CPU-only/8 GB target remains an unvalidated release proposal, not a constraint
on this development setup. Release topology and offline creator distribution
remain open. LAN inference needs no internet once the model is installed.

## Implemented experiment boundary

- `semaphore_core.embeddings` provides synchronous query/entry embedding methods.
  No Torch, Transformers, local model assets or new dependencies are needed.
- Set the operator-provided HTTP(S) origin via `SEMAPHORE_OLLAMA_BASE_URL`.
  Browsers never connect to Ollama. No endpoint discovery, model pulling,
  model switching, CPU fallback or fake-score fallback occurs.
- Initial query policy `semaphore-qwen4b-association-v1` prefixes clues with:
  `Instruct: Given a word-association game clue, retrieve the words or phrases most closely associated with the clue.\nQuery: `
  Entries receive no prefix. Preserve case and text. This custom instruction is
  a calibration hypothesis, not a proven improvement.
- Request 2,560 dimensions, `num_ctx: 512`, `truncate: false`, `keep_alive: 30m`.
  Default batch size is 16. A 30-second socket timeout serves diagnostics; it
  is not an approved game deadline or an overall request deadline.
- Validate response model, count, dimensions, finite numbers and L2 norm
  (absolute tolerance 0.001). Reject bad responses instead of repairing them
  or returning partial vectors. Empty input returns no vectors locally.
- No automatic retries. Distinguish unavailable transport, HTTP status and
  invalid responses. Never echo raw service errors, which may contain clues.
  Redirects and environment proxies are disabled for this direct LAN connection.
- Snapshot model tag/digest/details and Ollama version before and after each
  check/run. A configured digest pin detects a different installed model.
  Freeze the service during measurement; snapshots cannot detect a tag changed
  and restored between observations.

The experiment fingerprint has its own namespace. It does **not** satisfy the
W2 production schema's Hugging Face revision, tokenizer hashes, pooling and dtype
requirements. W3 must reconcile that schema with Ollama artifact/runtime identity
before publication reports or persistent vector caches are introduced. No
production verification schema is silently relaxed here.

## Prepared measurements and remaining gates

The runner preserves fixture bytes and splits, 6/12/20-entry stacks, category
summaries, five deterministic pack decoy samples, the weak generic-clue control,
label/context modes and nearest pairs. Illegal controls never reach the API.
Held-out runs require a calibration report with identical model/encoding
fingerprint and fixture. Changes to input policy require new calibration first.

Record warm serial/concurrent HTTP p50/p95, batch throughput, concurrency,
fingerprint, client environment and `/api/ps`. HTTP time includes transport and
queuing; it is not game round-trip latency. The first request is not a cold start
because the model may already be loaded. Attach server GPU, driver, OS and memory
inventory separately. No synthetic test establishes real GPU performance.

When the URL arrives: run the documented check, pin its digest, run calibration,
review results and freeze policy before held-out evaluation. Verify GPU offload
on the server. Preserve reports under new paths, never overwriting evidence.

The gameplay proposal already maps infrastructure errors to `inference_failed`,
clears pending state and discards late results after game end. Keep transport
errors separate from semantic rejection. The future server must run this adapter
outside its event loop, enforce a bounded queue/game deadline, and ignore late
worker results. Caller cancellation does not cancel Ollama work. Queue limits,
production near-ties, publication thresholds, creator parity and human play
remain evidence gates. This work does not declare W2/W3 complete.

## References

- [Ollama embedding endpoint](https://docs.ollama.com/api/embed)
- [Model inventory](https://docs.ollama.com/api/tags)
- [Loaded-model inventory](https://docs.ollama.com/api/ps)
- [Qwen4B and query instruction format](https://huggingface.co/Qwen/Qwen3-Embedding-4B)
- [Commands and configuration](../../experiments/model_eval/README.md)
