# S2-W2-C — Trusted installed packs

November 16, 2026. Implementation ready for coordinator review from dispatch
`8ac07292ed469be28f755edd28dd4e711ed79c75`. No real model was contacted or content
published during this session.

## Delivered

`SQLitePacks(connection)` implements the frozen transaction-scoped pack port.
`PackService(transactions, asset_root, embedder, now_ms=..., monotonic=...)` exposes
host-only installation, explicit casual-artifact acceptance, recovery cleanup and
schema-shaped installed-pack/artifact read projections. Composition supplies the
shared TransactionFactory and validates HTTP authentication, Host and queries.
Repositories do not commit; services return success only after context commit.

Install checks explicit rights acceptance and live operator/owner identities,
reserves the namespace before digest/retry disclosure, retains namespace ownership
when a version fails, and rejects tagged synthetic/practice/tutorial content.
Manifest parser enforces strict JSON, hygiene and the 8 MiB cap. Installation adds
40–500 entries and <=5 clues each / 2500 total. One process-wide verification slot
has no waiting queue. Core verify_pack recomputes the exact locked model report;
caller reports and supplied vectors are not accepted. Provisional reachability
0.85 is read from the existing policy. The measured report remains unchanged;
a separate explicit publication decision records operator, rights reference and
time. This does not validate the provisional semantic-quality threshold.

The verifier's validated ordered entry vectors and exact original manifest bytes
are staged by digest, fsynced, rechecked and renamed within the selected asset
filesystem. Root ancestors and final existing files reject symlink/junction
redirects. The host must protect this directory against untrusted local writers.
Version, ordered entries, report, immutable vector cache and publication marker
commit together. Orphan cleanup is pre-traffic only and serialized with installs;
it preserves assets referenced by published rows/caches and fails pending slots.

Accepted casual artifacts validate through the unchanged GameArtifact reducer
contract. Their config binds the complete ordered board and schedule, explicit
seed/generator policy (null when absent), deadline, capacity, zone, pacing and
special-clear settings. Different board orders produce different cohort hashes.
At most 100 artifacts are accepted per version, enforced within the transaction
so frozen read DTOs stay representable. Namespace retirement is rechecked before
publication. Public projections omit owners, private account IDs and rights notes.

## Validation

- `uv sync --locked --group dev`: passed in the isolated worker environment.
- `uv run --no-sync pytest tests/hub/packs -q`: 18 passed.
- `uv run --no-sync ruff check .`: passed.
- `uv run --no-sync ruff format --check .`: 131 files formatted.
- `git diff --check`: passed before commit.

Tests use a temporary real SQLite database. Coverage includes concurrent first
claims, owner-before-digest, exact bytes/retry, conflicting bytes, failed verification,
missing/wrong model, timeout/threshold failure, unpublished legacy rows, explicit
operator/acceptance requirements, corrupt assets, orphan cleanup, immutable vector
tuples, artifact report pins, full config identity and frozen public JSON schemas.
Independent account-agent review produced fixes for artifact count and retirement
races, both covered by regressions. Unit success-path reports/vectors are explicitly
synthetic stubs; they establish storage/control flow, not semantic quality.

## Content and remaining acceptance

Existing `packs/everyday.json` is the bounded authored MIT candidate, with original
content/provenance retained in that file and the repository's content evidence.
It is not installed or accepted by this change. It may be passed as exact bytes to
the host installer only after the operator reviews rights/source provenance and
explicitly accepts it. The host must supply the real locked embedder and record
the returned report, accepted artifact and hashes for W4. A historical experiment
measurement is not substituted. No synthetic unit fixture is a public competition
artifact. Independent human/content review and source-yield gaps remain open.

The 600000 ms deadline is checked before/after each model operation and immediately
before publication. A synchronous underlying transport cannot be interrupted by
this service: compose bounded network timeouts; a blocked physical operation keeps
the verification slot occupied and never publishes a late result. This is not a
subprocess hard-kill guarantee. Model work runs outside SQLite transactions.

Coordinator HTTP/CLI composition, actual trusted installation and real-model/human
acceptance remain integration/W4 work. No Stage 1 latency, offline/resource,
human or content gate is closed by these tests.
