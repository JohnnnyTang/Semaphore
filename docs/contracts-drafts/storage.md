# SQLite storage proposal (no migration)

> November 14 update: pack ownership, durable game/score transport and privacy
> decisions are adopted in [decision 0005](../decisions/0005-durable-game-contract.md).
> Conflicting proposals below are historical; other platform decisions remain drafts.

Enable foreign keys on **every connection**, with bounded busy timeout and short
transactions. Use parameterized statements. The single application process owns
the model and write coordination; verification runs outside database transactions.
Integer timestamps are UTC epoch milliseconds for durable records; live game
ordering uses a separate monotonic elapsed clock. Never compare those clock domains.

| Table | Fields and constraints | Purpose / access |
| --- | --- | --- |
| `users` | PK user_id; UNIQUE login_key; display_name; password_hash; role CHECK player/admin; created_at; disabled_at nullable | Private account lookup; role set by operator only |
| `auth_sessions` | PK token_digest; FK user_id; csrf_digest; created_at; last_seen_at; expires_at; revoked_at | No raw token; index expiry and user_id for revoke |
| `packs` | PK pack_id; FK owner_id; hidden boolean; is_default boolean; created_at | Stable ownership independent of manifest author |
| `pack_versions` | PK version_id; FK pack_id; UNIQUE(pack_id, version); manifest_digest; immutable relative asset path; semantic_hash; vector_hash; publication_state; published_at | Metadata visible only after atomic publication |
| `entries` | FK version_id; entry_id; ordinal; display_text; embed_text; aliases_json; forbidden_json; tier; PK(version_id, entry_id); UNIQUE(version_id, ordinal) | Every reference includes version_id, never entry ID alone |
| `verification_runs` | PK run_id; FK version_id nullable before publish; FK upload_job_id; full fingerprint JSON/hash; metrics_version; protocol_hash; semantic_hash; status; computed_report_json; created_at | Hub authority; report status distinguishes rejected/failed from passed |
| `upload_jobs` | PK job_id; FK owner_id; reserved pack_id/version; body_digest; staged_path; state; safe_error_json; created_at; finished_at | Private owner-scoped job; bounded staged bytes |
| `idempotency_keys` | PK(owner_id, endpoint, key); body_digest; FK job_id; expires_at | Same key cannot change payload |
| `challenges` | PK challenge_id; FK version_id; fingerprint_hash; ruleset_id; rules_config_json; schedule_hash; immutable schedule_path; seed; starts_at; duration_ms; created_by | Schedule independent of player's actions |
| `games` | PK game_id; FK user_id/version_id; FK challenge_id nullable; fingerprint_hash; ruleset_id; config_json; seed; status; started_at; finished_at; score nullable; end_reason | One pinned cohort; active state may stay in memory |
| `scores` | PK game_id FK games; FK version_id; challenge_id nullable; display_name_snapshot; score; completed_at; fingerprint_hash; ruleset_id | One server-finalized result, never client-written |
| `clue_attempts` | PK attempt_id; FK game_id; command_id; target_entry_id; received_at; resolved_at; clue_text; legality; reject_code; rank nullable; cleared; UNIQUE(game_id, command_id) | Private, retention-limited; target joins game's version |
| `command_results` | PK(game_id, command_id); payload_digest; received_at; response_json; expires_at | Retry result and side-effect deduplication; private because response may contain clue |

JSON columns store bounded validated structures, not arbitrary user documents.
Foreign-key cascades are explicit: revoke/delete sessions when a user is removed;
never cascade-delete published packs/scores as a side effect of deleting an account.
Exact deletion/anonymization behavior is an open policy decision. Keep private
attempts deletable without deleting immutable manifests or competition results.

## Transactions and races

**Reserve:** after cheap validation, begin a short write transaction. If no pack
exists, create an owner reservation; otherwise compare authenticated owner. Enforce
unique version/job reservation with a unique partial index for active jobs (or a
separate reservation table). The first transaction wins a competing new pack ID.
Check published manifest digest and scoped idempotency key inside this transaction.
Write staged bytes to an operator-owned location before recording a durable job;
never derive a filesystem path directly from user strings.

**Publish:** finish embedding/verification outside a transaction. Store immutable
manifest and derived assets using temporary files plus atomic rename on the same
filesystem; verify their digests before the database commit. In one transaction
insert immutable version/entries/verification result and mark job published. Public
queries require published state, so partial data is invisible. On failure, roll
back rows; orphan immutable files are safe and can be removed by bounded recovery.
Do not advertise success before commit. Never edit a published manifest in place.

**Finish game:** atomically compare game status, insert exactly one `scores` row,
set completed state and final score. Unique game ID makes duplicate end events
idempotent. Interrupted games receive no score. Event scores must match challenge's
pack/model/rules identity via checks in the transaction; a challenge ID by itself
does not prove compatible configuration.

**Apply command:** record the immutable command receipt and attempt once. Active
reducer state remains in memory in v1, so a crash cannot resume a game by guessing
from partial attempt logs. On restart mark all running games interrupted and clear
their pending commands without creating final competitive scores. Durable duplicate
attempt/result keys prevent retransmission from duplicating private records.

**Retention:** delete bounded batches indexed by `received_at`/`expires_at`. Cleanup
uses a fresh cutoff each run and covers attempts, clue-bearing result payloads,
failed staged files, terminal job diagnostics and expired sessions. It never
deletes published authored test sets or finalized scores. Failed cleanup is an
operator-visible error; it cannot be reported as successful privacy deletion.

## Query and competition details

Index scores on `(version_id, score DESC, completed_at ASC, game_id ASC)` and on
`(challenge_id, score DESC, completed_at ASC, game_id ASC)`. Equal scores order by
earliest completed timestamp then game ID. Proposed v1 board lists each finalized
game (not a best-per-account reduction); W3 should confirm this product choice.
Pagination cursor includes the full tie key and board identity to prevent gaps.
Pin model/rules for each version's competition cohort; future migrations must
create a distinct cohort/board instead of silently mixing scores.

The public version record links one current authoritative verification run;
self-reported report stays in manifest bytes and is displayed separately.
Reverification appends runs and preserves historical provenance; it does not
mutate the previous run or retroactively rewrite old game identity.
