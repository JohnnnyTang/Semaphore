# Semantic evaluation evidence

November 9 update: the owner-selected `qwen3-embedding:4b` now has measured LAN
calibration and held-out evidence. Context-enriched entries perform strongly on
this synthetic fixture; measured embedding HTTP p95 already exceeds the proposed
100 ms full-game goal. Development selection remains distinct from release acceptance.

## Qwen4B LAN measurements, November 9, 2026

Preserved reports: [calibration](ollama/qwen4b-calibration.json),
[policy freeze](ollama/policy-freeze.json), [held out](ollama/qwen4b-held-out.json).
Both runs used the unchanged fixture hash recorded below, native 2,560 dimensions,
Q4_K_M model digest `df5bd2e3c74cd8d069d21dc038f1b359fcdc9458fce1c99bd43c9eb1518ff907`,
Ollama 0.40.15, and `semaphore-qwen4b-association-v1`. Calibration was reviewed
before held-out inference: context (`embed_text`) became the primary entry mode;
label-only remains the preregistered comparison. The instruction, unprefixed
entries, 512 context, no truncation, normalization checks and both modes were
unchanged. No prompt, dimension, threshold or near-tie search was performed.
The freeze records the calibration SHA and precedes the held-out report timestamp;
the held-out report binds that same calibration SHA and fingerprint.

| Split / entry mode | 6-entry top-three | 12-entry top-three | 20-entry top-three |
| --- | --- | --- | --- |
| Calibration / label, 270 clues | 98.52% | 97.41% | 96.30% |
| Calibration / context, 270 clues | 100% | 99.63% | 99.63% |
| Held out / label, 180 clues | 98.89% | 96.11% | 89.44% |
| Held out / context, 180 clues | 100% | 100% | 100% |

Median rank is 1 in every category/stack/mode/split. At 20 entries, label-only
ambiguity drops from 83.33% calibration to 63.89% held out; context reaches 100%
in both. Held-out label concrete is 88.89%, biology 94.44%, geography and multiword
100%; all held-out context categories reach 100%. Calibration context has one
20-entry miss, `concrete-03-c2`, rank 4, with `multiword-14`, `concrete-09` and
`concrete-06` ahead. Label-only `ambiguous-07` has ranks 16/17/20 across its three
calibration clues, illustrating sense ambiguity. Context resolves that case.
These are authored clues and contexts from one fixture, not independent human
generalization or evidence that context always improves arbitrary packs.

| Pack view | Calibration label / context | Held-out label / context |
| --- | --- | --- |
| General intended-good | 98.15% / 100% (54 targets) | 94.44% / 100% (36) |
| Biology difficult | 94.44% / 100% (18) | 91.67% / 100% (12) |
| Weak generic control | 14.44% / 10% (90) | 15% / 16.67% (60) |

Pack percentages summarize top-three reachability after five deterministic
20-entry decoy samples: median rank across samples per clue, then across authored
clues per target. They are not the per-clue fixed-stack percentages above and
do not calibrate the separate W3 publication verifier or its sampling contract.
The extreme weak control separates well from intended-good views, but does not
locate a defensible boundary among marginal packs. The proposed 85% publication
threshold remains provisional; no numeric threshold is selected from held-out
results. Obtain independently authored, borderline and adversarial packs using
the actual verifier protocol before claiming publication calibration.

Context nearest neighbors include `geography-24`/`geography-25` (0.9433),
`geography-19`/`geography-20` (0.9379), `geography-24`/`geography-26` (0.9343)
and `biology-26`/`biology-27` (0.8951). These close related entries justify retaining
hard decoys and human review; successful authored-clue ranks do not prove that
entries are interchangeable or that a production near-tie tolerance is validated.

| HTTP performance | Calibration | Held out |
| --- | --- | --- |
| Warm serial p50 / p95, ms | 131.0 / 191.9 | 148.9 / 201.9 |
| Eight-worker p50 / p95, ms | 306.7 / 373.4 | 299.5 / 338.7 |
| Batch-16 clue embeddings / second | 39.46 | 41.82 |

