# Hardware and content feasibility pilot

November 14, 2026, Asia/Shanghai. The owner selected the current LAN GPU setup
and supplied its Ollama origin, then requested measurements on the local machine.
This changes this task's measurement target; it does not establish CPU-only/8 GB
release support. Existing performance/contract work was preserved.

## Findings and gate disposition

| Question | Observed result | Disposition |
| --- | --- | --- |
| Fresh local application startup with restricted egress | 2.772 s to HTTP 200 using the pinned real model; installed dependencies, new Python process | Bounded server startup passed |
| Local CPU/RAM | Peak working set 111.414 MiB; sampled peak private bytes 98.277 MiB; 25.422 CPU seconds / 29.579 elapsed seconds | Measured on current local host only |
| Fully offline topology | Only the Python process was restricted; configured model origin remained reachable | Open: remote egress/model-host restart not verified |
| Small authored pack | 40 targets, 120 legal clues, 40 exact-label negative controls rejected; real verifier reachable entries 40/40, mean rank 1.1, no flagged pairs | Bounded automated pilot passed |
| Source yield and human review cost | 50 purposively authored candidates including 10 deliberate rejects; no human reviewers | Open: no random-source yield or timed human review |
| Gameplay performance | Seven eight-player inference timeouts; all measured p95 values exceed 100 ms | Failed; keep Stage 1 open |

## Hardware and runtime method

[Local inventory](feasibility-2026-11-14/local-hardware.json): Windows 10 build
19045, Intel i5-13490F (10 cores / 16 logical CPUs), 34,164,101,120 bytes physical
RAM and RTX 4070. The local GPU did not perform embedding inference. The model
service matched the full existing Qwen3-Embedding 4B Q4_K_M fingerprint, native
2,560 dimensions, Ollama 0.40.15. The separately installed local Ollama 0.18.3
was not substituted for that service.

The [runner](../../experiments/acceptance/feasibility.py) installs a Python audit
hook before application imports. It permits only loopback and the operator's
literal model IP/port, denies other connects and DNS, and proves one prohibited
connect is blocked without sending it. The successful run recorded 233 model
connections, 787 loopback connections and only the one deliberate denied connect.
This is process-level evidence, not an OS firewall or remote-host isolation test;
native libraries and other processes are outside its assurance boundary. There
was no model download, runtime dependency installation, model change or remote
restart. Index HTTP serving was tested; browser rendering was not measured here.

Before startup `/api/ps` returned an empty model list. The adapter subsequently
loaded the installed model and startup succeeded. This establishes an observed
nonresident-to-resident transition, not reboot/disk-cold startup or offline model
asset completeness on the remote host. Afterward the service reported
2,647,539,056 model bytes and the same VRAM allocation. Those are service-reported
allocations, not independent GPU inventory, utilization or peak VRAM measurements.

The first run stopped because the probe called `running_model()` before loading
an initially nonresident model. Its failure evidence is preserved in
[local-run](feasibility-2026-11-14/local-run/startup.json). The corrected probe
records raw pre-start inventory rather than requiring residency. The successful
[raw report](feasibility-2026-11-14/local-run-2/startup.json),
[100 ms resource samples](feasibility-2026-11-14/local-run-2/resources.json) and
[summary](feasibility-2026-11-14/local-run-2/summary.json) are retained separately.
Windows peak-working-set counters capture the process lifetime; sampled private
memory may miss short peaks. CPU averaged 85.94% of one logical CPU, or 5.37%
of all 16 logical CPUs. This includes the in-process HTTP clients, server, sampler
and sequential verifier; it excludes browser memory and remote model resources.
It is not an isolated production-server capacity measurement.

## Bounded gameplay and content verification

Three clue rounds per simulated player, 10 ms polling, real HTTP/embedding,
sequential 1/4/8-player groups; verification ran afterward, without verifier
pressure. `miss` is a completed semantic result for the probe's generic clue.
No performance improvement over earlier pressure runs can be inferred.

