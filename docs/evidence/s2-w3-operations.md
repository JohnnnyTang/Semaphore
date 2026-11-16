# W3-F operations implementation evidence

November 16, 2026. Isolated worker baseline:
`2a00a4334227274abfdf29ea9eb86c3571b95057`.

Implemented the frozen `Maintenance` repository and `Recovery` callbacks, exact
read-time raw expiry, daily cleanup hook, ledger-first clue/account deletion,
account tombstones, result anonymization, private unpublished asset removal,
shared-content retention, and external-key validation. Games are interrupted and
forgotten via the injected E lifecycle. Per-game locks are acquired sequentially;
no maintenance transaction waits on a game lock.

Added authenticated HMAC-chained, fsynced external deletion records; replay is
idempotent. Added AES-256-GCM snapshots using pinned `cryptography==50.0.2`, bounded
SQLite online backup, authenticated creation/expiry metadata, rotation and restore
preparation with mandatory recovery callback before publishing a new database.
No raw participant data, keys, credentials, database or model weights are tracked.

Validation:

- `uv sync --locked --group dev`: passed in isolated worktree.
- `uv run --no-sync pytest tests/hub/operations -q`: 12 passed.
- `uv run --no-sync ruff check .`: passed.
- `uv run --no-sync ruff format --check .`: 158 files formatted.
- `git diff --check`: passed.

The tests use real SQLite with explicitly synthetic private clues and a fake
lifecycle. They cover exact 30-day read/cleanup and 90-day retry boundaries,
HMAC preservation after clue deletion, external-ledger-before-SQL crash replay,
missing command keys/readiness failure, tampered ledger, anonymous natural zero
scores, interruption without scores, session/profile erasure, shared pack/cache
retention, unpublished assets, active-game conflict, cleanup/rotation failure
reporting, ciphertext/tamper/wrong-key rejection, expiry rotation and restore
replaying a deletion that happened after the backup was taken.

Windows validation found that fsync on a read-only restored DB handle fails;
restore now opens the final fsync handle read/write. Backup plaintext is confined
to the restricted restore preparation directory and removed on callback failure.

The [operator runbook](../operations/durable-hub.md) specifies exclusive operator
composition, scheduling, external key/ledger custody, separate immutable asset
retention and required restore validation. E integration, coordinator host CLI,
real-service crash probes and signed-in real-model/W4 human acceptance remain
coordinator work. A fake lifecycle pass does not establish integrated recovery.
The existing Stage 1 latency, human, content/source-yield and remote-host resource
carryovers remain open. Nothing in this worker changes contracts or migrations.

## W3 completion: concrete dependency readiness

November 16, 2026. Added `operations.validate_assets(connection, asset_root)`
for live and restored SQLite databases. It verifies content-addressed manifest
bytes, vector hashes, root confinement, vector dimensions/counts, published
version cache availability, artifact/configuration digests and retained game
artifact availability. Missing or altered dependencies stop readiness.

`EncryptedBackups.validate_restorable(now_ms, keys, validate_assets)` decrypts
and checks every unexpired authenticated snapshot in memory, including SQLite
integrity/foreign keys and all still-required HMAC versions. It includes versions
no longer used by the live database, rejects future-dated snapshots, and returns
the immutable asset filenames that must remain available. No plaintext scan file
is created. Host composition must retain these files through backup expiry and
use the same concrete validator before publishing a restored database.

Validation: `uv run --no-sync pytest -q tests/hub/operations` — 15 passed;
Ruff check and formatting passed for the operations implementation/tests. New
cases cover keys required only by backups, scanning multiple snapshots, expired
and future snapshots, and missing/tampered/mislocated or malformed vector assets.
These are synthetic SQLite and asset checks; real-model and human gates remain
outside this evidence. The integrated host and independent probe evidence record
the corresponding end-to-end W3 checks.
