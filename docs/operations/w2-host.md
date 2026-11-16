# W2 foundation host operations

The module supplies local operator commands and an IPv4 loopback account/pack
listener, not a complete durable game server. JSON APIs only; browser/service
composition remains W4. The listener refuses game-bearing databases and account
tombstones until W3 ledger/retention/recovery is composed. Start with a new W2
database; never use this foundation-only host to restore backups.

Keep database, assets and key outside source control in host-restricted storage.
Provision a file containing 32 cryptographically random bytes, restrict its host
filesystem permissions and retain it across restarts. Passwords are read twice
with getpass, never supplied in arguments. Output contains result IDs only; the
listener emits no access/body/header logs.

Global flags go before the subcommand. Examples (replace paths and identifiers):

```powershell
uv run python -m semaphore_hub D:/private/hub.db
uv run python -m semaphore_hub D:/private/hub.db --csrf-key D:/private/csrf.key --assets D:/private/assets bootstrap operator Operator
uv run python -m semaphore_hub D:/private/hub.db --csrf-key D:/private/csrf.key --assets D:/private/assets reset-password ACCOUNT_ID
uv run python -m semaphore_hub D:/private/hub.db --csrf-key D:/private/csrf.key --assets D:/private/assets install-pack PACK.json --owner ACCOUNT_ID --operator OPERATOR_ID --rights-reference RIGHTS_FILE --accept-publication
uv run python -m semaphore_hub D:/private/hub.db --csrf-key D:/private/csrf.key --assets D:/private/assets accept-artifact PACK_ID VERSION CONFIG.json --operator OPERATOR_ID
uv run python -m semaphore_hub D:/private/hub.db --csrf-key D:/private/csrf.key --assets D:/private/assets --origin http://localhost:8080 serve-foundation --port 8080
```

Installation uses SEMAPHORE_OLLAMA_BASE_URL and existing optional timeout,
batch-size and model-digest environment settings. PinnedEmbedder validates the
frozen complete identity; no synthetic provider/fallback is used. Manifest reads
are capped at 8 MiB. Explicit acceptance records operator, owner and rights
reference; it does not claim independent human content acceptance. Artifact JSON
contains exactly initial_board, schedule, seed and generator_policy (explicit null
where absent).

One process owns a database and asset root at a time, including installation,
startup cleanup and the listener lifetime. Nonblocking OS file locks reject
contention. Stop the listener before operator changes. Different databases cannot
concurrently use the same asset root. Stable .host.lock files remain after release;
do not remove them while a process runs. Migration holds the database lock too.
Direct library callers must acquire exclusive_host when accessing these resources.

The listener binds only 127.0.0.1, with eight workers, sixteen queued connections,
five-second socket timeouts and a 16 KiB request cap. It rejects ambiguous framing,
preserves duplicate headers for auth checks and closes every connection. Saturated
workers close excess connections. Remote/TLS exposure needs reviewed W3/W4 host
composition; changing --origin does not add TLS.

Validation: `uv run --no-sync pytest tests/hub/test_host.py -q` passes 8 tests:
real socket signup/pack reads/logout, invalid Host/body framing/size, secret
readiness, operator bootstrap/reset, input caps, cross-process and shared-asset
lock contention. Targeted Ruff lint/format and git diff whitespace checks pass.
