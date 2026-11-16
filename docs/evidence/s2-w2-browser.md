# W2 browser evidence

November 16, 2026. Worker baseline `8ac07292ed469be28f755edd28dd4e711ed79c75`.
State: implemented and fixture-tested; pending coordinator integration.

`/web/durable.html` adds signup/login/logout, registration config, installed artifact
selection, private clue disclosure, authoritative snapshots/commands/receipts,
current-game discovery, terminal results/history and exact-artifact boards. The
existing `/web/` experiment remains unchanged. All requests are same-origin and
uncached; mutations carry the current session CSRF token. Logout is a bodyless POST.
No passwords, tokens or clues are written to localStorage, URLs or console.

Uncertain creates never retry automatically. Discovery returning 404 leaves the
uncertainty explicit; only the separately labelled user action permits another
create. Uncertain clues retain their exact ID, original payload and revision in
memory; explicit retries reuse that payload. Same-game discovery preserves pending
commands and seen receipts. Monotonic GameStore application prevents rewinds and
receipt replay. Authentication generation guards discard old-account responses.
An expired session clears private rendered lists, game state and CSRF. Opaque page
cursors stay scoped to their view; changing artifact clears board pagination.

Design: retain the existing signal-blue (#355cff), navy (#18294a), pale-blue
(#edf2fa), mint-zone (#d5f3ed) and white palette. Bahnschrift headings/word labels
and Segoe UI controls preserve the experiment identity. The left-aligned word stack
is the main activity, with quiet account controls above and results/board below.
A responsive single-column layout, target text and visible focus support small
screens and keyboard use. No animation is required to update game authority.
Visual review caught and fixed inherited clue-input border and word-height rules.

Validation:

- `uv sync --locked --group dev`: passed in isolated worker environment.
- `node --test tests/web/*.test.mjs`: 20 passed (13 durable, 7 existing).
- `uv run --no-sync ruff check .`: passed.
- `uv run --no-sync ruff format --check .`: passed, 127 files.
- `git diff --check`: passed.
- Playwright CLI actual Chromium fixture journey: passed sign-in, escaped malicious
  display name, keyboard start/clue, pending/final receipt polling, authoritative
  score, exact board rendering, 320px no-overflow, reduced-motion and logout cleanup.
  Harness: `tests/web/browser-durable.js`; screenshots reviewed in ignored
  `output/playwright/durable-mobile.png` and `durable-desktop.png`.

Reproduce: serve repository root with `python -m http.server 18742 --bind 127.0.0.1`,
open `http://127.0.0.1:18742/web/durable.html` using Playwright CLI session `s2-w2-d`,
then `playwright-cli -s=s2-w2-d run-code --filename tests/web/browser-durable.js`.
The harness intercepts `/api/v1` with frozen synthetic payloads; the static server
alone does not implement the API. FixtureTransport supports scripted network/error
sequences for Node checks and makes no authentication/durability claim.

Limits: pending clue bodies are memory-only; reloading loses an unacknowledged
command payload, so recovery uses current-game discovery and server pending receipts,
never invents an automatic retry. W4 still requires real HTTP wiring, human play,
actual persistence/restart/deletion and live model evidence. Stage 1 carryovers
remain open. No synthetic fixture score is publication or competitive acceptance.
