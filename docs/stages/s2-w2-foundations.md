# Stage 2 W2 — Parallel implementation

November 16, 2026 (Asia/Shanghai). State: W2 implementation and bounded acceptance complete; Stage 1/W4 gates retained.
Common baseline: `8ac07292ed469be28f755edd28dd4e711ed79c75`.

The owner requested “get started with W2 using parallel sub agents”. This explicitly
authorizes bounded Stage 2 W2 implementation. It does not declare Stage 1 accepted.
The 100 ms latency target, full human acceptance, remote-host offline/resource
isolation, independent content review and population sourcing yield remain open.
Follow-up remains controlled real-model measurement and human/content review in
Stage 2 acceptance; synthetic account/pack/browser checks cannot close these gates.

W1 implementation baseline: `92aaffb0594ea329489b3df1eeea6336312edda3`.
W1 evidence baseline: `c37e504`. The common W2 dispatch commit includes this record
and the maintained Argon2 dependency. Workers use isolated worktrees and frozen
W1 interfaces. Shared changes remain coordinator-owned.

| Session | Owned paths | State |
| --- | --- | --- |
| B accounts | `packages/semaphore_hub/auth/`, `tests/hub/auth/`, account evidence | Integrated locally |
| C packs | `packages/semaphore_hub/packs/`, `tests/hub/packs/`, pack evidence | Integrated locally |
| D browser | `web/`, `tests/web/`, browser evidence | Integrated locally |

Detailed scope and acceptance: [implementation briefs](s2-w1-session-briefs.md).
No W3 dispatch, real-model/human acceptance or production readiness is claimed.


## Integrated implementation slice

All three workers used the same dispatch commit in isolated worktrees:
accounts `8718153`, packs `d321b93`, browser `08861a9`. The coordinator reviewed
and integrated their work, plus real shared SQLite transaction composition and
an authenticated framework-neutral account/pack HTTP dispatcher. No network
listener or fake game-service fallback is introduced. The transaction integration
checks cover account/pack rollback together, reopen persistence and independent
thread-owned connections. HTTP integration checks prove persisted sessions guard
pack reads and logout revokes access.

Worker evidence: [accounts](../evidence/s2-w2-accounts.md),
[packs](../evidence/s2-w2-packs.md), [browser](../evidence/s2-w2-browser.md).
Independent review corrected cookie lifetime, account-switch response races,
same-game uncertain-command recovery, artifact count limits and retirement during
verification. The existing experiment entry and regression tests are retained.

## Remaining W2 acceptance and later waves

The implementation is a bounded foundation slice, not a complete playable durable
server. Coordinator host CLI/listener composition and an actual trusted installation
with accepted content/report/artifact provenance remain open before W2 closure.
The authored MIT everyday pack is a candidate, not automatically published content.
W3 durable games, lifecycle/recovery and independent fault probes are not dispatched.
W4 still owns real browser/service wiring and signed-in real-model/human acceptance.
The browser currently has fixture evidence; uncertain clue bodies remain memory-only
across page reload. The installer needs a bounded underlying model transport and
holds its slot until synchronous work returns; timeout cannot kill a blocked call.
All named Stage 1 carryovers above remain open. Nothing has been pushed.

## Combined validation

- `uv run --no-sync pytest -q`: 387 passed.
- `node --test tests/web/*.test.mjs`: 20 passed.
- `uv run --no-sync ruff check .`: passed.
- `uv run --no-sync ruff format --check .`: 144 files formatted.
- `git diff --check`: passed.
- `uv build --no-build-isolation`: wheel and source distribution built.
- Worker Playwright fixture browser journey passed; details in browser evidence.

These results cover the integrated code, including coordinator composition checks.
They do not imply real-model, human, complete-service or Stage 1 acceptance.


## W2 completion — November 16, 2026

The owner requested finishing W2 before parallel W3. The remaining operator
bootstrap/reset/install/artifact CLI and bounded loopback account/pack listener
are implemented; see [host runbook](../operations/w2-host.md). Cross-process DB
and asset locks prevent install/cleanup races. The foundation listener rejects
DBs requiring W3 game/deletion recovery. This is intentionally not the W4 LAN
browser/game deployment.

[Fresh real installation](../evidence/s2-w2-installation.md) published the exact
235-entry authored MIT pack after pinned-model verification: 233 reachable entries
(99.1489%), 705 clues, 51,074 ms. Accepted artifact, exact retry and reopen checks
passed. Private runtime data stays ignored. Review also fixed browser uncertainty
and stale private state across account changes, retaining same-account recovery.

This supersedes the remaining-W2 items above. All named Stage 1 carryovers and
W4 signed-in real-game/human acceptance remain open. No production readiness,
independent human content approval or latency-target closure is claimed.

Closure validation: 395 Python tests, 23 Node tests, Ruff lint/format, package build and diff checks passed.

