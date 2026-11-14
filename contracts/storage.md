# Durable storage contract — durable-game-v1

Adopted November 14, 2026 for the persistence implementation. This supersedes the
W4 storage draft and conflicting W2 storage proposals, not the running
process-local `/experiment/v1` service. No migration or durable service is claimed.
See [durable game behavior](durable-game.md) and
[decision 0005](../docs/decisions/0005-durable-game-contract.md).

Enable foreign keys on every connection; use short transactions, parameterized
statements and server-generated IDs. Durable timestamps are UTC epoch milliseconds;
live reducer ordering uses elapsed monotonic milliseconds. Never compare those clocks.

## Pack ownership and immutable versions

`packs(pack_id PRIMARY KEY, owner_id, created_at, retired_at)` owns the global
public pack namespace. `pack_versions` has a version ID primary key, a pack FK,
`UNIQUE(pack_id, version)`, exact accepted manifest bytes/digest, semantic hash and
vector hash. The public ownerless pack route resolves this global namespace.
Manifest author/provenance never grants ownership. Pack IDs are not reassigned.

After cheap validation, a short transaction reserves a new pack ID for the
session's account and reserves `(pack_id, version)` for one publication job.
The first committed reservation wins concurrent claims; a different owner gets
an ownership conflict even if the bytes match. Check owner before returning any
existing job, digest or retry result. Failed/cancelled jobs release the version
job reservation for that owner, but not the pack ID. Retired IDs remain reserved.

For an existing immutable version, the same owner and exact raw digest return
that version idempotently; different bytes conflict and require a new version.
Embedding and verification occur outside transactions. Write immutable assets by
atomic rename, validate their digests, then publish version, entries and trusted
report reference in one transaction. Readers require published state. Orphan files
are cleaned by recovery; success is never returned before commit. Reverification
appends reports and cannot replace bytes or rewrite historical game pins.

`verification_reports` binds version, manifest/semantic hashes, fingerprint hash,
protocol hash and exact playable ruleset ID. Self reports are separate and untrusted.
`vector_caches` is unique on `(vector_hash, fingerprint_hash)` with validated
ordered vectors. A mismatch is a cache miss, never an in-place identity repair.
The experiment's measured report alone does not authorize publication.

## Game and command transactions

`games` stores game ID, player FK, immutable version FK, mode, full model identity,
playable ruleset, config digest and canonical config, artifact/schedule identity,
challenge identity if any, revision, status, start/finish time and terminal reason.
Pins cannot change after creation. State may remain in memory while active; persist
the full terminal snapshot in the finalization transaction for later reads. On
restart interruption, use the last committed revision and persisted state metadata,
clear pending, and advance revision once; never fabricate a recovered live board.
Persist the last acknowledged snapshot with each committed command/state transition
so interruption can return a schema-conforming terminal snapshot.

`commands` is unique on `(game_id, command_id)` and stores the exact-payload digest,
received time, pending/final receipt and expiry. `clue_attempts` uses the same unique
key and stores private raw clue, target, timing, legality and outcome. Validate
transport/schema and ownership before accessing these rows. Bound game duration
and command count as in gameplay.md. A duplicate does not create another attempt.

Before acknowledging admission, commit command reservation and private attempt.
Apply each completion once under the per-game lock: commit receipt, attempt outcome
and durable revision before sending success. A crash between in-memory mutation
and commit interrupts the game; it never replays a partially recorded command.
Pending receipts may become final once; final receipts are immutable.

Natural termination commits the terminal game record, final pending receipt (if
any), and exactly one `scores` row together. `scores.game_id` is a unique FK.
Check active status and all pinned cohort fields inside that transaction. A retry
of finalization returns the committed result. Failure rolls back all rows and
must not announce success. Score is reducer-authoritative, never client supplied.

At startup, before accepting traffic, atomically mark previously active games
`over`/`interrupted`, settle pending receipts as `game_over`, and create no score.
Do not reconstruct active state from clue logs or resubmit work. Completed games
and receipts survive restart; late completions cannot change terminal records.
Explicit quit and operator interruption use the same no-score transaction.

## Privacy, retention and deletion

Disclose before play: clues are private, retained for up to 30 days from receipt
for operator feedback, and never shared with pack creators or public boards.
Only authorized operators with audited host filesystem/database access may inspect
them. There is no raw-clue admin-web API, public export or command enumeration API.
Do not put clues in application/access logs, telemetry, error diagnostics or fixtures.

Delete raw clues, raw command payloads, clue-bearing receipt/diagnostic copies and
any derived per-player clue/vector material at `received_at + 30 days`, or earlier
on a player's deletion request. Jobs run at least daily; reads deny expired data
at the deadline even if physical cleanup is pending. Surface cleanup failures to
operators. Published authored test clues are pack content, not participant captures.

Exact retry lasts until 90 days after terminal time. Store a keyed HMAC-SHA-256 of
the canonical validated ORIGINAL command (including unnormalized clue and expected
revision), computed over the restricted canonical JSON array
`["durable-command-v1", game_id, command_id, original_command]` from verification.md. Keep the key outside the database
under operator control and retain its key version through receipt expiry. This
prevents raw deletion from breaking equality checks and limits offline guessing
from a leaked digest database. Digests remain private. Receipts contain no clue
text; raw payloads are unnecessary for retry after hashing. Changed payloads
conflict, including whitespace/case changes. The original final receipt is returned
with a fresh snapshot; never rerun inference. At expiry delete command digest,
receipt and remaining attempt metadata; an expired terminal game cannot execute
new commands. Retain only its non-clue terminal/result record.

Account deletion first interrupts active games and revokes sessions, then removes
all private attempts, payloads, receipts, digests and account credentials/profile.
Remove player links and display-name snapshots from retained game/score rows and
show `Deleted player`. Keep immutable published packs under a non-login deleted-owner
tombstone and keep their IDs reserved; account deletion does not silently unpublish
shared content. Remove unpublished private assets. Public results retain score and
cohort provenance, not an account identifier. Explicit clue-only deletion removes
raw/derived clue material but retains private digests and clue-free receipts until
the retry deadline; account deletion revokes that retry access entirely.

Encrypted backups expire within 30 days of creation, with restricted operator
access. A deletion ledger without clue text must be applied before a restored
backup serves traffic, followed by retention and interruption recovery. Disclose
that deleted data may remain only in inaccessible backups until expiry (up to 30
additional days); never claim immediate erasure of backup bytes. Retain ledger
entries through the last affected backup's expiry. Rotation and restore drills
are persistence acceptance requirements, not properties of the experiment server.