| Players | Requested / resolved receipts | Completed semantic results | Inference timeouts | p95 all receipts, ms |
| --- | --- | --- | --- | --- |
| 1 | 3 / 3 | 3 | 0 | 353 |
| 4 | 12 / 12 | 12 | 0 | 2,174 |
| 8 | 24 / 24 | 17 | 7 | 5,418 |

p95 uses nearest rank, includes timeout receipts, and has very small denominators.
`probe_completed` means the measurement finished, not that gameplay passed.
The new [manifest](feasibility-2026-11-14/content/manifest.json) was passed through
the existing core verifier and pinned model: five deterministic decoy samples per
clue, 40/40 reachable targets, 120 legal clues, mean rank 1.1 and no flagged pairs.
Verification took 3.474 s. See [semantic report](feasibility-2026-11-14/local-run-2/semantic.json).
This is a newly authored diagnostic pack, not an independent human-held-out set.
No policies or thresholds were tuned using its results.

## Sourcing and authoring pilot

The [source files and provenance](../../fixtures/content-pilot/README.md) retain
40 original targets with three original clues each, five categories of eight,
and the ten editorial rejection controls. The [audit](feasibility-2026-11-14/content/audit.json)
records the sequential counts: 50 candidates -> 49 after normalized duplicates
-> 48 after duplicate senses -> 46 after proper names -> 44 after abstract terms
-> 42 after unresolved senses -> 40 after specialist terms. Automated core
validation took 0.0071 s. Drafting/build wall time was 191 s, including tooling;
this does not measure human review or production throughput.

The official [WordNet license](https://wordnet.princeton.edu/license-and-commercial-use)
was rechecked: redistribution requires retaining the license notices and disclaimers.
The [wordfreq maintainer documentation](https://github.com/rspeer/wordfreq#license)
was also rechecked; its data is not a license-free noun list. Neither dataset was
imported or redistributed, so this pilot chooses the original-authoring fallback.
Concreteness-data redistribution remains on hold as recorded in
[content sources](content-sources.md). No joined source yield was measured.

The 80% retained fraction is constructed by selection and is not a population
estimate. Do not use it to revise the earlier 380–480 review-hour planning scenario.
A 500-candidate stratified source sample and independent timed review of 100
sets remain the larger content gate. For this small pack, independent reviewers
should record active minutes, edits/rejections, unfamiliar terms and clue quality
before accepting it for play. No review-hours or review outcome is fabricated.

## Reproduction and remaining checks

Use installed locked dependencies; select a fresh output directory each run:

```powershell
$env:PYTHONPATH = 'packages;.'
$env:SEMAPHORE_OLLAMA_BASE_URL = 'http://<operator-provided-IP>:11434'
.venv/Scripts/python.exe -m experiments.acceptance.content_pilot --output-dir data/pilot-new
.venv/Scripts/python.exe -m experiments.acceptance.feasibility --manifest data/pilot-new/manifest.json --output-dir data/feasibility-new
```

To close full offline hardware acceptance, repeat on both hosts with internet
access removed while retaining their private connection, start Ollama with cached
assets, restart the application, and capture model-host CPU/RAM/GPU/VRAM through
startup, gameplay and concurrent verification. Record installed-asset size and
missing-asset failure behavior. Current measurements cannot substitute for that
host access. Keep the existing 100 ms target and Stage 1 disposition unchanged.

Validation: 31 targeted core/acceptance tests and one network-guard regression
passed (32 total). Ruff lint/format pass for the added scripts/test; rebuilding
the pilot reproduces the retained manifest byte-for-byte. Final reproduction
source hashes are retained in `feasibility-2026-11-14/source-snapshot.json`.

Follow-up: [queue/polling refinement](feasibility-refinement-2026-11-14.md) records
subsequent reliability improvements. The measurements above remain the baseline.
