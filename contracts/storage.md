# SQLite boundary for W4 and later persistence

W4 may use in-memory repositories implementing these identities; no production
migration or account service is claimed here. SQLite persistence is a draft W4
boundary. Enable foreign keys, use transactions and server-generated IDs/time.

| Record | Required identity and invariants |
|---|---|
| pack_versions | unique(owner_id, pack_id, version); immutable manifest bytes, digest, semantic_hash, vector_hash |
| verification_reports | version FK, fingerprint_hash, protocol_hash, ruleset_id, report bytes; untrusted self reports separate |
| vector_caches | unique(vector_hash, fingerprint_hash); ordered IDs, dimensions, validated vectors; trusted writer only |
| games | owner/player FK, pinned version/model/rules/schedule identity; revision, status, server clock origin |
| commands | unique(game_id, command_id); canonical payload, outcome; same ID different payload conflicts |
| scores | unique(game_id); terminal result recorded once in same transaction as game end |
| clue_attempts | unique(game_id, command_id); private clue/target, times, legality, outcome; no public export |

Same owner/pack/version plus identical raw digest is an idempotent retry;
different digest conflicts and needs a new version. Check ownership before
digest-based retry replies. Server identity establishes owner, never upload data.
Future publication exposes manifest, entries and recomputed report atomically;
W3 measured status alone is insufficient to publish. Reverification appends
reports and never mutates version content. Cache mismatch is a miss, not repair.

Private clue capture is owner-authorized for future feedback; creator visibility
is not authorized. Access restricted to internal operator roles. Retention period
and deletion jobs remain a production gate; W4 must not invent a public retention
promise. Do not log passwords, session tokens, raw upstream errors or participant
clues in public diagnostics. No raw participant clues belong in Git fixtures.
