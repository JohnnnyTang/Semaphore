# Independent W4 probe method

These probes were authored against baseline `bdfa190` and the frozen W3 contracts,
without consuming F/G's unmerged implementation. They exercise tooling on synthetic
fixtures and a deliberately incomplete HTTP fake. W5 must run the integrated core,
real server, real pinned model and named hardware. A successful probe never sets
`acceptance_established`; the stage report adjudicates those gates separately.

Run from the repository with the locked development environment. In PowerShell,
set `$env:PYTHONPATH='packages;.'` so a different installed checkout cannot silently
supply the core. All child processes reset PYTHONPATH to this checkout and run here.

```powershell
python -m experiments.acceptance.run plumbing --rounds 1
python -m pytest tests/contracts/test_acceptance_probes.py
python -m experiments.acceptance.run invalid --backend core
python -m experiments.acceptance.run replay --adapter semaphore_core.trace:TraceReplay
python -m experiments.acceptance.run parity --backend core --output parity-synthetic.json
# Contact the configured trusted LAN model only when collecting real W5 evidence:
python -m experiments.acceptance.run parity --backend core --ollama-env --output parity-real.json
python -m experiments.acceptance.run robustness --base-url http://SERVER:8000 --artifact-id default
```

`plumbing` replays the independent fixture oracle, deliberately reordered transport
frames, manifest rejection, HTTP robustness and 1/4/8 simulated players against a
local disposable fake. Its pressure subprocess actually executes the W3 verifier
using text-hash synthetic unit vectors. No model is contacted. Fake load durations
and latency target decisions are suppressed, rather than published as load evidence.
The test suite also uses trivial measured-result subprocesses solely to test the
pressure orchestration and explicitly tests rejection of empty successful output.

## Separate verification paths

`parity` launches two fresh Python processes. The first invokes the frozen
`experiments.w3.verification.measure` reference; the second invokes
`semaphore_core.verification.parse_manifest` and `verify_pack`. Both receive the
same raw bytes. Each records only the vectors returned by its own trusted adapter,
then independently invokes that path's sampling/ranking functions for **every**
clue and all five samples. Comparison covers report identity/hashes/metrics and
diagnostics, candidate membership, full ordered IDs, target ranks and every raw
score. Only elapsed time is excluded. The absolute score tolerance is 1e-5;
rank changes still fail inside that tolerance. A rejection must agree on code.
Missing/empty rank audits fail. Threshold disagreements are visible through report
metrics and rank decisions; 0.85 remains a diagnostic, not publication authority.

The default embedder is deterministic text-only fake plumbing. It deliberately
returns the expected fingerprint to exercise identity guards but is always labeled
synthetic; it never looks up test-set target IDs or expected ranks. A real run uses
the existing Ollama adapter independently in each process, including its identity
checks. Aggregate artifacts contain hashes, counts and failure locations, not clues,
vectors or upstream response bodies. Worker streams are private IPC, not evidence
files. Errors never echo arbitrary subprocess stderr or submitted content.

`--backend reference` on parity is a same-implementation process-isolation smoke
test, explicitly marked `independent_implementation: false`. It cannot establish
core parity. Missing core imports and failed workers produce a nonzero exit; there
is no fallback to the reference or to fixture responses.

## Replay and robustness

Replay adapter factories receive a deep copy of each trace with `expected_state`
and `expected_result` recursively removed. `expected_revision` is preserved because
it is actual command input. Their `step(event)` returns precisely `result` and the
legacy `state` mapping. The harness alone compares those against the sealed fixture
expectations. This prevents an adapter accidentally echoing expected states. The
oracle is specification scaffolding, and a deliberately broken adapter test proves
the comparison fails. The integrated engine adapter is
`semaphore_core.trace:TraceReplay`, supporting explicit fixture-only initial overrides.

Traces cover in-flight and final retries, payload conflicts, busy admission, stale
revision, reconnect, equal-time spawn/overflow ordering, rejected clues, score and
terminal behavior. The HTTP robustness probe separately sends future revisions,
identical rejected retries, changed payloads under the same ID, a client-authored
score, a 121-character clue, unknown receipts and repeated quits. Schema-invalid
score injection must receive 400. Real HTTP envelopes are schema validated.
Oversized manifests (>8 MiB), malformed JSON, duplicate JSON keys, uploaded vectors,
missing license and an illegal test clue must reject **before any embedder call**.
There is no manifest upload endpoint in the frozen experimental HTTP contract;
these probes intentionally exercise the callable input boundary in fresh processes.

