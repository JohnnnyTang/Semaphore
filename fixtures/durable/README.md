# Durable HTTP fixtures

Synthetic W1 contracts only; none of these records represent published content,
real accounts, real credentials or participant clue captures. `payloads.json`
references local schemas. `scenarios.json` maps named payloads to operation paths
and HTTP outcomes; placeholder path parameters are filled by the test transport.
The uncertain-create scenario intentionally has no HTTP response: the browser must
explain the lost response and require an explicit choice before another creation.

Game envelopes retain the adopted `experiment-v1` wire label and schemas; durable
HTTP routing, ownership, persistence and retry guarantees are separate. Existing
trace envelopes supply pending/final/rejected samples without changing game rules.
A fixture transport must not claim to implement authentication, SQL durability,
cohort authorization or production recovery. Those are later-wave acceptance.

Cursors are opaque server-validated strings, at most 200 characters. Implementations
may use a bounded server-side cursor handle or a signed compact encoding; they must
bind account/query for history, full cohort plus score/time/game tie key for boards,
and query plus pack/version key for packs. Invalid, expired or mismatched cursor
returns 400 `invalid_cursor`; silently restarting or broadening the query is forbidden.
Board order is score descending, completion time ascending, game ID ASCII ascending.
History order is completion time descending, game ID ASCII ascending. All times are
UTC epoch milliseconds. A board resolves identity from an installed artifact rather
than trusting a client's model/config/version declarations.
