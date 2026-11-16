# Stage 2 acceptance report — interim

November 16, 2026. Disposition: continue bounded W4 acceptance; do not close Stage 2
or dispatch Stage 3 yet.

W4's first parallel integration slice connects the durable browser to the actual
HTTP service, corrects clear-zone/command-ID behavior and supplies independent
HTTP load and operator CLI acceptance tools. See the [W4 record](../stages/s2-w4-acceptance.md)
for the common baseline, ownership, worker commits and validation.

An automated Edge flow against disposable SQLite and the real durable listener
passed signup, authoritative clue receipt, natural completion, history, exact
leaderboard, reload, mobile layout and logout. Verification and query vectors
were synthetic. This proves transport/product wiring, not real-model or human
acceptance. Existing W3 crash/restart evidence remains separately labeled.

Fresh-schema and supported migration checks, deletion-aware encrypted restore,
missing-ledger/host-lock failures and restore overwrite refusal passed through
CLI entry points. The runbook now describes local secret/bootstrap setup and
same-origin browser serving. The listener remains loopback-only; LAN deployment
and a fresh locked/offline installation are not established by this slice.

Remaining evidence includes a signed-in person's real-model game with result
retrieval after restart; controlled 1/4/8-player real-model load with verifier
pressure and resource measurements; remote-host offline readiness; independent
content review and source-yield evidence. The inherited 100 ms p95 target remains
unchanged. The HTTP runner reports missing evidence explicitly and cannot close
these gates by receiving a synthetic successful response.

Integrated validation: 476 Python tests and 25 Node browser tests passed, along
with lint, formatting, wheel/source build and diff checks. Detailed commands and
scope are recorded in the W4 ledger. These checks do not close the outstanding
real-model/human acceptance boundary.
