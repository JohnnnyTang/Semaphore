# Semaphore browser experiment

A dependency-free browser client for the frozen `experiment-v1` transport. All
assets, including the flag favicon, are local. No build or package install is needed.

## Launch

From the repository root, start a static server:

```powershell
python -m http.server 18737 --bind 127.0.0.1
```

Open http://127.0.0.1:18737/web/ and choose **Scripted practice**. The static
server must serve the repository root, because practice reads the promoted
`/fixtures/protocol/*.json` evidence. A production asset server is outside this scope.

Practice pauses at the next recorded command. Each explicit clue submission
advances that command, then polling advances its pending/completion/spawn frames.
The submitted clue does **not** determine its recorded result. Scores, boards,
targets, ranks and endings come directly from frozen envelopes. Only command IDs
are rebound to browser-generated IDs. A sequence without a terminal frame ends
with **Practice sequence complete**, preserving its last recorded score.

For real play, launch the experiment server using its documented command with
`--web-root <absolute repository root>`, then open its `/web/?transport=http`.
Choose **LAN game server**, artifact ID `default`, and a supported mode. An operator
may preload another artifact; use `?transport=http&artifact=other-id` or edit the
Artifact ID field. HTTP and assets must share an origin. This browser never calls
Ollama or sends scores, embeddings, target IDs, entry lists or schedules.

## Transport and state

`transports.mjs` implements create, snapshot, command, receipt and quit against
`/experiment/v1/games`. `store.mjs` applies only nondecreasing revisions and elapsed
times, while an older receipt can still resolve its matching pending command.
Every accepted envelope replaces the full snapshot; the next 250 ms poll obtains
a fresh snapshot even after a revision gap. Seen command IDs prevent duplicate
result presentation. The playfield animates authoritative board changes: new words descend over
1.1 seconds and reordered words settle over 650 ms. Identical polling snapshots
do not restart motion. Authoritative state is never blocked by animation.

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

Six dependency-free tests exercise Unicode code points, one pending command,
out-of-order snapshots, older matching receipts, duplicate suppression, terminal
state, frozen fixture replay, HTTP payloads and structured error handling.

Browser checks use the Playwright CLI (an optional development tool, never a runtime
dependency). With the static server above running:

```powershell
npx --yes --package @playwright/cli playwright-cli -s=semaphore-g open http://127.0.0.1:18737/web/ --headed
npx --yes --package @playwright/cli playwright-cli -s=semaphore-g run-code --filename=tests/web/browser-smoke.js
npx --yes --package @playwright/cli playwright-cli -s=semaphore-g run-code --filename=tests/web/browser-reconnect.js
```

See [QA.md](QA.md) for measured coverage and limits.

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

The default scripted preview now uses web/practice/spacious-arcade.json.
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
