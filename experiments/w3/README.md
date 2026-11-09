# W3 protocol and latency probes

These development probes execute the promoted verification protocol with real
pinned Ollama embeddings. They are separate from the earlier retrieval evaluator
and are not a publication service. Use the ordinary locked dev environment plus
Node (measured with v24.12.0) for independent numeric ranking parity.

Run from the repository root. To prepare a new input set, choose a new directory:

```powershell
.venv/Scripts/python.exe -m experiments.w3.run prepare --inputs data/new-w3-inputs
$env:SEMAPHORE_OLLAMA_BASE_URL = 'http://<operator-provided-host>:11434'
$env:SEMAPHORE_OLLAMA_MODEL_DIGEST = 'df5bd2e3c74cd8d069d21dc038f1b359fcdc9458fce1c99bd43c9eb1518ff907'
.venv/Scripts/python.exe -m experiments.w3.run run --inputs data/new-w3-inputs --output data/new-w3-reports
```

For exact retained inputs, omit `--inputs`; the default is `fixtures/w3`.
Outputs use exclusive creation. An interrupted output directory is incomplete
until `binding.json` exists; choose a fresh output directory for another run.
No model/vector files are written. Reports omit raw clues, vectors and endpoint.
Review synthetic report contents before copying them into tracked evidence.

The runner validates all input hashes and the source fixture, protocol and model
pins; runs calibration authored/weak/mixed packs; writes an unchanged-policy
freeze; then runs the same modes on held-out targets. Both splits use their own
entry pool, always at least 40 entries. The weak pack uses three distinct generic
clues, so it passes clue hygiene without falsifying the protocol. The mixed pack
substitutes the first legal other target's clues at every third entry, without
score-based selection. No parameter search occurs.

Parity passes real vectors to Node through stdin and compares ordered IDs and
raw scores for ten representative queries per pack. Boundary tests separately
cover ties and positive/negative bucket edges. It does not establish independent
creator packaging, every runtime or full verifier parity.

Finally, 100 pinned single-clue operations at each of 1/4/8 concurrent workers
measure end-to-end adapter time and per-endpoint timings. Model identity checks
remain enabled. Warm requests reuse one clue and may benefit from service caches;
they are not cold inference or representative gameplay. The service does not
necessarily report inference duration; missing values remain null. Component
percentiles do not add up to end-to-end percentiles.

See [the closure decision](../../docs/decisions/0004-w3-gate-closure.md) for scope
and [the W3 evidence](../../docs/evidence/w3/README.md) for retained results.
