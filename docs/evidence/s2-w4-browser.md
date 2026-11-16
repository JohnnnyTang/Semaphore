# Stage 2 W4 browser integration

November 16, 2026. Worker baseline: `871184892bfa6e4f9a007060394463a797b0097e`.

Compared account, installed-pack, games/receipts and result/board routes against
actual hub HTTP adapters. Endpoint/body/response projections match the frozen
client. The clear-zone display did not: the durable page highlighted the last
three board entries, while the reducer ranks clear positions from 1. The page now
marks ranks 1 through zone_size and includes visible clear-zone text.

LAN HTTP does not expose secure-context-only crypto.randomUUID. Command IDs now
fall back to cryptographic getRandomValues with UUID v4 version/variant bits,
while retaining the same exact retry behavior. Navigation stays on durable.html
instead of linking to an unserved experiment. Privacy disclosure explicitly says
backup retention can extend beyond deletion by an additional 30 days.

Added a Playwright CLI real-service flow in tests/web/browser-durable-live.js:
signup, installed artifact selection, command/receipt settlement, natural terminal
result, exact board, reload, mobile/reduced-motion and logout. It creates test
accounts/scores and is restricted to disposable acceptance installations. No API
route is mocked. It requires a preinstalled short accepted artifact and signup.

Validation in this worker: 25 Node tests passed, including explicit rank-zone and
LAN HTTP UUID regressions; git diff --check passed. The new live-service runner
has not been executed in this worker. Coordinator must run it after static host
integration and disposable installation provisioning, recording model identity.
Human, real-model latency, server restart and release gates remain open; the
runner does not claim those checks.
