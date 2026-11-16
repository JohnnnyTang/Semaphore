# Semaphore browser experiment

A dependency-free browser client for the frozen `experiment-v1` transport. All
assets, including the flag favicon, are local. No build or package install is needed.

## Launch

Launch the experiment server with `--web-root <absolute repository root>` using
[the server instructions](../experiments/game_server/README.md), then open `/web/`.
Choose a game mode supported by the loaded word pack. The default pack ID is
`default`; use `?artifact=other-id` or the Word pack ID field for another loaded pack.
HTTP and assets must share an origin. This browser never calls Ollama or sends
scores, embeddings, target IDs, entry lists or schedules.

The optional guided warm-up works without a server and waits for the three example
clues. Starting the actual game requires the server. Scripted practice and its
scenario picker have been removed; old `transport` query parameters are ignored.
Recorded protocol fixtures remain development evidence for automated tests only.

For browser QA without Ollama, run the synthetic test server from the repository:

```powershell
$env:PYTHONPATH = "packages;."
.venv/Scripts/python.exe -m tests.web.serve-browser-smoke
```

Open http://127.0.0.1:18739/web/. This server uses authored test vectors, not a real
semantic model, and is only for development checks.

## Transport and state

`transports.mjs` implements create, snapshot, command, receipt and quit against
`/experiment/v1/games`. `store.mjs` applies only nondecreasing revisions and elapsed
times, while an older receipt can still resolve its matching pending command.
Every accepted envelope replaces the full snapshot; the next 250 ms poll obtains
a fresh snapshot even after a revision gap. Seen command IDs prevent duplicate
result presentation. The playfield animates authoritative board changes: new words descend over
0.85–1.5 seconds from above the ceiling, remaining fully visible as they fall.
Reordered words settle over 650 ms. The chute stays bottom-anchored; unchanged rows
retain their DOM nodes and in-flight animations across arrivals and polling snapshots. Authoritative state is never blocked by animation.

One pending command retains its text read-only, with Send disabled. Uncertain POSTs
reconcile through GET snapshot and GET receipt; only `receipt_not_found` retries
the exact original ID, clue and expected revision. A new ID requires a new explicit
submission. Server game ID, draft, pending payload and seen receipts are kept in
sessionStorage for this tab's reload recovery, removed on Leave or a new game.
No clue is written to a URL, console or persistent localStorage. Storage failure
still permits play but loses reload recovery. Leaving during a network outage
exits locally; it cannot stop the server clock. Expired/interrupted games never
create a local official result.

## Checks

```powershell
node --test tests/web/client.test.mjs
```

Dependency-free tests exercise Unicode code points, one pending command,
out-of-order snapshots, older matching receipts, duplicate suppression, terminal
state, HTTP payloads and structured error handling.

Browser checks use the Playwright CLI (an optional development tool, never a runtime
dependency). With the synthetic QA server above running:

```powershell
New-Item -ItemType Directory -Force output/playwright | Out-Null
npx --yes --package @playwright/cli playwright-cli -s=semaphore-g open http://127.0.0.1:18739/web/ --headed
npx --yes --package @playwright/cli playwright-cli -s=semaphore-g run-code --filename=tests/web/browser-smoke.js
npx --yes --package @playwright/cli playwright-cli -s=semaphore-g run-code --filename=tests/web/browser-reconnect.js
```

See [QA.md](QA.md) for W4 browser coverage and [W5 browser acceptance](../docs/evidence/w5-playtest.md) for the HTTP smoke check and human playtest protocol.

## Frontend refinement

The signal arcade layout places the clue dock below the board. The striped ceiling
marks capacity; empty slots shrink as the authoritative board fills. The highlighted
bottom range is driven by the server's zone_size, with rank 1 at the bottom.
Only the flagged target can clear. This is discrete arrival/ranking motion, not
a new continuous falling-word ruleset.

