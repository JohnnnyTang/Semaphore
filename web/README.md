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
result presentation. Animation uses a receipt's ranked board only when its revision
matches the current snapshot, and a later snapshot cancels the presentation.
Authoritative state is never blocked by animation.

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
