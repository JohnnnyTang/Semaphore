# S2-W2-B — Local accounts

November 16, 2026 (Asia/Shanghai). Implemented against dispatch baseline
`8ac07292ed469be28f755edd28dd4e711ed79c75` in the isolated accounts worktree.

## Delivered boundary

`SqliteAccounts(connection)` implements the frozen Accounts port and never commits.
`AuthService(transaction_factory, policy, csrf_key, clock=None)` owns short committing
transactions, performs password work outside transactions, and exports credentials,
session, authenticate, logout, bootstrap, reset_password and revoke_all operations.
Reset atomically revokes sessions; a login rechecks identity/hash after verification
so concurrent reset/deletion cannot issue a stale session. Tombstones cannot sign in.
Operations requiring an operator run only through host composition; bootstrap refuses
an existing live operator. Account erasure orchestration remains W3 maintenance work.

`AuthHttp(service).handle(method, path, raw_header_pairs, body, peer)` returns
`Response(status, body, headers)`. Preserve raw header pairs in the HTTP adapter:
duplicate security headers must not be collapsed upstream. The socket peer supplies
rate-limit identity. It enforces exact Host/Origin, JSON content type, 16 KiB body
limit, duplicate JSON keys/unknown fields, CSRF, no-body logout, and no-store responses.
The socket parser must bound body acquisition before invoking the adapter. Transport
remains authorized LAN HTTP, with unencrypted passwords/session traffic; cookies use
HttpOnly, SameSite=Strict, Path=/, Max-Age=86400 (Secure only for HTTPS).

The externally supplied 32-byte CSRF key is mandatory. Missing keys fail startup;
a changed key invalidates existing sessions. Operator replacement must revoke all
sessions before new issuance/traffic (coordinator/W3 startup orchestration); this
service never silently generates replacement material. Public projection contains no
login name or hash; account IDs are confined to the private session response.

Admission bounds are process-local: five attempts/login, twenty/socket peer per
rolling minute, 4096 combined keys, two nonblocking Argon2 slots, no waiting queue.
The coordinator must share one service instance across requests. Monotonic time drives
limits; UTC drives session persistence. No secrets or request bodies are logged.

## Argon2 measurement

Command: `uv run --no-sync python -m semaphore_hub.auth.benchmark`.
Windows 10 build 19045, Intel Core i5-13490F, physical RAM 34,164,101,120 bytes,
Python 3.12.10, argon2-cffi 25.1.0, bindings 26.2.0. Frozen Argon2id profile:
64 MiB, time cost 3, parallelism 1, 32-byte output, random 16-byte salt.
Five warmups per operation, thirty serial samples and thirty concurrent pairs
(sixty operations) per operation. p95 is nearest-rank; synthetic credentials only.

| Operation | Serial p50/p95 ms | Paired p50/p95 ms |
| --- | --- | --- |
| Hash | 119.72 / 133.37 | 132.03 / 136.84 |
| Correct verification | 122.68 / 133.01 | 133.44 / 138.50 |
| Wrong-password verification | 114.13 / 122.79 | 134.06 / 141.75 |

Windows process peak working set across the run: 161,333,248 bytes. Concurrent
operations are bounded to two. These host measurements are password cost evidence,
not game inference latency or LAN throughput acceptance. Parameters remain unchanged.
The benchmark's peak-memory collection is Windows-specific.

## Verification and handoff

- `uv sync --locked --group dev`: passed in the isolated worker environment.
- `uv run --no-sync pytest tests/hub/auth -q`: 11 passed.
- `uv run --no-sync ruff check .`: passed.
- `uv run --no-sync ruff format --check .`: 133 files formatted.
- `git diff --check`: passed.

Tests cover case collisions, disabled signup with existing login, generic invalid
credentials, idle/absolute expiry equality, rotation/logout/reset, reset during
verification, tombstone rejection, CSRF/Origin/header/body/schema failures before
writes or session renewal, persisted digests, private projection, throttle map and
password slot bounds, commit failure rollback, and operator bootstrap restrictions.
HTTP listening and interactive secret prompting belong to coordinator composition.
W3 durable games/privacy operations and W4 real-service/human acceptance remain open;
no Stage 1 carryover is closed by these checks.
