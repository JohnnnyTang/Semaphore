# Durable hub operations

The durable host composes the real game lifecycle, shared game locks, external
command keys, deletion replay, encrypted backups and immutable asset checks.
Operator commands are host-only; they do not expose captured clues over HTTP.

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
the concrete host and independent probes exercise the integrated lifecycle.

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


## Concrete host and commands

Provision independent random 32-byte CSRF, ledger and backup key files under
operator-only permissions. Provision the command key JSON with an `active` version
and `keys` mapping from version labels to base64-encoded random keys (at least
32 bytes each). Preserve old versions while any live receipt or restorable backup
requires them. Create the external ledger once as described above; startup never
creates or replaces a missing ledger. Retain the immutable asset directory alongside
the encrypted snapshot directory.

Use the same arguments for all durable commands, placing common options before the
subcommand. For example (paths are operator-provisioned, not generated by this command):

```powershell
uv run python -m semaphore_hub data/hub.db --assets data/hub-assets --csrf-key secrets/csrf.key --command-keys secrets/commands.json --ledger secrets/deletions.jsonl --ledger-key secrets/ledger.key --backups data/backups --backup-key secrets/backup.key serve-durable --port 8080
```

`serve-durable` binds IPv4 loopback only. Configure the existing Ollama environment
for the pinned model provider. The identity check, deletion replay, expiry, key and
asset validation, active-game interruption, initial cleanup and encrypted backup
all complete before the listener binds. The host advances game clocks every 100 ms
when idle and after incoming connections; cleanup and encrypted backup creation run
on startup and at least every 24 hours thereafter. Maintenance failures close
readiness and stop the listener, with a nonzero process exit for supervision.
HTTP request threads and inference drain before the exclusive process lock releases.
Use `serve-durable --web-root web` for same-origin browser assets at `/web/durable.html`; without that option the listener remains API-only.

With the same common options, substitute:

- `cleanup`: replay startup recovery, expire private data and rotate backups.
- `backup`: recover, validate dependencies and create an encrypted SQLite snapshot.
- `delete-clues ACCOUNT_ID`: record and apply clue deletion.
- `delete-account ACCOUNT_ID`: record and apply account erasure.
- `restore BACKUP_PATH NEW_DATABASE_PATH`: prepare a new database, replaying the
  current external ledger before publishing it. The destination must not exist.

Stop the listener before operator commands. Every CLI command holds the database
and shared-assets process locks; restore also locks its new destination. Restart
the listener using the restored database path after a successful restore. Foundation
mode remains available and continues refusing game-bearing databases.

Every startup and backup validates all unexpired snapshots' HMAC and asset
requirements. Orphan-asset removal is deferred while encrypted backups exist, so
restorable snapshots cannot lose their immutable dependencies. Expired snapshots
are rotated during daily maintenance. Restore validates the restored database with
the same asset checks and never cleans shared assets from its temporary snapshot.

Focused host validation: `uv run --no-sync pytest -q tests/hub/test_host.py
tests/hub/test_durable_host.py`. These checks use synthetic inference or offline
operator recovery, and do not establish real-model load or human acceptance.

## Fresh local acceptance setup (PowerShell)

Use Python 3.12 and install the locked environment with `uv sync --locked --group dev`.
This may need package-network access; it is not an offline-install proof.
Create an operator-only directory using your operating system's filesystem
permissions before generating secrets. Use ignored `data/w4-local` for acceptance;
Git ignore rules do not restrict other local users. Keep this directory and its
ledger outside the browser root.

For a **new installation only**, save this Python snippet as an operator setup
script and run it with `uv run --no-sync python PATH_TO_SCRIPT`:

