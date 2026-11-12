# Wave 5 browser acceptance and playtest

November 11, 2026. Tested on Windows with Chromium through Playwright CLI 0.1.15.
The game server and browser shared the loopback origin 127.0.0.1:18739.

## Browser results

- Node browser-state and tutorial tests passed, 7 of 7. Chromium fixture checks
  covered keyboard and IME submission, Help, terminal focus, replay, themes,
  reduced motion, long labels at 320 CSS px, 200% CSS zoom, and the mocked
  request-loss retry path.
- The actual HTTP binding, inference worker and reducer were exercised with
  controlled unit vectors that map authored clues to pack entries. The smoke
  server kept the default six starting entries, then scheduled three arrivals
  five seconds apart before pace adjustment. The synthetic provider presents
  the frozen fingerprint for artifact validation. This fingerprint does not
  establish that a live model ran.
- The warm-up held its target through an incorrect input and more than one
  normal arrival interval. Completing the examples waited for Start game.
  An intentionally dropped create request showed a retryable error in place.
  The next attempt started a server game at zero. A target-name rejection
  preserved the draft and score.
- The browser submitted a legal clue and deliberately lost its HTTP response
  after the real server accepted it. Receipt reconciliation awarded the clear
  once. Reload restored the same game, 100 points and the unsent draft. Four
  further clues advanced the streak and triggered a fifth-clear sweep and
  cascade. The browser reached a natural server ending and displayed its
  authoritative 800 points for eight words cleared. The server reported
  pack_exhausted at 20,234 ms of observed elapsed time. The deliberately lost
  response needed one command POST and a receipt lookup.
- A separate fresh game at 390 × 844 CSS px skipped the warm-up. Its clear
  feedback remained visible with reduced motion and the board did not
  animate. Physical mobile keyboard and assistive technology are untested.

Fixed three browser issues during acceptance. A failed server start from the
completed warm-up now keeps the warm-up visible with a retry button and error.
Tutorial polling preserves the typing prompt. The final summary counts words
removed, including sweep and cascade bonuses.

## Repeat the browser check

From the repository root, with its development environment installed:

```powershell
New-Item -ItemType Directory -Force output/playwright | Out-Null
$env:PYTHONPATH = (Get-Location).Path + ';' + (Join-Path (Get-Location) 'packages')
uv run --no-sync python tests/web/serve-browser-smoke.py
```

In a second terminal:

```powershell
npx --yes --package @playwright/cli playwright-cli -s=w5-browser open 'http://127.0.0.1:18739/web/?transport=http'
npx --yes --package @playwright/cli playwright-cli -s=w5-browser run-code --filename=tests/web/browser-live.js --raw
```

For real-model acceptance, run the [standard game server](../../experiments/game_server/README.md)
with the calibration-authored manifest, the pinned Ollama origin, the repository
web root and port 18739. Run the same browser check from a new session and
record its output and the server's model identity. The five scripted authored
clues are a smoke sequence. If one misses, record the receipt and continue a
short run through game over. The larger real pack can take about two minutes
to finish this check.

## Human playtest protocol

Run one short session each with at least three volunteers on the real-model
server. Have each person play through game over, then offer a second run using
the warm-up skip. If a phone is available, use one phone session to observe the
physical keyboard and scrolling. Give the goal in one sentence, then let the
player choose their own clues. Offer help only when asked and record the prompt.

- Ask each player to point to the target and predict what the clear zone does.
- Observe a rejection or miss, a reorder, a clear and the ending. Ask why the
  clue had that outcome, what moved, and why the game ended. Record when any
  event fails to occur. If someone reaches a sweep, ask what they think caused it.
- Ask whether the pace left room to think, which outcome felt surprising,
  and whether they would play again. Use participant labels P1–P3 and record
  device, warm-up choice, score, observed confusion and willingness to replay.
  Record raw clues only with participant consent.

## Open gates

**Real-model browser game** remains open. The configured LAN Ollama endpoint
refused TCP connections (Windows error 10061) during the Wave 5 preflight.
No real model startup or real clue result was observed in this browser run.

**Human feel** remains open. Zero participant sessions were recorded. Whether
players understand target selection, rejection, reordering and loss, and whether
the selected model's results and pace feel fair enough to keep playing, remain
unanswered.
