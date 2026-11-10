# W2-D platform and creator contract drafts

Status: **proposal for W3 reconciliation, not a frozen implementation interface**.
Baseline: `80ebde2bec2289002f9bd58c6e131ad8627dc9d8`. Prepared November 8, 2026.

These drafts carry forward confirmed local accounts, private clue capture,
server-owned scores, immutable pack versions and independently recomputed hub
verification. Registration policy, retention, verification thresholds, model,
ruleset and event behavior remain proposals until W3 reviews B/C/D together.

| File | Contract |
| --- | --- |
| `manifest.schema.json` | Strict publication-manifest shape; no vectors or unknown fields |
| `http.schema.json`, `openapi.json` | Bounded request/response shapes and route/auth/error map |
| `events.schema.json` | Client command and server snapshot/event envelope proposals |
| `verification.schema.json` | Hub report and fully specified embedding fingerprint shapes |
| [format-and-verification.md](format-and-verification.md) | Parsing, semantic checks, canonical hashes, verification bounds |
| [platform.md](platform.md) | Identity, authorization, private logs, jobs and protocol behavior |
| [storage.md](storage.md) | Annotated relational model and transaction/recovery invariants |
| [Creator kit](../design/creator-kit.md) | CLI contract and future skill outline |
| [Manifest fixtures](../../fixtures/manifests/README.md) | Passing/failing cases and validation command |

Schema validity is necessary, never sufficient, for publication. Fixture checks
exercise the drafts without implementing a server, model adapter or production CLI.
The positive pack is authored synthetic data, not a measured playable pack.

## W3 reconciliation checklist

- Select a measured model revision and exact runtime/encoding fingerprint from B.
  No placeholder fingerprint may publish a real pack.
- Reconcile C's state names, board order, revisions, equal-time ordering,
  command retry rules and end reasons with these event proposals. JSON schemas
  intentionally use `draft-w2` IDs and do not freeze C's work in progress.
  Specifically, C needs pending-command state and a structured receipt containing
  result, applied revision and rank separately from the latest snapshot. This
  draft does not yet distinguish pending versus miss or fully describe reconnect
  recovery. C's `pack_cleared`, `pack_exhausted`, `event_complete` reasons also
  need mapping to or replacement of D's `exhausted`/`duration` proposals.
- Freeze Unicode/legality and canonical serialization versions. Review the hash
  vectors, including changed metadata/report versus changed clues/entry order.
- Calibrate duplicate and reachability thresholds; specify exact random sampling
  algorithm and hard-decoy fraction, not just a seed. Until then verification
  cannot claim cross-process parity or final publication decisions.
- Decide open signup/publishing, admin-started events, 30-day private-log retention,
  deployment transport and account session lifetime. These are recommendations.
- Promote reviewed schemas into `contracts/`, publish callable interfaces, and
  integrate event fixtures. This session makes no changes there.

## Specification references

Schemas use [JSON Schema 2020-12 validation](https://json-schema.org/draft/2020-12/json-schema-validation)
and the route document uses [OpenAPI 3.1.1](https://spec.openapis.org/oas/v3.1.1.html).
The fixture runner checks schema syntax and sample payloads; it does not claim a
complete OpenAPI interoperability audit. Storage requires explicit per-connection
[SQLite foreign-key enforcement](https://www.sqlite.org/foreignkeys.html).
Our constrained canonical encoding is versioned separately from
[RFC 8785 JCS](https://www.rfc-editor.org/rfc/rfc8785); implementations must not
silently substitute one for the other.
