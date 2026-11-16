# Stage 2 W3 — Durable services and independent probes

November 16, 2026. State: first implementation slice integrated; W3 acceptance remains open.
Common dispatch baseline: `2a00a4334227274abfdf29ea9eb86c3571b95057`.
W2 closure commit: `dc32882`. The owner requested finishing W2 then starting W3
with parallel subagents. All named Stage 1 and W4 gates remain open.

Three isolated worktrees start from one committed baseline. Owned paths and
acceptance follow [the frozen briefs](s2-w1-session-briefs.md): E durable games
and results; F retention/recovery/deletion/encrypted backups; G independent
subprocess fault probes. Coordinator owns dependencies, shared composition,
contracts and final integration. Cryptography is locked for maintained authenticated
backup encryption. Workers must not modify shared schemas or import peer trees.

This dispatch starts W3 implementation; it does not claim W3 acceptance, real
signed-in browser integration, human review or release readiness.


## Integrated first slice

All three workers completed from the common baseline in isolated worktrees:
E games/results `73de8d4`, F operations `7584f88`, G probes `a19e2e8` with
contract-oracle corrections `4288878` and `01d6021`. The coordinator integrated
all changes and added bounded runtime locks/inference, external versioned HMAC
keys, concrete shared transactions and authenticated game/result HTTP composition.

Games use the real reducer and immutable installed artifact pins. Operations use
real SQLite retention/erasure, external authenticated deletion records and
AES-GCM encrypted backups. Independent subprocess probes detect deliberately
faulty fake adapters; their fake passes are not real-service crash evidence.

Cross-domain validation combines the real game lifecycle with operations: pending
admission, clue deletion/interruption without a score, exact retry preservation,
account erasure and encrypted restore replaying the newest external ledger. The
authenticated dispatcher rejects missing auth, invalid Host/Origin/CSRF and oversized
bodies before game mutation. These use synthetic inference, not model-quality data.
Independent review fixed browser account state (W2), malformed URLs, oversized
cursor numbers, whitespace quit parsing and failed-restore plaintext sidecars.

Evidence: [games](../evidence/s2-w3-games.md),
[operations](../evidence/s2-w3-operations.md),
[independent probes](../evidence/s2-w3-independent-probes.md).

## Remaining W3 integration and W4 acceptance

- Implement the real E/F subprocess adapter and execute all independent commit-window
  crash, ownership/retry/cohort/deletion and restore probes against it.
- Compose durable startup/ledger/key/asset readiness, tick/daily-cleanup/backup
  scheduling and operator commands into the host. The W2 listener remains
  foundation-only and refuses game-bearing databases; DurableHttp is a reusable
  dispatcher, not a newly deployed complete service.
- Validate retained HMAC versions against all restorable backups and immutable
  asset availability in the concrete restore host. Operator callbacks alone are
  not an unattended scheduler or a completed restore deployment.
- W4 owns real signed-in browser/service play, controlled model load and human
  acceptance. All Stage 1 latency, independent content/source-yield, human and
  remote-host offline/resource gates remain open. No work was pushed.


## Combined validation

- `uv run --no-sync pytest -q`: 447 passed.
- `node --test tests/web/*.test.mjs`: 23 passed.
- Ruff lint and format: passed (183 files).
- Wheel/source package build, legacy hub smoke and diff whitespace: passed.
- Final inference memory-release change: all four runtime adapter tests passed.

All pre-existing frozen-contract tests remain in the suite; the new dispatcher
checks use a separate composition test file. These results establish the integrated
first slice, not completion of the remaining W3/W4 acceptance items above.
