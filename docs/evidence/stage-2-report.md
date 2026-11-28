# Stage 2 acceptance report

Latest November 16 correction: keep-alive model transport and stale-clue draft
recovery are implemented. Final isolated 1/4/8-player p95: **329/641/735 ms**,
with two eight-player stale rejections; all restart checks passed. Validation:
487 Python tests, 27 Node tests, lint/format/build/diff passed. **W4 remains open**:
100 ms target unmet; offline startup remains explicitly deferred; inherited
reference-resource and human/content gates remain unfulfilled. See the
[latest correction](../evidence/s2-w4-performance-correction.md#latest-correction--persistent-model-transport).
Earlier measurements below remain historical evidence.


November 16, 2026. Disposition: **revise within W4**. Durable product acceptance
has substantial passing evidence, but the real-model performance gate failed.
Stage 2 and inherited Stage 1 gates are not declared complete; no Stage 3 dispatch.

## Observed product and persistence

The owner completed a real-model browser game: 1,000 points, level 3,
`pack_exhausted`. After an actual server process restart, the owner confirmed the
same 1,000-point result in private history and the exact round board. A read-only
before/after SQL comparison found one unchanged score row. Signup initially failed
with generic `invalid_request`; field validation and visible account requirements
were corrected, and the owner successfully retried. Polling now uses a guarded
250 ms interval instead of 1.5 seconds. See [human evidence](s2-w4-human-playtest.md).

The fresh-install acceptance run passes locked dependencies from an empty cache,
installed-wheel resources/CLI outside source paths, supported migration checks and
separate cached-offline installs. Cached wheel resolution initially lacked metadata;
that limitation is retained in [installation evidence](s2-w4-installation.md).
This does not establish a portable offline release bundle or remote-model isolation.

The real-model orchestrator also passed natural-result snapshot/history persistence,
exactly-one score, and restart interruption of an active game without a score.
Existing W3 independent crash/deletion/restore evidence remains applicable.

## Controlled model run

A fresh trusted installation of the exact authored MIT Everyday discoveries pack
used pinned Qwen3-Embedding 4B. One warmup per player is retained but excluded from
latency; each player then attempted five measured commands. Repeated actual pack
verification overlapped measured commands in every cohort. Timings are command
POST through final receipt, including polling, over loopback HTTP and a remote
Ollama endpoint. This is a small diagnostic sample, not release certification.

| Concurrent players | Successful / measured | Successful-command p50 | Successful-command p95 | Outcome |
| --- | --- | --- | --- | --- |
| 1 | 5 / 5 | 594 ms | 625 ms | 100 ms target missed |
| 4 | 20 / 20 | 937 ms | 1,344 ms | 100 ms target missed |
| 8 | 28 / 40 | 2,093 ms | 2,406 ms | 12 stale-revision rejections; target missed |

Failures remain in [retained results](s2-w4-real-results.json); percentiles exclude
failed outcomes and must be read with the counts. The revision argument contained
a coordinator transcription error, corrected against observed Git HEAD with the
original value and raw-report hash retained. No runtime source changed during the
run. Remote CPU/GPU/RAM was not collected. Initial local resource sampling captured
a Windows virtualenv launcher rather than its interpreter child and is marked
invalid; it cannot establish the hub resource envelope.

## Remaining work and decision

Investigate queue/model latency and scheduled-state races under eight-player load,
then rerun the same controlled acceptance with unchanged 100 ms target. Preserve
exact-revision command semantics; do not hide stale commands by silently rewriting
retries. Collect valid local process-tree and remote model resource evidence,
remote-host offline startup, broader human observations and independent content
review/source-yield evidence. The single owner round does not replace those gates.

Regression: 482 Python tests, 27 Node tests, lint, formatting, source/wheel build
and targeted signup browser validation passed. No changes pushed.

The process-tree resource sampler has since been corrected and verified against
the idle human host without model traffic. The next controlled load should collect
valid resource evidence with that sampler. The first run remains unchanged and
its launcher-only measurements remain invalid. Thirteen focused acceptance tests
passed after this final instrumentation change; the earlier full suite had 482 passes.


## Performance/resource follow-up — November 16

Clock-only GET/tick no longer rewrites durable game snapshots. Full regression:
484 Python tests and 27 Node tests passed; lint/format/diff checks passed. Two
controlled reruns retained all failures; the repeat p95 was 610/906/1,484 ms for
1/4/8 players, with four eight-player stale-revision rejections. Restart checks
passed. Local and remote model process-tree/GPU measurements are now retained,
with sampling limitations; resource-envelope acceptance is not declared. The user
explicitly deferred remote offline startup. W4 remains open with the unchanged
100 ms target. See [correction evidence](../evidence/s2-w4-performance-correction.md)
for source hashes, results, resource scope, and next work.
