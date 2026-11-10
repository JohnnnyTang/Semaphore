# Experimental Arcade rules — experiment-arcade-v1

This W3 contract supersedes conflicting W2 wire drafts for the W4 experiment.
It does not freeze production accounts, publication, model quality or supported
hardware. See `core-verification-api.md` and the model lock for shared numeric
ranking, normalization and explicit lexical inputs. A scripted ranker is valid for
protocol work; its results are never semantic quality evidence.

The board is bottom first; rank 1 is index 0. Default initial size is 6, capacity
12, zone 3. Fixture overrides are explicit. Initial size must be positive and less
than capacity; zone is positive and less than capacity. IDs are unique. A spawn
appends to the board. Reaching capacity, including exactly 12, immediately ends
with `overflow`; a terminal snapshot may contain 12 words. An active one may not.
Target is initially and after each clear the ASCII-smallest surviving ID, remains
fixed across misses/spawns, and is null on an empty board. Only the target clears
when rank <= zone. Every clear awards 100; level = 1 + clears // 5. Score has no
other source. Rank against the current board at completion, including new spawns.
Ranked-board and target-rank receipt fields describe the board BEFORE removal.

Use the numeric total order in `core-verification-api.md`: descending bucket
floor(score / 1e-5 + 0.5), then ascending ASCII ID. No pairwise epsilon comparisons
or game-specific similarity threshold. Scripted trace scores are exact test inputs.
Labels must be resolved from the immutable artifact entry table, never from IDs.

Integer elapsed milliseconds come from an injected monotonic server clock.
At a timestamp process deadline first, spawns in artifact order next, inference
timeouts next, external commands/completions in assigned sequence order last.
Deadline is exclusive: a completion or spawn at the deadline cannot score.
Same-time scheduled work always beats HTTP admission/read/quit. Drain all due
work before a response. Revision starts at 0 and advances once per actual state
transition: admission, spawn, successful ranking (including a miss), inference
failure/timeout, terminal deadline or quit. A spawn that ends the game is ONE
transition; finalizing its pending receipt does not add a second revision.
Late worker results, rejected admissions, retries, receipt reads and snapshots
never change revision. Sequence orders wire envelopes even without revision changes.

Admission precedence: exact command-ID retry or conflict, ended game, pending
command (`busy`), stale revision, missing target, legality, global overload.
Store the complete original payload including raw clue and expected_revision.
Same ID and same payload returns the cached pending/final receipt; changed payload
returns `command_conflict` without replacing the original receipt. All admission
outcomes, including rejections, are cached. A corrected clue requires a new ID.
Only one inference per game is outstanding. Admission sets pending immediately;
pending contains its command ID, admitted target and admitted time. Worker input
is a clue vector request; completion ranks current IDs, not a stale admission board.
Infrastructure failure yields `inference_failed`; timeout yields `inference_timeout`.
Both clear pending, increment revision and become final receipts. They cannot later
succeed. Terminal transition immediately replaces any pending receipt with final
`game_over`, even before the worker finishes. No late score is allowed.

## Explicit provisional resource and replay choices

These are bounded experiment defaults, NOT measured latency or fairness claims:
8 globally outstanding inference requests (running plus waiting), one per game,
5000 ms from admission through queue and inference. Reject excess with `overloaded`
before admission. Timeout is inclusive and processed before same-time completion.
Gameplay clock never pauses. One FIFO inference worker initially; no verification
job may enter the gameplay queue. W4 load probes must report contention and timeout
rates before these values can be accepted for a supported release.

Retain full game state, payload/receipt map and artifact binding until 900000 ms
after terminal time. Active sessions have a maximum published duration of 600000 ms
and at most 4096 distinct command IDs. At the command limit return HTTP 503
`unavailable` before accepting a new ID; known-ID retries still work. Transport must
bound request size to 16384 bytes before JSON parsing. Once retention expires all
reads/submits return HTTP 410 `game_expired`; keep only a game-ID tombstone for the
process lifetime. Unknown IDs return 404. IDs are never reused. Restart invalidates
all in-memory sessions; no durable score or restart recovery is promised. Clients
show interrupted on lost server generation, never invent a competitive result.
Raw clue payloads are private; no command-list, creator-log or receipt enumeration API.

