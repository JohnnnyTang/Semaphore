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
