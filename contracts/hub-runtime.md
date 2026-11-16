# Durable hub runtime boundary — hub-runtime-v1

Frozen W1 contract, November 16, 2026. Executable values live in
`packages/semaphore_hub/policy.py`; adoption does not claim production services.
Use [account decision 0006](../docs/decisions/0006-local-accounts.md),
[storage](storage.md), [durable games](durable-game.md) and [gameplay](gameplay.md).
The experiment namespace and its process-local retention remain unchanged.

## Admission, clocks and capture

A single process owns live games. Maximum 64 active games globally and one per
account; refused creates return 503 unavailable, never silently interrupt an
existing game. Creating has no automatic retry guarantee: after an uncertain
response, inspect private history/current game and require an explicit user
choice before another create. Game duration is at most 600000 ms, with 4096
unique command IDs per game. Known-ID retries precede the command-limit check.
The transport cap is 16384 bytes before JSON parsing; no arbitrary payload logs.

Preserve reducer due-work ordering and admission precedence. Inference is one
FIFO worker, eight physically outstanding clues, one per game, with a 5000 ms
monotonic deadline from admission (inclusive timeout). Batch only already-waiting
requests, up to eight, with no fill delay or deduplication. Verification uses a
separate queue. Logical cancellation/timeout cannot free a physical slot while a
model call still runs. Submit under the game lock, persist admission before
releasing that lock, and cancel logically if commit fails. Callbacks must be
asynchronous, never inline during submit, and must reacquire the common lock. Malformed batch output fails all active members. A callback
must carry original game/command identity and pinned fingerprint; under the shared
game lock ignore late/terminal results. Never perform model or filesystem work
inside SQLite write transactions; no success is sent before commit.

Capture only after valid bounded JSON/schema, authentication, Origin/CSRF and
ownership checks. Unknown/foreign games and bad transport do not create attempts.
After those checks, new IDs get a durable command receipt and at most one private
attempt even for legality, stale, busy or overload rejection, within the command
budget. Changed-payload retry conflicts never replace/capture a second attempt;
exact retries reuse the first. Retain raw clue only as the private attempt field,
never in receipts/diagnostics; raw payload storage is unnecessary. Clues normalize
for legality/inference only after the ORIGINAL validated command is HMAC-bound.

Durable UTC epoch milliseconds govern retention; monotonic elapsed milliseconds
govern live reducer/deadlines. Never compare them. Tests must inject both clocks.
Natural termination, final pending receipt and score share one transaction;
interrupted termination has no competitive score. SQL alone cannot certify score
eligibility or reducer authority.

## Trusted operator installation

W2 supports a bounded host-only installation path, not creator uploads. Manifest
input is at most 8 MiB with the existing schema/hygiene rules. W1 operating budget
is 40–500 entries and at most five clues per entry (2500 total), one verification
job at a time, 600000 ms wall deadline. Unsupported size is rejected before model
work; timeout leaves no published version. Budgets do not change verification
thresholds, sampling, model identity or the unchanged shared verifier.

Operator identifies the intended live account owner plus a nonempty rights/source
reference and explicitly accepts publication. Attribution never grants ownership.
After cheap checks, reserve namespace and version in a short transaction; inspect
owner before revealing retries/digests. Failure releases only the version slot.
Validate model lock, canonical manifest/projection hashes, vectors and trusted
report outside the write transaction; preserve exact accepted manifest bytes.
Recompute using the shared verifier. A creator self-report or historical measured
experiment report is not approval. Operator acceptance records who, when, rights
reference and exact report/artifact identity; neither this signature nor a passed
static report claims human balance or full corpus acceptance.

Stage immutable files beneath an operator-selected asset root; reject path escape,
symlinks/reparse redirects and uncontrolled remote references. Recheck digests
before atomic rename on the same filesystem. Commit version, entries, trusted
report reference and publication marker together. Readers require publication;
cleanup removes orphan staging/assets after interruption. Reverification appends
reports; it never replaces accepted bytes or historical game pins. Retired pack
names and deleted-owner tombstones stay reserved.

Artifacts bind the full ordered initial board, full ordered schedule, seed and
generator policy (explicit null when absent) into canonical configuration identity,
plus timing/scoring/pacing/special-clear inputs. Verify the binding against stored
bytes; do not trust client cohort values. Different randomized artifacts have
separate boards. Reuse an explicitly accepted artifact for multiplayer ranking
acceptance, without merging random cohorts.

## Keys, retention and recovery

Command equality uses HMAC-SHA-256 over the restricted canonical JSON array
["durable-command-v1", game_id, command_id, original_command]. Keys have at least
32 random bytes, immutable version IDs and host-controlled storage outside SQLite.
New commands use the active version; retries use their stored version. Rotation
retains old versions through the latest affected receipt expiry, including active
games and restorable unexpired backups. Never replace a missing key, fall back to
unkeyed hashes, recompute old digests or return a new receipt for an old command.
Missing active/required key fails startup readiness and runtime admission closed.

Startup runs before traffic: migrate, replay the current external deletion ledger,
expire private data, validate needed key versions, interrupt prior active games,
settle pending receipts and clean orphan assets. Keep the service unavailable if
any step fails. The external deletion ledger must outlive backup restoration;
a ledger only inside the restored database cannot prevent resurrection. Its entry
IDs are idempotent, contain no clue text and survive the last affected backup.

Raw/derived clue material expires at received_at + 30 days; clue-free private
receipts/digests/attempt metadata expire at terminal_at + 90 days. Cleanup runs
at least daily and read-time checks enforce equality deadlines. Clue-only deletion
preserves retry equality until expiry. Account erasure first locks/interrupts live
games and revokes sessions, deletes all private retry material, anonymizes retained
results and preserves published pack tombstones; remove unpublished assets.
All live maintenance acquires the same game lock as commands before opening its
transaction. Never acquire a game lock while holding a database write lock.

Backups are encrypted with maintained tools, operator-restricted and expire within
30 days of creation. Backup rotation and restore are W3 acceptance requirements.
Restoring must apply the newest external deletion ledger and retention before
traffic; inaccessible backups may retain deleted bytes for up to 30 additional
days. Missing ledger/key material fails recovery closed. Log only safe operation
IDs/error codes, never clues, digests, secrets, raw bodies or participant vectors.