## Finite schedule and unresolved production gates

W4 uses immutable prebuilt artifacts for BOTH modes: entry table (labels, explicit
aliases/forbidden/inflections), initial board, unique spawn IDs and elapsed times,
deadline, config and identity digests. Artifact creation is offline, not gameplay.
Event artifacts are identical across players and independent of their boards,
clues, levels and latency. No skipped or replacement spawns, no ID reuse. Empty
event boards wait for schedule/deadline and end `event_complete`. Overflow ends
early. Casual experiment artifacts likewise predeclare their schedule; they make
no adaptive semantic diversity claim. This is an explicit narrow experiment scope.

The historical casual formula is not evaluated with floating-point pow in W4.
An adaptive casual generator (RNG, tier eligibility, aggregate similarity and
calibrated rejection threshold) remains BLOCKED on model evidence and is not part
of this ruleset. Do not silently implement a guessed .65/.45 cutoff. Future ruleset
changes require a new artifact/ruleset identity. Lexical tables are reviewed fixture
inputs; complete production English stem/lemma handling remains a separate gate.

Casual artifact deadline is last spawn + 5000 ms (or start + 5000 with no spawns).
After final spawn, clearing the board ends `pack_cleared`; otherwise deadline ends
`pack_exhausted`. Event deadline is explicitly published, greater than every spawn,
and <= 600000 ms. `interrupted` is used for explicit quit/operator interruption;
it is noncompetitive. Other reasons are `overflow`, `pack_cleared`, `pack_exhausted`,
`event_complete`. Disconnect alone changes neither game nor pending inference.

## Wire reconciliation

`events.schema.json` replaces draft running/terminal names with `active`/`over`,
ID-array board and nullable target. `pending` is gameplay state; `receipt` is a
separate immutable outcome for a command, with original `applied_revision`. Every
wire envelope carries a current full snapshot; its receipt may be older. Never
roll state backward to an old receipt. Never animate a command result twice.
Structured receipts include rank, pre-clear ranked IDs and score delta; no raw
similarity precision is needed in the browser. `sequence` is a game-local transport
counter; duplicate receipt requests can have a new sequence and identical revision.
Snapshot revisions cannot decrease within a stream. Snapshot reads do not advance
revision; elapsed time may advance. There is no incremental replay endpoint or SSE
buffer dependency: poll snapshots while pending and resolve an uncertain command
by ID. Gaps require a full snapshot, not invented transitions.

`fixtures/protocol/` promotes each W2 synthetic trace into full envelopes. Protocol
fixtures are checked against their original expected states by independent schema
and invariant tests. Identity strings explicitly identify synthetic fixtures; real
artifact digests must be checked by the service, not trusted because schema accepts
a string. Numeric ranking fixtures and game fixtures are complementary evidence.

## Paced casual extension

The paced casual configuration additionally binds `special_clear` into its config
digest. Five consecutive successful submissions trigger a zone sweep. Remove the
current ranked zone simultaneously, compact the surviving ranked board, select its
ASCII-smallest ID, and remove that target while it is within the refilled zone and
the original clue passes legality for it. Stop at an empty board, an out-of-zone
target, or an illegal clue for the new target. Never consume future scheduled spawns.
Each removed ID earns 100 points once; all waves are one atomic completion/revision.
The finite ranked board bounds the loop. Successful clue submissions, not bonus
words, charge the streak. Sweep resets it to zero. Misses, illegal clue admissions,
and inference failure/timeout reset it. Illegal admissions in this extension advance
revision; infrastructure admission rejections preserve the streak. Optional snapshot
`streak` and receipt `strike`/`clear_waves` report this behavior. Event and unpaced
rules above remain frozen. The optional browser tutorial precedes session creation,
so its instructional waits do not pause or alter an authoritative game clock.