Light and dark themes follow the system on first load. A chosen theme is stored
locally under semaphore-theme; clue text is never stored with that preference.
Reduced-motion mode disables arrival, reorder, headroom and score animations.
No fonts or other assets are fetched from external services.

Additional browser verification:
npx --yes --package @playwright/cli playwright-cli -s=refine run-code --filename=tests/web/browser-refine.js

## Spacious arcade rules

New casual games use 20 positions with six initial phrases, leaving 14 empty
positions. Positions 1–3 form the clear range: the target does not need to be the
single closest association. Clearing still removes only the target for 100 points.

The paced casual ruleset is experiment-arcade-paced-v1. Every five clears
(500 points), base arrival intervals decrease by 10 percentage points, down to
40% of base. With the default five-second interval this gives 5, 4.5, 4, 3.5,
3, 2.5, then 2 seconds. A level-up proportionally shortens the remaining time
to the next arrival. The last arrival leaves five seconds before pack exhaustion.
Event artifacts and old recorded traces retain their existing fixed schedules.

Browser tests use the recorded evidence in web/practice/spacious-arcade.json.
Regenerate it with:
python -m experiments.game_server.generate_practice
This recording comes from the reducer with authored ranking scores. It demonstrates
the larger board and third-place clears, but does not evaluate a player's clue.

## Guided warm-up and special clears

Before either transport starts, an optional local warm-up introduces moon, wave,
and tree on the playfield. Contextual notes respond to typing. Only the example
clues advance its three steps; reads, time, and incorrect clues do not. No HTTP
session exists during this warm-up, so there are no arrivals, deadline, or overflow.
The pre-game checkbox bypasses it. After completion, Start game creates a fresh
normal session with zero warm-up score. Reloading a live HTTP session still resumes
that session directly.

Paced casual games count consecutive successful clue submissions. The fifth clears
the entire current ranked zone, then advances surviving ranked words into the zone.
The new ASCII-smallest target clears recursively if it is in the zone and the same
clue is legal for it. Future scheduled arrivals are not pulled forward. Each removed
word scores 100 exactly once. Bonus words do not charge another streak. Misses,
illegal submitted clues, and inference failures/timeouts reset the streak; busy,
stale, or overloaded requests do not count as attempts. Event and legacy fixture
rules stay unchanged. Receipt `clear_waves` describes removal order; `strike` marks
the sweep. Trails illustrate the waves without delaying authoritative state, while
reduced motion retains the textual result and suppresses the trails.

Run `node --test tests/web/*.test.mjs` and
`python -m pytest tests/game tests/contracts/test_game_contracts.py -q`.
The browser regression is `tests/web/browser-tutorial.js` (Playwright CLI run-code).

## Arrival motion regression

Run `tests/web/browser-motion.js` with Playwright CLI against the static preview.
It mocks HTTP snapshots to check visible descent, stationary settled rows, overlapping
arrivals without animation restarts, desktop sizing through 2560px, mobile overflow,
and reduced motion. Desktop text scales to 26.4px and slots to 52px on tall displays.


## Interface and lifecycle refinement

The welcome screen retains the signal-blue arcade identity with a straight word
stack, clear host-supplied word pack guidance, and an explicit untimed warm-up.
Help presents the three gameplay steps first, with streak and mode details folded
below. Keyboard users have a skip link and a named help dialog; the clue field
reports over-limit input and pending work. Narrow controls wrap at 320px, while
large desktop rows retain their readable scale. Forced-color mode preserves the
target and clear-zone distinction.

Leaving returns to setup immediately, even when quit is delayed or unavailable.
Late polling errors and quit replies cannot change a replacement game. Malformed
HTTP error bodies follow the normal unavailable/reconnect path.

Run tests/web/browser-hardening.js with the Playwright CLI against the local QA
server to check delayed poll/quit isolation, immediate leave, welcome widths, and
help focus restoration. Existing browser-refine.js, browser-tutorial.js, and
browser-motion.js cover themes, warm-up, clears, desktop scaling, and reduced motion.
