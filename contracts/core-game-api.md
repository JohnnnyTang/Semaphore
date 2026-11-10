# Callable experiment engine and transport API

W4 implements `semaphore_core.game` with immutable dataclasses and no HTTP, clock,
model process or filesystem side effects. Public signatures (Python 3.12):

```python
initial_state(artifact: GameArtifact, *, game_id: str) -> EngineState
advance(state: EngineState, *, now_ms: int) -> Transition
submit(state: EngineState, command: ClueCommand, *, now_ms: int,
       inference_slot_available: bool) -> Transition
complete(state: EngineState, *, command_id: str, now_ms: int,
         scores: Mapping[str, float] | None, error: str | None = None) -> Transition
quit_game(state: EngineState, *, now_ms: int) -> Transition
snapshot(state: EngineState, *, now_ms: int) -> dict[str, object]
```

`GameArtifact` is a validated immutable value containing `mode`, `identities`,
`entries` (ID -> label, aliases, forbidden, inflections), `initial_board`, `schedule`
(ordered at_ms/entry_id records), `deadline_ms`, `capacity`, `zone_size` and optional
initial fixture overrides in TEST MODE ONLY. Real artifacts derive lexical forms from the shared reviewed policy; arbitrary manifest inflections are forbidden. No random selection occurs in reducers. Reject invalid
artifacts rather than repair them. Identity fields have the exact schema names.
`ClueCommand` has the three fields of http.schema.json command. `EngineState`
contains the snapshot fields plus private immutable receipt/payload maps, used IDs,
and scheduled deadlines. Never expose clue payloads in snapshots.

`Transition` contains `state: EngineState`, `receipt: dict | None`,
`effects: tuple[InferenceRequest, ...]`, `changed: bool`. An InferenceRequest holds
`command_id`, model input text preserving case per shared encoding policy, target ID, admitted time and timeout time.
Only first admission emits it. Caller executes embedding outside the reducer.
`advance` drains schedules/timeouts and may finalize pending receipts in state;
transport resolves receipts from the resulting state. All entry IDs in `scores`
must exactly equal the current board; reject nonfinite scores and malformed worker
results as inference_failed. A late/unknown/already-final worker result is ignored.
Server computes board scores from a returned vector against current pack vectors;
clients cannot call completion or supply scores. Engine tests may supply scripted
scores. `snapshot` requires a state already advanced to now_ms and does not mutate
it; backwards time is an error. Functions never mutate their inputs.

Replay W2 game traces through these functions using synthetic scores and compare
all legacy state fields. Replay protocol fixtures through HTTP or a fixture transport
without importing an actual model. These are required independent entry points for
frontend and parity/load workers; no server import is needed for engine tests.
Shared rank, legality and verifier interfaces are defined in `core-verification-api.md`.

## HTTP binding

`openapi.json` defines only the experimental routes. Same-origin local LAN service,
no production login, registration, upload, publication, leaderboard or private-log
API. Artifact IDs resolve operator-preloaded artifacts; never accept client-authored
score, identities, schedule or entry vectors. Game IDs are server-generated opaque
unguessable identifiers for this disposable experiment, not production auth.

POST games returns 201 initial envelope. GET game advances clock and returns 200
snapshot envelope. POST commands returns 202 only for pending receipts (including
identical pending retry); all final/rejected command outcomes return 200 with current
snapshot and structured receipt. Schema-invalid input returns 400; request body
byte limit violations return 400 invalid_request. Oversized legal-domain clues up
to transport schema limit return a cached clue_too_long receipt, not parser failure.
GET receipts returns 200 current snapshot plus cached receipt; unknown command is
404 receipt_not_found. POST quit returns 200 final snapshot, finalizing pending
receipt; repeating quit is a no-op. Expired game always returns 410. No route is
allowed to accept a client score or a revision increment.

The browser polls GET game every 250 ms while visible and pending or active; the
period is a provisional UI choice, never game timing authority. GET receipt resolves
uncertain submissions. Retry EXACT original payload on transport uncertainty;
new IDs require deliberate user submission after snapshot reconciliation. Apply
only snapshots with revision >= latest local revision; command receipts may still
resolve pending input at older applied revisions. Keep a seen command-ID set to
suppress duplicate result animations. Every snapshot includes the immutable `entries` map (ID -> label), including all scheduled entries, so frontend label resolution requires no invented endpoint. No network font or model download is required.

Clue normalization is for legality only. Preserve case and model preprocessing for
inference exactly as core-verification-api.md specifies; do not embed casefolded tokens.

The service first calls advance(now_ms), then computes scores against the resulting
current board, then calls complete at that same logical timestamp. Embedding vector
arrival does not itself authorize scoring against an admission snapshot. A worker
error accepts only inference_failed or inference_timeout; never expose exception text.
All reducer ordering is synchronous under a per-game serialization boundary.