Each run measured 100 serial and 100 concurrent single-clue operations, followed
by all selected clues in batches of 16. Digest inventory checks are included in
each operation; socket timeout was 30 seconds. No failed operation was converted
to a score. First requests (0.201/0.184 seconds) are not cold-load measurements.
Warm serial embedding p95 alone misses the proposed 100 ms game round-trip goal;
this does not constitute a full-game latency test. Eight workers are a request
probe, not eight-player gameplay with uploads, event delivery and bounded queues.
Next performance work should use a bounded representative server load probe,
separate inventory/transport/inference timing, and test queue/deadline behavior.
Any optimization comparison needs fixed pin settings and a fresh performance
run; do not retune semantic policy against these held-out ranks. If the goal
remains unattainable, explicitly revise development latency scope with the owner.

Client reports capture Windows 11/Python 3.12. Server inventory reports 2,647,539,056
loaded bytes and the same `size_vram`, with context 512 and runner `llamacpp`.
This is server-reported allocation, not independently verified GPU execution.
Owner-reported hardware: NVIDIA 5090, 32 GB VRAM, Windows, NVIDIA driver 610.88.
Exact GPU SKU, OS version/build, CPU/RAM, server load and `ollama ps` offload
verification are still missing. No release GPU, CPU-only/8 GB or full-game
acceptance is established. The historical client inventory below is not server
hardware. Reports were reviewed for raw clues/vectors and endpoint/client paths;
none are present. The server-supplied generic model-blob parent path is retained
inside the fingerprint to preserve its hash and the calibration binding.

Validation: seven `tests/test_ollama_eval.py` tests and five historical evaluator
unit tests pass. A first pytest invocation hit sandbox temporary-directory
permissions; rerunning with a workspace temporary directory passed all seven.
Both full real-model runs completed with unchanged pre/post identity and passed
response validation. See [decision 0002](../decisions/0002-lan-ollama-development.md)
and the [runner instructions](../../experiments/model_eval/README.md).

## Historical CPU comparison (superseded for development)

Date: November 8, 2026. Status: fixture and harness implemented; model-selection
gate remains open until the three pinned candidates have comparable measurements.
No model is selected and no performance or semantic-quality pass is claimed here.

## Preregistered experiment

The [fixture](../../fixtures/semantic/README.md) contains 150 synthetic entries
across five equally sized categories, with 90 calibration and 60 held-out targets.
Each target has three authored clues and an exact-label illegal control. Legal
clues: 270 calibration, 180 held out. Candidate stacks are fixed at 6/12/20;
two same-category decoys are retained in each. Held-out targets are not used for
encoding or threshold tuning. Independent human clue authoring remains missing.

Frozen fixture SHA-256:
`6ef2b3b9d68d3ad7a219a95cb064a909c01844f0bed360749486830f76f13d13`.
It was authored and structurally validated before model inference. UTF-8 LF
generation and the repository's existing JSON LF attributes preserve the digest
across Windows/Linux checkouts. Any semantic fixture change after measurements
invalidates comparison with this version.

| Candidate | Immutable repository revision | Encoding policy |
| --- | --- | --- |
| BAAI/bge-base-en-v1.5 | `a5beb1e3e68b9ab74eb54cfd186867f64f240e1a` | Unprefixed clue and entry; normalized full-dimensional embeddings. |
| thenlper/gte-base | `c078288308d8dee004ab72c6191778064285ec0c` | Unprefixed clue and entry; normalized embeddings through the pinned Sentence Transformers pooling configuration. |
| nomic-ai/nomic-embed-text-v1.5 | `e9b6763023c676ca8431644204f50c2b100d9aab` | `search_query: ` clues and `search_document: ` entries; layer normalization then L2, full dimensionality. |

