# W4 real-model orchestration readiness

November 16, 2026. Integrated input baseline:
`b7f686ad2c0c33a28761b2d84c00574e63ed5e61`.

The opt-in `experiments.durable_acceptance.real_run` runner now prepares a fresh
private installation using the real trusted installer, independent generated keys,
eight disposable accounts and the pinned provider. It launches the durable host
and a real verifier in separate processes, runs the 1/4/8 HTTP cohorts, and records
model-call and cohort intervals. Overlap is established only by completed
successful model calls intersecting the actual load interval. Unfinished verifier
calls and process exit state remain visible.

The restart phase checks a naturally ended game's unchanged snapshot/history and
one score row, then verifies an active game becomes interrupted without score.
Local hub process CPU/RSS sampling is optional when psutil is installed; remote
model resources and queue timing remain unmeasured.

Offline validation covers real SQLite/account/key/asset provisioning with a clearly
synthetic substituted verification result, telemetry failure privacy, interval
overlap rules, incomplete final telemetry, subprocess invocation and failure report
retention. These tests do not establish real-model behavior or performance.

No model endpoint was contacted by this worker. Actual execution is held while the
user plays on the coordinator's real-model host. Human acceptance, measured model
load and all inherited performance/content/offline gates remain open until the
coordinator records observed evidence. See the [runner instructions](../../experiments/durable_acceptance/README.md#fresh-real-model-orchestration).


## Executed measurement

The coordinator executed the real run at verified source `b6e8046a45dcfce6910efd7218b9966368dd227a`.
See [retained results](s2-w4-real-results.json) and [acceptance report](stage-2-report.md).
The report retains a corrected revision-argument transcription error and the raw
report hash. Thirteen warmups succeeded and are excluded from 65 measured attempts.
Successful verifier intervals intersected 5/5, 20/20 and 15/40 measured commands
in the 1/4/8 cohorts; cohort overlap does not mean every command overlapped.
One verifier pass completed before the next pass was stopped. The 12 eight-player
failures were stale_revision, consistent with the contract advancing scheduled
state before checking expected_revision. A GET-to-POST race under load is a plausible
explanation, not a demonstrated root-cause profile. No inference timeout or score
corruption is established by these rejections.

The initial local CPU/RSS sampler observed the Windows virtualenv launcher only;
those samples are invalid for hub resource claims. Remote resources remain unmeasured.

## Resource instrumentation correction

Commit `eed4531` samples the launched process plus recursive interpreter children,
retaining per-process identities and summing RSS/CPU. Six sampler/orchestrator tests
passed in the worker and thirteen focused acceptance tests passed after integration.
A read-only idle check of the actual human host found launcher PID 15996 and
interpreter PID 64976, with approximately 50 MB total RSS across five samples.
No HTTP/model call occurred in that check. This validates the process selection
fix only; it does not replace the failed load-time resource measurements.
