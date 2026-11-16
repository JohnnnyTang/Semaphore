# Stage 2 W4 HTTP probe first slice

November 16, 2026. Baseline: `871184892bfa6e4f9a007060394463a797b0097e`.

Added an opt-in HTTP load runner for operator-prepared disposable accounts and an
accepted artifact. Sequential 1/4/8-player cohorts exercise actual cookie/CSRF HTTP
transport, game creation, commands, receipt polling, exact retries and cleanup.
Reports retain partial failures, early endings, successful p50/p95, cohort pins
and declared server revision. Missing observations cannot pass the latency gate.

Offline self-checks cover concurrency/counts, exact retries, rejection accounting,
pending timeout retention, failed starts, duplicate-account rejection, and a real
loopback HTTP server's cookies/CSRF and redirect refusal. These are synthetic
runner checks, not a deployed-model load run. No model endpoint was contacted.

Validation: six focused pytest checks pass; Ruff check/format pass. Usage and
measurement definitions are in the [probe README](../../experiments/durable_acceptance/README.md#w4-opt-in-authenticated-http-load).

Remaining: actual signed-in real-model measurements, verifier overlap and
queue/resource instrumentation, restart-linked HTTP observations, human play and
all inherited Stage 1 gates. No Stage 2 completion or performance pass is claimed.
