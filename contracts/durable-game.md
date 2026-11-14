# Durable games and scores — durable-game-v1

Adopted November 14, 2026. This is the target for durable implementation;
`openapi.json` and `/experiment/v1` remain the executable, disposable experiment.
The W2 WebSocket proposal is superseded for durable game transport by authenticated
HTTP commands, full snapshots and receipt polling. Account signup/session issuance
and LAN transport policy remain a separate account decision; this contract does
not claim the unauthenticated experiment is suitable for durable accounts.

## Transport and retry

The durable namespace is `/api/v1`. Game ownership comes only from the authenticated
session. Every game, receipt, quit and private result operation checks that owner;
unauthenticated requests return 401, other users' and unknown games return 404.
Cookie-authenticated mutations require a valid CSRF token and allowed Origin.
The account contract must bind token issuance before this service ships.

| Method and path | Behavior |
| --- | --- |
| POST /api/v1/games | Same create body as `http.schema.json`; commit player and immutable artifact pins before 201 with `events.schema.json` envelope |
| GET /api/v1/games/{game_id} | 200 full current envelope, including durable terminal snapshot |
| POST /api/v1/games/{game_id}/commands | Same command body/envelope as experiment; admission/retry precedence from gameplay.md; final receipt survives restart |
| GET /api/v1/games/{game_id}/receipts/{command_id} | 200 original pending/final receipt plus current snapshot; unknown command 404; expired receipt window 410 `game_expired` |
| POST /api/v1/games/{game_id}/quit | Idempotent interruption; same quit body/envelope as experiment; repeat returns terminal state |

Durable terminal snapshots do not expire with receipts. Commands after the retry
window return 410; during it, known IDs are checked before terminal rejection.
An unseen ID on a terminal game gets `game_over`, never inference. Read a snapshot
on reconnect and resolve each uncertain command by its original ID. Disconnect
alone does not pause or end play. Sequence is a connection-local ordering aid,
not durable replay authority; revision and final receipt applied_revision persist.
Never roll back a current snapshot to an older receipt or animate a receipt twice.
There is no incremental event replay or WebSocket requirement.

The create operation has no automatic HTTP retry guarantee: after an uncertain
create response, the client must not silently create another game. A later account
API may add a separately specified creation idempotency key. This does not weaken
command-ID retry or score finalization guarantees.

## Terminal results and board identity

Natural terminal reasons `overflow`, `pack_cleared`, `pack_exhausted`, and
`event_complete` persist one result/score row per game, including zero scores.
Only mode-valid reasons qualify (`event_complete` for event; `pack_cleared` and
`pack_exhausted` for casual; `overflow` for either). `interrupted` covers quit,
operator stop and restart recovery: retain terminal status and observed game score
for the player's history but create no competitive score row. Terminal commits
and pending receipts are atomic as specified in storage.md. A quit racing a
natural terminal transition follows gameplay's due-work ordering; first committed
terminal outcome wins and cannot be overwritten by a later quit.

A board is identified by the exact tuple `(mode, pack_id, version,
manifest_digest, fingerprint_hash, ruleset_id, config_digest, challenge_digest)`.
Configuration includes all scoring/timing inputs: initial board size, capacity,
zone, duration, spawn schedule/generator policy, pacing and special-clear policy.
Casual v1 is finite-artifact play: its config digest must also bind the exact
initial board and schedule/seed, so different casual artifacts cannot mix scores.
Event challenge digest binds its immutable initial board, schedule, deadline and
seed. Verify these pins against the stored artifact, not client declarations.
Portable model identity and adaptive generation require separately versioned work.

Only trusted server games starting at zero with a valid published version and
exact artifact pins enter boards. Tutorial, practice, test-mode and synthetic runs
never enter public competition. W3 measured status is not publication approval.
The paced and base rulesets always have distinct boards even though their static
verification policy is shared. Model/config/version migrations create new boards;
never recalculate or move old scores into a new cohort.

List every finalized eligible game, not best per account. Order by score descending,
then completed_at ascending, then game_id ASCII ascending. Persist completion time
once; retries do not update it. A pagination cursor binds the whole board identity
and last full tie key. Boards expose only public display name (or `Deleted player`),
score, completion time and public game/cohort identity; never clues, receipts,
private account identifiers or session data. Storage keeps one row per eligible
game even if an account is deleted; anonymization does not alter ranking.

## Persistence acceptance

Before replacing the experiment, demonstrate concurrent pack reservation and
owner-before-digest checks; crash injection before/after admission, completion and
terminal commits; duplicate/changed command retries after raw deletion; restart
interruption with no score; quit/finish races; cohort isolation and equal-score
pagination; raw deletion, account anonymization and backup restore cleanup. These
are implementation exit criteria, not claims that durable behavior exists today.
