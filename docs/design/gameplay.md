# Arcade gameplay and fairness draft

Status: S1-W2-C proposal, November 8, 2026. This specifies an experiment, not a
frozen public protocol. Inputs are the handoff, W1 decision ledger and project
plan. Synthetic replay evidence lives in `fixtures/game_traces/`; no real-model
quality, human enjoyment or latency result is implied.

## State and rank vocabulary

The server owns game state, clock, command receipts and score. A game pins pack
version/content, embedding fingerprint, ruleset and configuration. Event games
also pin a challenge schedule digest. Those identities never change mid-game.

The ordered `board` is **bottom first**: index 0 is the most related word after
ranking and has rank 1. This is the existing `FakeRanker` return order. The browser
reverses it for top-to-bottom drawing. The clear zone consists of indices
`0..min(zone_size, len(board))-1`; reachability uses rank <= zone_size, never the
last three values in a descending similarity list. Rank is measured before clear.

The replay state contains `status` (active/over), `board`, `target`, `score`,
`clears`, `level`, `revision`, `next_spawn_index`, `pending` and `end_reason`.
Pending contains command ID, original target ID and admitted time. The server
also retains command payloads/receipts for idempotency; they are transport state,
not public gameplay state. Clock time belongs in the event envelope. A snapshot
contains every gameplay field, plus identities and server time in the eventual
W3 protocol. Revisions start at 0 and advance once per state-changing event.

## Initial values and transitions

| Item | Draft rule |
| --- | --- |
| Start | Six unique entries, capacity 12, clear zone 3; fixtures use small overrides |
| Target | Lexicographically smallest surviving entry ID, independent of visual order |
| Score | 100 per cleared target; no other word clears and no bonus |
| Level | `1 + floor(clears / 5)` |
| Spawn | Append at the top (end of bottom-first board); preserve existing target |
| Overflow | A spawn that makes board length **equal to** capacity ends the game immediately |
| Clear | Rank all current entries, remove target only if its rank <= zone, choose next target |
| Miss | Keep ranked board and target, score unchanged |
| Empty board | If future spawns remain, stay active without target; next spawn becomes target |
| End | No mutation by later clue commands; repeated snapshot reads are harmless |

Reaching the top means reaching capacity, consistent with the handoff. A clue
cannot rescue a board at that same timestamp. Initial configuration must satisfy
`1 <= initial_count < capacity`, `1 <= zone_size < capacity`, and unique IDs.
Only entry IDs select targets; human labels may contain spaces and punctuation.
The target stays fixed on a miss or a spawn. After a clear, the smallest surviving
ID becomes target. This deliberately simple policy is reproducible; its feel is a
W5 playtest question. No outcome waits for browser animation completion.

Exact score ties use ascending entry ID. W2 traces use exact scripted scores.
Do not implement pairwise epsilon comparisons: they can be non-transitive. W3
must choose an evidence-supported total-order policy for real near ties (for
example fixed quantization followed by ID) and test threshold boundaries.

## Clock, admission and inference

Use integer elapsed milliseconds from a server monotonic clock. Wall-clock dates
are metadata only. Every input has a server-assigned sequence number; client time
cannot reorder inputs. At each timestamp drain scheduled work first, then process
external inputs in server sequence order. Specifically: deadline, spawn, then
clue admission/completion/read/reconnect. The deadline is exclusive: no spawn or
clear at or after it counts. Fixture files explicitly list system events before
external events at equal timestamps.

Admission checks this precedence after due scheduled events: existing command ID,
game over, pending command, stale expected revision, missing target, clue legality.
An admitted clue sets pending and advances revision. Only one inference is in
flight per game. Rejected input changes neither board nor score nor revision;
elapsed time and scheduled events still proceed. A rejection receipt includes a
stable reason and current snapshot, without claiming the whole attempt cost no
time. A new command ID is required after editing a rejected clue.

Inference does not pause the clock. At completion, drain scheduled events through
completion time, then rank the **current** board using the computed clue vector.
Newly spawned entries therefore participate. The admitted target is still the
target unless the game ended: no second clue can clear it while pending. If a
spawn/deadline ended the game, discard the result and return `game_over`; no late
score is possible. The terminal event immediately finalizes the pending receipt
as `game_over`, even if the worker has not returned yet. Infrastructure failure
clears pending, advances revision and
returns `inference_failed`; time already elapsed is not refunded. Failed or timed
out inference cannot turn into a successful retry of the same command ID.

Clock treatment is identical across players, but server contention still affects
opportunity to act. This is an explicit fairness limitation to measure under load,
not a claim of equal inference latency. W3 must set bounded inference timeout and
queue admission limits from the benchmark evidence. Overloaded servers reject
before starting inference and cannot silently pause one player's clock.

## Clue legality

Reject raw input longer than 120 Unicode code points before normalization, Unicode
category-C characters except tab/CR/LF, and an empty normalized token list.
Normalize with NFKC, Unicode casefold, and tokenization into maximal sequences of
Unicode letters/numbers; punctuation and whitespace delimit tokens. Preserve the
original clue privately under the logging policy; the normalized form is used for
checks. Encoding text/prefix policy remains the selected model's W3 contract.