The reordered-delivery check repeats frames, reverses their delivery and applies
old responses after the latest state. The harness observer must retain the highest
revision and must not replace final receipts with delayed pending receipts. This
tests the probe observer, not G's browser; browser acceptance remains separate.

## Load procedure and timing limits

Load requires an explicit JSON argv for a verification subprocess. Configure
`SEMAPHORE_OLLAMA_BASE_URL` in the environment used by the server and load probe.
From an active virtual environment in PowerShell 7.3 or newer:

```powershell
$pressure = @('python', '-m', 'experiments.acceptance.verify_worker', '--backend', 'core', '--manifest-path', 'fixtures/w3/held_out-authored.json', '--ollama-env', '--pressure') | ConvertTo-Json -Compress
python -m experiments.acceptance.run load --base-url http://SERVER:8000 --artifact-id default --verification-command-json "$pressure" --rounds 10 --output load-real.json
```

The operator must configure the **same pinned model service** for server gameplay
and verifier pressure; record that configuration and machine/service identities.
The background command starts behind a barrier with 1, 4, then 8 independent HTTP
players and repeats until gameplay finishes. With `--pressure`, the verifier worker
reports its pinned fingerprint and monotonic embedding adapter intervals in private
IPC. The probe counts successful clue round trips that intersect those intervals.
An older worker emitting only `status: measured` fails the real-pressure check.
Use `load --synthetic` with injected fake embeddings to measure orchestration;
the report suppresses latency values and uses the verifier process interval for
overlap. The protocol has no verification route. Model-service queue fairness
requires separate instrumentation.

Each player creates its own game, sends one clue at a time, polls receipts to a
terminal result and retries the exact payload to detect double application. An
artifact must last long enough for the requested sample count; early game-over,
rejection, timeout, malformed envelopes or pressure failure is reported as failure,
not silently removed from the denominator. Clear and miss count as completed model
work; busy/overload/illegal/failure outcomes do not count as successful load samples.
The generic clue may be inappropriate for some packs: use an operator-preloaded
artifact for which it is legal. Default ID is `default`.

Client round-trip time starts before command submission and ends at observed final
receipt, including HTTP and polling delay. Default polling is 10 ms and recorded;
the browser's provisional 250 ms polling makes its visible latency a separate
measurement. Nearest-rank p50/p95 and maxima are reported at each concurrency.
Retries and create/quit calls are outside the clue sample interval. Optional server
headers `X-Semaphore-Queue-Ms` and `X-Semaphore-Embedding-Ms` on final receipts can
supply separate components. The frozen contract does not require these headers:
missing components have count 0 and null statistics, never fabricated zero time.
Do not subtract queue or embedding from round-trip and call the residual network
latency. A 100 ms timing result cannot close the gate if components/hardware are
unrecorded, pressure is unproven or the model is synthetic.

Record CPU/OS/RAM, GPU/offload status, Python and model versions, model fingerprint,
core commit, server invocation/artifact identity, cold versus warmed state, input
hashes, rounds and polling interval. Hardware utilization, offline startup and human
play observations are not measured by this tool and remain W5 work. LAN GPU timings
do not establish the CPU-only 8 GB release envelope.

## Independent leakage and trust review

The public W3 authored/weak/mixed packs reuse synthetic vocabulary whose retrieval
results were already visible. Separating process execution cannot restore an unseen
evaluation set. Mixed clues were selected without model scores, but neither they nor
the held-out label establish independently judged marginal-pack quality. Do not tune
the threshold on these probe results or relabel authored clues as human play evidence.

Creators control labels, embed context and test clues, and can overfit the declared
tests. Verified means recomputed tests only. Hold model/rules identities and decoy
policy outside upload control; recompute hashes and reports. Uploaded vectors and
self reports must not become scoring authority. The current rejection suite covers
uploaded vectors; W3 tests separately cover malicious self reports and semantic hash
independence. Context can encode an authored clue and inflate declared reachability;
no schema check can turn those clues into independent evidence. Independent creator
packaging, marginal/adversarial editorial review and later private real-play feedback
are still required for their respective gates.

An opaque disposable game ID is not production authentication. Browser score,
schedule, vectors, identity and revision authority stay server-side. Raw private
clues and upstream exception text stay out of public snapshots/aggregate probe
results. The fake has no authentication, inference, deadlines, schedule or queue
semantics and is never an acceptance service. Full account isolation, persistence,
publication ownership and private-log deletion are later-stage checks.