```python
import base64
import json
import secrets
from pathlib import Path
from semaphore_hub.operations import ExternalLedger

root = Path("data/w4-local")
root.mkdir(parents=True, exist_ok=False)
for name in ("csrf.key", "ledger.key", "backup.key"):
    with (root / name).open("xb") as output:
        output.write(secrets.token_bytes(32))
with (root / "commands.json").open("x") as output:
    json.dump({"active": "v1", "keys": {
        "v1": base64.b64encode(secrets.token_bytes(32)).decode()
    }}, output)
ExternalLedger(root / "deletions.jsonl", (root / "ledger.key").read_bytes(), create=True)
```

The script refuses an existing directory so a repeat cannot overwrite keys or
reset a ledger. Secure the parent directory before running it so generated files
inherit restricted access. Inspect partial setup manually; do not use this script
to repair an existing deployment.

Set common CLI arguments once (no secret contents appear on the command line):

```powershell
$hubArgs = @('data/w4-local/hub.db', '--assets', 'data/w4-local/assets',
  '--csrf-key', 'data/w4-local/csrf.key', '--command-keys', 'data/w4-local/commands.json',
  '--ledger', 'data/w4-local/deletions.jsonl', '--ledger-key', 'data/w4-local/ledger.key',
  '--backups', 'data/w4-local/backups', '--backup-key', 'data/w4-local/backup.key',
  '--origin', 'http://localhost:8080')
uv run --no-sync python -m semaphore_hub data/w4-local/hub.db migrate
uv run --no-sync python -m semaphore_hub @hubArgs bootstrap operator Operator
```

Bootstrap prompts twice for the password and prints the account ID. Retain that ID
for operator and pack-owner arguments. Empty and checksum-matching v1 databases
upgrade to schema v2; existing accounts survive and old versions are not silently
published. Edited, future and unversioned histories fail instead of being adopted.
Stop the host and retain a restorable deployment before upgrading an existing DB.

Install only rights-cleared content with `install-pack MANIFEST --owner ACCOUNT_ID
--operator ACCOUNT_ID --rights-reference REFERENCE --accept-publication`, followed
by `accept-artifact PACK_ID VERSION CONFIGURATION --operator ACCOUNT_ID`. These
subcommands follow the same `@hubArgs`. The configuration JSON must contain exactly
`initial_board`, `schedule`, `seed`, and `generator_policy`; use the accepted pack's
entry IDs. Installation runs real pinned-model verification and may reject content.
An empty fresh database has no playable packs until installation and acceptance finish.

Once the pinned Ollama provider is configured, launch the integrated browser host:

```powershell
uv run --no-sync python -m semaphore_hub @hubArgs serve-durable --port 8080 --web-root web
```

Open `http://localhost:8080/web/durable.html` using the exact configured origin.
`localhost` and `127.0.0.1` are different origins; changing the port also requires
changing `--origin`. Keep the root pointed at the repository `web` directory. The
listener still binds loopback; this local acceptance setup does not establish LAN
access, HTTPS, remote-host offline readiness or human acceptance.

Stop the listener before this backup/restore drill. Retain the backup path printed
by `backup`; substitute it for `BACKUP_PATH` below:

```powershell
uv run --no-sync python -m semaphore_hub @hubArgs backup
uv run --no-sync python -m semaphore_hub @hubArgs cleanup
uv run --no-sync python -m semaphore_hub @hubArgs restore BACKUP_PATH data/w4-local/restored.db
```

For a disposable acceptance account only, run `delete-clues ACCOUNT_ID` or
`delete-account ACCOUNT_ID` between backup and restore to verify that the newest
external ledger removes the older snapshot's data. Account deletion is destructive;
do not use a real operator/player account for a drill. Start the restored deployment
with its new database path and the same retained assets, keys and current ledger.
Restore never overwrites an existing destination.

Reproduce the CLI acceptance checks with:

```powershell
uv run --no-sync pytest -q tests/hub/operations/test_cli_acceptance.py
```

These checks use isolated temporary databases and generated test keys, without
model calls or participant data. Service-level populated-game/crash tests cover
interruption and receipt semantics separately; this operator drill does not prove
a real-model completed result or a fully offline installation.
