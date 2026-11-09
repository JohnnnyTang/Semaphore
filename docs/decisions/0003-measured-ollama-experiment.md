# Measured Ollama experiment and W3 scope

Recorded November 9, 2026 (America/New_York).

The owner authorized LAN access and parallel W3 work using GPT-6.1 Sol at medium
effort. Direct Ollama access works; the installed model is Qwen3-Embedding 4B,
Q4_K_M, with 2,560-dimensional embeddings. Preserve the observed artifact/runtime
identity in the experiment lock. Do not substitute a generative Qwen model.

## Evidence and decision

Calibration preceded an explicit policy freeze and held-out evaluation. Contextual
entry text performed better than labels on ambiguity cases. Keep the existing
query instruction and use each entry's effective embed text (falling back to its
label). Do not change that policy after inspecting held-out results.

The synthetic held-out contextual evaluation reached top-three rank for 180/180
clues at the preregistered stack sizes. This supports continuing the bounded
experiment, not claiming general gameplay quality. The promoted verifier uses a
different deterministic sampling protocol and needs its own calibration and parity
evidence. Authored clue success does not establish human enjoyment or publication
threshold validity.

Serial embedding HTTP p95 was about 192 ms in calibration and 202 ms held-out;
the eight-worker p95 was about 373/339 ms respectively. These measurements
already exceed the proposed 100 ms full-game target before game processing.
The target has **not passed**. Continue contract work and experimental plumbing,
with a bounded latency investigation required before accepting supported gameplay
performance. Do not quietly redefine the target or remove model identity checks
to make a benchmark pass.

## Bounded next evidence

Instrument inventory-check, HTTP transport, service inference and game queue time
separately under the same pinned model. Compare one, four and eight players and
background verification pressure once the server exists. Measure rather than
assume GPU offload or LAN latency. An optimized path must preserve model-change
detection; any change needs repeat measurements and an explicit decision about
the target. Hardware is owner-reported NVIDIA 5090, 32 GB VRAM, Windows, driver
610.88; exact OS/build and independent hardware inspection remain unverified.

## Experiment boundary

W3 contracts are for a disposable Stage 1 experiment. They do not authorize
production publication. Prebuilt schedules make event fairness reproducible;
adaptive casual selection and general English morphology remain explicit gates.
The reviewed lexical subset and explicit aliases/forbidden phrases allow bounded
fixture work without claiming a complete English stemmer. The browser can use
locally bundled assets and the frozen experiment transport; production account,
upload and persistence routes remain later-stage work.

The coordinator records final integration checks and W4 readiness in the
[W3 record](../stages/s1-w3-contract-reconciliation.md). The measured result is a
reason to continue carefully, not a declaration that Stage 1 is complete.
