# Durable repository ports — W1

`packages/semaphore_hub/repositories.py` is the shared typed boundary for W2/W3.
`testing.py` supplies deterministic in-memory adapters and `smoke()`; they are
fixtures, never a production fallback. SQLite implementations follow in W2/W3.
The fixture report, manifest and snapshot JSON are deliberately synthetic; fake
adapters do not establish verification, authorization, snapshot validity or durability.

## Transactions and data ownership

Services enter a UnitOfWork for each short write group. Clean context exit commits;
any exception rolls back all repositories. Repositories never commit or nest UoWs.
Repositories are transaction-scoped and must not be retained across contexts.
Production UoW uses the shared SQLite transaction runner. Obtain the live per-game
lock before opening a transaction; never wait for inference, assets or locks inside
one. Authentication/schema checks precede private row access. `owned` and `receipt`
map missing and foreign objects to the same NotFound. `for_recovery` is internal
only and must never be exposed as an HTTP handler.

Account ports handle normalized login, creation timestamps, opaque-token digests,
expiry, touch, reset and revocation. Password reset revokes all sessions in the same
transaction. Token/CSRF plaintext is never stored. Public projections never return
Account or Session records directly. Services enforce account/session policies.

Pack reserve checks namespace owner before digest/retry and retains the namespace
after release. Existing same-owner exact bytes return the prior version; changed
bytes conflict. Verification and asset staging occur outside transactions. Publish
atomically installs version, entries, trusted report and explicit acceptance after
asset digest validation. Publication is represented by membership in
`published_versions`; neither a version row nor a report alone grants visibility.
Artifacts require a published version and matching trusted report. Vector cache
identity is the exact vector/model tuple; mismatch is a miss. Version manifest,
report, ordered entries, vector cache and artifact identities are immutable.

`Publication.report_json` must be a passing trusted server report produced outside
the transaction, with exact model/protocol/ruleset and manifest pins. `accepted_by`
is an authorized operator account and `rights_reference` is a nonempty acceptance
record, not an automatic claim of legal verification. The installer service checks
ownership, rights and operator authority. The SQL schema checks references and
trust flags; it cannot prove the trustworthiness of arbitrary caller-supplied JSON.
Append a new report for reverification; never overwrite historical artifact pins.

## Game operations

`Game` carries immutable artifact/model/start pins plus the last acknowledged full
snapshot. `admit` stores one command and private attempt before acknowledgement.
Known IDs compare keyed original-payload equality before stale/terminal handling;
changed payloads conflict. `resolve` updates final receipt, attempt outcome and game
revision together. `save_transition` persists due-work state changes without a clue.
`finish` commits terminal snapshot, all pending final receipts, retry expiry and a
single natural score together. Repeated finalization returns the committed game.
Interrupted endings pass no Score. The service validates mode-specific reasons,
reducer-authoritative score and all cohort pins; production storage rechecks them.
Late completions cannot modify a terminal game or final receipt.

`history` is private terminal-only, ordered completed_at descending then game ID
ASCII ascending. Its continuation is the last game ID, resolved to that owner's
terminal timestamp for the full tie key. `current` returns the one active owned
game or None and supports uncertain-create recovery. A partial unique index limits
one active game per account. Published versions order pack_id then version ASCII;
its version ID continuation resolves the full pack/version tie key. Services bound limits to
1–100 and wrap repository keys in validated opaque cursors. Board continuation is
(score, completed_at, game_id), ordered descending score then ascending time and
ASCII game ID, and is always bound to the whole Cohort. Public DTOs omit player IDs.
Casual config binds exact initial board, schedule and seed/generator policy.

## Privacy and recovery

Operations record deletion requests in a separate clue-free ledger before applying
live deletions, and export that ledger outside database backups. The operator
lifecycle replays it before expiry/interruption recovery and before traffic.
`erase_clues` clears capture through the requested UTC cutoff while retaining exact
retry HMAC/receipts. `erase_account` requires active games already interrupted under
the shared lock, revokes sessions, removes private rows, anonymizes results and
retains non-login owner tombstones and published content. Unpublished assets and
reservations are removed; file deletion is orchestrated outside the transaction.
Raw capture expires at received_at + 30 days; receipts/digests/attempt metadata expire
at terminal_at + 90 days. Reads enforce deadlines independently of cleanup timing.
The `required_hmac_keys` port includes active and unexpired receipts; keys remain
outside SQLite. Ledger retention extends through the latest affected backup expiry.
Fake expiry only models row cleanup; production operations must also erase derived
material, manage encrypted backup expiry and validate restore ordering.

## Schema evolution

Migration 0002 is additive to 0001. Existing initial-schema rows remain readable;
legacy version rows are unpublished until explicit trusted acceptance. No experiment
state is imported. Existing game rows are not retroactively declared eligible.
New game service admission must resolve a published artifact and verify every pin;
there is deliberately no fabricated artifact backfill for old rows.
Migration count is now 2. A known-prefix database upgrades without rewriting 0001;
unknown/modified histories remain rejected by the migration runner.
