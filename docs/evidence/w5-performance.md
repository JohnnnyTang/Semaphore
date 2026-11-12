# Stage 1 Wave 5 performance and parity evidence

November 11, 2026. Application baseline `64e3a90`, Windows 10 build 19045,
Python 3.12.10, Intel Core i5-13490F and 34,164,101,120 bytes of client RAM
reported by Windows. The client hosted the disposable game server on loopback.

## Model availability and open gates

The configured development Ollama origin failed the pinned adapter identity
preflight with `EmbeddingUnavailable`. The adapter bypassed proxies and used a
five-second socket timeout. An independent direct TCP check with a four-second
timeout returned `ConnectionRefusedError` (WinError 10061). No W5 model identity,
offload or inference data was obtained. W3's earlier LAN measurements remain in
[the model decision](../decisions/0003-measured-ollama-experiment.md).

W5 real-model parity and warmed clue latency at 1/4/8 players remain open. There
is no new result against the 100 ms p95 target. The W4 HTTP server does not emit
the optional queue and embedding timing headers. A reachable pinned service and
timing instrumentation are needed to collect both components. CPU/RAM behavior
under actual inference, reference GPU inventory and a network-isolated startup
with real model assets remain unmeasured.

## Checks completed with synthetic embeddings

| Check | Observed result |
| --- | --- |
| Actual reducer via `TraceReplay` | All 10 frozen traces matched their withheld expectations, covering 84 events. |
| Actual core versus W3 reference | Independent fresh Python processes agreed across all 900 sampled clue cases, including ordered ranks and score tolerance of 1e-5, on `held_out-authored.json` (SHA-256 `8ebf7369b1a1406e3ae3f2e2b553f77b97e451414fef7fa3e095c14552e9b76f`). |
| Manifest and delivery checks | All six invalid manifests rejected before any embedding call. All 10 reorder fixtures passed the harness observer. |
| Actual HTTP binding | All seven robustness checks passed, including command retries, payload conflicts, future revision, invalid client score and repeated quit. |
| Actual HTTP binding with core verifier subprocess | 3/3, 12/12 and 24/24 clue round trips completed at 1, 4 and 8 simulated players. Each group overlapped one successful verifier process. |

The HTTP smoke used the casual `calibration-authored.json` artifact, the default
5-second spawn interval and 10 ms client receipt polling. The smoke injected
`SyntheticEmbedder` into `GameService`, served with `make_server`, and used the
core verification worker with `--pressure` and no Ollama selection. Its main
process rejected non-loopback socket connections. The pressure subprocess used
deterministic text-derived vectors. The report suppressed timing components and
latency-target decisions. This scope demonstrates model-free server and worker
startup plus orchestration.

## Reproduction

From the checkout with the locked development environment in PowerShell:

```powershell
$env:PYTHONPATH = 'packages;.'
python -m experiments.acceptance.run replay --adapter semaphore_core.trace:TraceReplay
python -m experiments.acceptance.run parity --backend core
python -m experiments.acceptance.run invalid --backend core
python -m experiments.acceptance.run reorder
python -m pytest -q tests/contracts/test_acceptance_probes.py
```

When the owner-provided service is reachable, configure the server and verifier
with the same `SEMAPHORE_OLLAMA_BASE_URL`, then run the
[server and load procedure](probe-method.md#load-procedure-and-timing-limits).
Use `parity --backend core --ollama-env` to run the same two paths against the
pinned Ollama model. The real load probe requires the verification worker's
`--pressure` mode and records how many completed clue round trips overlapped
verified adapter calls. Process startup alone cannot satisfy real-model overlap.