Reject a contiguous normalized phrase matching the target label, any target
alias, explicit forbidden phrase, or enumerated inflection/stem-equivalent form.
Check the highlighted target only: another visible word's label is legal unless
also forbidden for the target. Do not use substring matching: `car` must reject
`cars` through an explicit inflection but must allow `carpet`. A multiword phrase
must match consecutive complete tokens; `oxbow, lake` matches `oxbow lake`.

Each trace entry includes a finite `inflections` list, making its fixture behavior
fully defined without pretending to solve English morphology. Examples include
`run` / `running` / `ran`, and `glacier` / `glaciers`; `glacial` is explicitly
forbidden. These are experiment-only inputs, not a proposed manifest extension.
W3 must specify how production lexical forms are generated (a pinned reviewed
stemmer/lemma table plus overrides), including false-positive tests. Until that is
resolved, fixture conformance is not full compliance with the handoff's stem rule.

## Retry and revision contract

A client sends a fresh opaque `command_id`, clue, and `expected_revision` observed
at submission. Scope IDs to the game. Compare retries against the original full
payload, including expected revision. An identical retry returns the cached
receipt (pending or final), without inference, a second clear, or score addition.
A changed payload with the same ID returns `command_conflict`, before other checks.
Retain receipts through the game and the documented reconnect window; W3 must
bound that window and reject expired receipts rather than replaying them.

A stale new command returns `stale_revision` with the current snapshot; never
silently apply it to a different target. A client may offer the unchanged text
again with a new ID after showing the new target. Do not auto-resubmit across
target changes. Snapshot reads/reconnects do not change revision. Old receipts
carry their original applied revision; attach a current snapshot separately and
never let an old receipt roll the browser state backward.

Disconnect does not pause gameplay, suppress spawns or terminate pending
inference. A reconnect authenticates the same game owner and reads current full
state plus the receipt for any uncertain command. Server restart ends an active
experiment as interrupted, with no completed competitive score; durable recovery
and score writes are Stage 2 work. An explicit quit uses the same noncompetitive
interrupted outcome, not a user-supplied final score.

## Casual play and finite event fairness

Casual mode can adapt to the current board. It samples unused entries with a
pinned RNG, tier policy and model-calibrated similarity limits. Try at most 32
candidates; use the least-similar remaining eligible entry, with ID tie-break,
when the diversity filter cannot be met. No already-used entry returns, including
cleared entries. W3 must pin RNG, similarity aggregation, tier eligibility and
thresholds after B's evidence; W2 does not freeze guessed cosine cutoffs.

Casual next-spawn delay is proposed as
`ceil(1000 * max(2.0, 5.0 * 0.9 ** (level - 1)))` milliseconds. Compute it when
scheduling the next spawn, using the level at the preceding spawn; an intervening
clear does not move an already scheduled spawn. The start schedules the first
spawn at 5,000 ms. When all unused entries are consumed, allow a final grace
interval of 5,000 ms; clearing the last entry before that ends `pack_cleared`,
otherwise the deadline ends `pack_exhausted`. W3 must pin a numeric formulation
or delay table across runtimes.

Event mode instead consumes an immutable challenge artifact containing initial
board order, unique spawn IDs and absolute elapsed times, and an exclusive end
time. It pins pack/model/rules/configuration plus a seed and digest. The artifact,
not a seed alone, is the replay authority. Build it once before anyone plays.
The same schedule is served to all players; it does not inspect their targets,
boards, clears, levels, disconnects or clue history. Difficulty increases by
preselected semantic groups and decreasing scheduled intervals, not player level.
Scoring level is informational in this mode. Never skip an event's scheduled
entry to restore diversity on an individual board.

The finite schedule may use at most the pack's unique entries. Set its deadline
to the last scheduled spawn plus a fixed challenge grace interval, or a shorter
published duration. No unscheduled replacement words or endless cycling. An empty
board before the deadline waits for the next scheduled word; if there are none,
it still waits for the common deadline and then ends `event_complete`. Players
who overflow finish early; future challenge entries are not applied to an ended
game. Their common schedule remains unchanged. This preserves equal scheduled
opportunities, while boards and targets appropriately diverge with play.

## Replay coverage and W3 decisions

The checked-in traces cover target-only clear, miss, normalization/legality,
inflection and unrelated-substring behavior, exact ties, inference-time spawning,
equal-time overflow, inference failure, finite exhaustion, an empty board waiting
for a later spawn, retries/conflicts, stale revision, reconnect, and two players
on the same immutable event schedule. The fixture validator is a deliberately
small specification oracle, not reusable production engine code. W4 should replay
these static expected states through an independently implemented engine.

W3 must reconcile real near ties and model thresholds with B, choose production
lexical expansion, pin casual schedule/RNG policy, set timeout/receipt limits,
and reconcile these state/receipt names with D's wire-schema draft. Those are
visible open decisions; this draft does not authorize W4 to invent them. The
capacity-at-equality rule and real-time inference treatment should be explicitly
accepted or changed during that review before freezing a ruleset ID.
