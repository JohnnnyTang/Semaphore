# W2 semantic evaluation evidence

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
weak/good separation and category failures, and collect actual reference-host
and human-play evidence. The [source review](content-sources.md) separately keeps
corpus licensing, yield and editorial effort gates explicit.