Revisions were resolved from each repository's public Hugging Face model API.
The [BGE model card](https://huggingface.co/BAAI/bge-base-en-v1.5) supports
unprefixed use outside short-query/long-passage retrieval; this is our initial
word-association policy. Its retrieval-prefix variant would require a separately
recorded calibration experiment. The [GTE card](https://huggingface.co/thenlper/gte-base)
shows unprefixed inputs and mean pooling, which its local Sentence Transformers
configuration supplies. The [Nomic card](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5)
requires task prefixes and states that native loading no longer needs remote code
from Transformers 5.5.0 / Sentence Transformers 5.3.0. The harness never enables
remote code; native loading failure remains a failed candidate run.

For every candidate compare label-only versus context-enriched entry text,
top-three rate and median rank by category/stack size, and top cosine neighbor
pairs. Five deterministic decoy samples yield per-clue medians and then per-entry
medians for three pack views: general intended-good, specialist biology, and an
intentionally weak generic-clue view. These views are not publication manifests.
No threshold is selected from held-out performance, and intended-good is an
authoring hypothesis rather than an assigned passing score.

## Environment and validation

Coordinator-provided measured development host: Intel Core Ultra 7 258V,
8 physical/8 logical cores, 33,796,481,024 bytes RAM, Windows 11 Home Chinese
10.0.26300 x64. This is roughly 31.5 GiB installed memory, **not** the initial
8 GB reference target. Root coordinator resolved CPU-only Torch 2.15.0+cpu,
Transformers 5.22.2, Sentence Transformers 5.7.0 and psutil in a locked optional
model-eval dependency group. Runtime imports completed, with unusually slow
initial import/source-compilation behavior observed by the coordinator.

Local commands and observations:

- `python experiments/model_eval/run.py validate`: 150 entries, 60 held-out
  targets, 450 legal clues and 150 illegal controls.
- `python -m unittest discover -s experiments/model_eval -p 'test_*.py'`:
  five tests pass for rank direction/ties, malformed scores, percentile and
  top-three arithmetic, split-leakage detection, and canonical fixture bytes.
- Ruff lint and format checks pass on the experiment Python files.
- Canonical fixture bytes match the recorded SHA after Windows generation.

These checks establish fixture integrity and benchmark arithmetic, not semantic
quality, inference parity, human fun, CPU load or end-to-end gameplay latency.

## Measurement status and W3 handoff

The [attempt record](../../experiments/model_eval/results/run-status.json)
contains the actual blocked download evidence. The initial BGE snapshot fetch
completed metadata but stalled on weights. A bounded HTTP fallback with
`HF_HUB_DISABLE_XET=1` and 30-second download/15-second metadata timeouts reported
that its peer closed the connection after 84,283,322 of 437,955,512 weight bytes;
the automatic resume was interrupted. No benchmark inference ran. GTE and Nomic
large downloads were deferred after this failure, so neither is called a failed
quality candidate. Partial files remain outside Git in the ignored cache.

The [runner instructions](../../experiments/model_eval/README.md) specify fetch,
offline run, thread caps and preserved result paths. Use two CPU inference
threads, one interop thread and float32 for the first comparable pass. Record
cached-process load separately from cold Python imports and OS cache effects.
Warm serial clue embedding and batch-16 throughput are not LAN round-trip or
concurrent upload measurements. The 5,000-entry verification/load probe remains
later work; extrapolating small-fixture throughput is not acceptance evidence.

W3 must not freeze a model, numeric near-tie policy or publication threshold from
this infrastructure alone. Before that gate: finish three calibration runs,
record a fixed encoding policy, run held-out data without further tuning, inspect
weak/good separation and category failures, and identify the measured benchmark
host. Reference-server load and human-play evidence remain Stage 1 exit gates
for W5 after the W4 playable experiment exists. The [source review](content-sources.md) separately keeps
corpus licensing, yield and editorial effort gates explicit.
