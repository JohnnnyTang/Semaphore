# W3-E durable games/results first implementation slice

November 16, 2026 (Asia/Shanghai). Common dispatch baseline:
`2a00a4334227274abfdf29ea9eb86c3571b95057`.

Implemented transaction-scoped SQLiteGames, injected-runtime GameService,
GamesHttp and ResultsService. Services use the real immutable reducer. No model,
key, lock or production-auth fallback is embedded. The default asset loader reads
installed vector caches and checks their digest. Create validates published report
trust, model pins, manifest/config/artifact digests, config fields and exact entries;
it rechecks the live account in the insertion transaction after asset loading.

Admission captures one original clue attempt with a versioned HMAC over canonical
original command bytes. Known IDs precede command budget checks. Exact/changed
retries remain distinguishable after raw deletion and restart. Pending receipts,
reducer snapshots and natural terminal scores commit atomically. Interrupted games
have no score. State advances in memory only after successful commit; failed
admission cancels logical inference, while injected inference retains physical
slot ownership. Timeout, pin mismatch, terminal and late callbacks cannot score.

Shared host composition API:

- `SQLiteGames(connection)` implements the frozen Games port.
- `GameService(transactions, inference, keys, locks, clock=..., artifact_loader=...)`
  provides create/get/command/receipt/quit/current and lifecycle interrupt/forget.
- `tick()` is the host scheduler hook for due work without browser traffic.
- `GamesHttp(games, results).handle(principal, method, target, body)` requires
  outer authentication and Host/Origin/CSRF validation before dispatch.
- `ResultsService(transactions)` provides history and exact-artifact-cohort boards.

Public board projection contains no player/account IDs. Pagination scopes cursors
to private owner or complete cohort and uses score/completion time/game ID. Tests
exercise equal score AND completion-time ties, distinct artifact boards, foreign
history cursors and oversized numeric cursor values.

Validation:

- `uv sync --locked --group dev`: passed in isolated worktree.
- `uv run --no-sync pytest tests/hub/games tests/hub/results -q`: 16 passed.
- Full Python regression before the final malformed-URL/cursor/quit edge regression:
  410 passed in 75.87 seconds. Final targeted rerun above includes those changes.
- `uv run --no-sync ruff check .`: passed.
- `uv run --no-sync ruff format --check .`: passed.
- `git diff --check`: passed.

Coverage includes real SQLite persistence/reopen, exact/altered retries after raw
removal, restart interruption/pending settlement, once-only completion, late
callbacks, overload, natural due-work before quit (including zero score), owner
hiding, create/account-erasure race, admission and completion commit failures,
HTTP body/ownership errors and corruption of trusted pins.

Limitations and next acceptance: model vectors in unit tests are synthetic and
installation verification is explicitly stubbed there. This is not real-model or
human acceptance. Coordinator must compose authenticated routes, shared runtime,
startup operations and periodic tick; run independent subprocess crash probes
against that integrated service, then W4 signed-in browser/model validation.
Restore, backup, deletion ledger and retention orchestration belong to F. The
snapshot returned after restart interruption intentionally retains the last durable
observed elapsed time because process-local monotonic time cannot be reconstructed.
No Stage 1 retained gate is closed by this evidence.
