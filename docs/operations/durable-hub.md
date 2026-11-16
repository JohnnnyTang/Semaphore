# Durable hub operations callbacks

W3-F provides host-only building blocks. Coordinator composition must supply the
integrated game lifecycle, common game locks and external command keys. These
callbacks are not web administration routes and do not expose captured clues.

## Startup and operator lifecycle

Create `ExternalLedger(path, ledger_key, create=True)` exactly once for a new
installation. Normal startup uses `create=False`; a missing, truncated or corrupt
ledger fails closed. Keep its independent random 32-byte key outside the database
and under operator-only filesystem permissions. Never reinitialize a missing
ledger when restoring an existing installation. Its authenticated records contain
account IDs, scope and deadlines, but no clue text. Protect ledger integrity and
availability separately from backups; authenticated chaining detects content edits,
not authorized-host rollback to an older complete ledger. Entries are retained
indefinitely, satisfying the affected-backup retention bound without risky pruning.

Compose:

```python
operations = Operations(
    database.transaction,
    common_game_locks,
    game_lifecycle,
    command_keys,
    external_ledger,
    pack_service.clean_orphan_assets,
    clock=clock,
    rotate_backups=encrypted_backups.rotate,
)
```

Run `Application.start()` before traffic: ledger replay, retention, required-key
validation, active-game interruption, orphan cleanup. Exceptions leave readiness
false. Lifecycle interruption must use the real game reducer/persisted snapshot,
settle pending receipts atomically without a score, and acquire the same game lock
as live mutations. The operations worker tests use an explicitly fake lifecycle;
coordinator acceptance must exercise the integrated lifecycle.

Host operator callbacks `delete_clues(account_id)` and `delete_account(account_id)`
fsync the external ledger before mutation. They interrupt affected games, then
remove private material under one shared game lock at a time. Clue deletion ends
an active game without score so outstanding inference/private memory can be
cancelled and forgotten; original HMACs and clue-free receipts remain retryable.
Account deletion also removes credentials and sessions, anonymizes retained games
and scores, and leaves a non-login account tombstone holding reserved pack names.
Published versions and shared caches remain available. Unpublished versions,
entries, reports and unreferenced vector-cache metadata are removed; the asset
cleanup callback removes orphan bytes outside the SQL transaction. If an impossible
unpublished-version/game reference exists, erasure fails visibly for investigation.

Do not run operator deletion concurrently with an installer or another destructive
operator command. Use the coordinator host process gate. The pack orphan callback
is a pre-traffic/installer-exclusive operation. Account erasure rechecks active
games in its final transaction; a new active game racing interruption causes a
conflict, not a false successful erasure. Replay/retry completes any partial work.
Already committed deletion IDs are idempotent and do not interrupt future games.

## Retention and failure handling

Call `daily_cleanup()` at least once every 24 hours while the host runs. It purges
raw clues at exactly 30 days and terminal command/attempt metadata at exactly the
stored 90-day terminal retry deadline. Shared locks are never nested, so striped
lock collisions cannot reverse lock order. `read_clue` is an audited host-only
callback that denies raw data at the exact deadline even if cleanup has not run;
never expose it as an HTTP route or log its output. Raw command copies and derived
vectors are not stored by this adapter. Other adapters must keep that invariant.

Supply `rotate_backups` whenever backups are configured. Errors propagate and do
not advance the successful-cleanup timestamp; the host must surface the failure
and retry. Restart also replays deletion/retention before traffic. This module does
not create an unattended scheduler by itself.

## Encrypted snapshots and restore

`EncryptedBackups(root, backup_key)` requires an independent external 32-byte key.
Use a restricted operator directory; the code rejects symlink/junction redirects
but cannot protect a directory writable by an untrusted local account. `create`
uses SQLite's consistent online backup into memory, authenticates/encrypts the
snapshot using AES-256-GCM and a fresh random nonce, fsyncs ciphertext and publishes
by rename. No plaintext snapshot is written during creation. The 256 MiB database
budget is checked before serialization; ciphertext input is bounded. Creation
rotates expired snapshots, and daily cleanup must also rotate on quiet days.
Snapshots expire at creation plus 30 days, and restore refuses expired or
future-dated snapshots. Keep the backup key until every dependent backup expires.

These snapshots include SQLite data only. Separately retain the immutable
content-addressed published manifests/vectors and all still-required command key
versions. Do not place keys or the authoritative external deletion ledger inside
the backup. A database snapshot without these dependencies is not a complete
restorable deployment.

`prepare_restore(backup, new_destination, now_ms, recover)` decrypts/authenticates,
checks database integrity, then invokes `recover(temporary_database_path)` before
publishing a new destination. The callback must compose the **current external
ledger**, replay it, expire private data, validate command keys, interrupt active
games, and validate every referenced immutable asset and digest. Close all handles
before returning. The wrapper checks foreign keys, checkpoints SQLite, fsyncs the
prepared database and renames it only after callback success. A callback exception
leaves the destination unpublished. No overwrite of an existing deployment is
allowed. Temporary restore plaintext requires the same restricted directory and
must never be served. Restore drills must test the integrated callback, including
missing assets/keys, before operational use.

Deleted data can remain only in inaccessible encrypted backups until their expiry,
up to 30 additional days. Restore replays the external deletion ledger before
traffic. Do not claim immediate erasure of historical backup bytes.

Failed restore removes the generated main database and its WAL, SHM and journal
sidecars. Cleanup errors (for example an open Windows handle left by the callback)
propagate for operator attention; they must not be logged as a clean failure.
