# Platform, account and private-data proposal

Status: W2 draft. Schemas bound payloads; this document specifies authorization,
cross-field constraints and lifecycle rules that JSON Schema cannot prove.

## Accounts and transport

Confirmed: local username/password accounts, no email or external identity provider.
Proposed: open local registration; all signed-in players may publish; only the
pack owner may add versions. Pack attribution is untrusted display content, not
ownership evidence. Admin role does not implicitly transfer another user's pack.

Login names are ASCII letters/digits/underscore, 3–32 characters, lowercased for
unique lookup. Display names are separate, NFKC/whitespace-normalized, 1–64 code
points; escape them when rendered. Passwords are not trimmed, casefolded or Unicode
normalized; propose 12–128 code points for registration/reset (login accepts old
credentials up to the same bound). Use a maintained password-hashing library with
versioned Argon2id parameters chosen and measured in Stage 2. No homegrown crypto,
plaintext password storage, browser-submitted role or security answer recovery.

An operator command creates the first admin and resets passwords using an
interactive secret prompt; no default account/password and no command-line secret
argument. Reset revokes all that user's sessions. No public role change endpoint.
Open registration can be disabled by operator configuration. Login failures use a
generic response without confirming whether the account exists; proposed limits
are five attempts/minute/account and twenty/minute/source, with bounded counters.

Sessions use cryptographically random opaque tokens (at least 256 bits), with only
token digests in SQLite, rotated on login and privilege change; proposed absolute
expiry 24 hours and idle expiry 8 hours. Cookie: HttpOnly, SameSite=Strict, Path=/,
and Secure when using HTTPS. Production account transport requires a deliberate
Stage 2 deployment decision: HTTPS on the LAN is preferred. Plain HTTP exposes
password/session traffic to the LAN and is only an explicitly selected trusted
development deployment; it must not be advertised as transport-secure.

State-changing HTTP requests require an exact configured Origin allowlist and a
session-bound CSRF token in `X-CSRF-Token`; registration/login require an allowed
Origin even before a session exists. Do not accept wildcard CORS with credentials.
WebSocket upgrade checks session and exact Origin; reject unauthorized upgrades
before opening. Do not send session tokens in URLs. Authenticate ownership on
every read/write, not just at game creation. Rate limits never replace auth.

## HTTP semantics

`openapi.json` lists routes and payload schemas. All requests use JSON and reject
unknown fields; no client payload contains a score, role, spawn choice or vector.
Authenticated read endpoints return 404 for another user's private game/job IDs.
Admin endpoints return 403 to non-admin accounts. Pack browse and boards expose
only published visible versions; hidden versions return 404 except explicit
owner/admin management views (deferred). Page size ≤100; opaque cursors ≤200 chars
are validated server-side. Public responses omit accounts' login names and IDs.

| Situation | HTTP |
| --- | --- |
| New local account/game/event | 201 |
| Accepted upload job | 202 with job ID; no claim of publication |
| Identical upload retry | 200 with existing job/result |
| Successful logout/moderation | 204, no body |
| Bad JSON, schema/hygiene, body cap | 400, 422, 413 |
| Missing auth, denied role, invisible/not-owned object | 401, 403, 404 |
| Owner/version/idempotency conflict | 409 |
| Busy queue/rate limit | 429 plus Retry-After |
| Unavailable model/runtime | 503 or terminal failed job |

New owner reservation and job staging happen in one short transaction. The
`Idempotency-Key` is scoped to authenticated uploader, endpoint and full request
digest. Same key/digest returns the same job even across reconnect; same key with
different bytes conflicts. Keep the mapping until terminal job retention expires
(propose 30 days); immutable version identity persists afterward. A new key cannot
create a duplicate job for the same reserved version. Published same owner/ID/
version and same full digest is a successful idempotent retry; different digest is
`version_conflict`, even if only the self-reported report changed. A different
owner always receives `owner_conflict`. Temporary reservations release only after
a failed/rejected initial upload has no other pending work; never steal an owned ID.

Job states: `pending → running → published | rejected | failed`. Schema/ingestion
errors fail synchronously before a job exists. Semantic quality failures reject;
runtime errors fail. The request may not modify a running job's manifest. On restart,
pending work may resume from immutable staged bytes; running jobs become failed
with `restart_interrupted` unless the entire deterministic verification is rerun.
Never publish partial results. Hidden packs reject new games and publication while
existing games finish under their pinned version. Hide/unhide does not delete history.

## Game transport proposal for reconciliation with C

HTTP creates/reads a game; `/api/games/{id}/events` uses a WebSocket authenticated
as that game's owner. `events.schema.json` describes frames; maximum serialized
client frame is 2 KiB, one in-flight clue per game. A 32 KiB cap bounds server
snapshots. Board index 0 is bottom/most related; rank 1 means that entry. Server
monotonic elapsed integer milliseconds are independent of browser clocks.

Each command has an opaque ID, expected revision and clue. Server retains the ID,
payload digest and result for the entire active game and at least the reconnect
window after ending (proposed 24 hours). Identical retries return the stored
outcome without reapplying state/score/logging. A reused ID with different payload
returns `command_conflict`. Check duplicate IDs before stale revision so a retry
still works after intervening spawns. A fresh stale command rejects with the current
snapshot; it does not silently apply to a different target. Rejection/spawn/revision
ordering and inference completion semantics must match C's final traces in W3.

Every server message includes a full authoritative state and current revision,
command ID or null, and server time. `rejected` requires an error; other event
types prohibit it. `game_over` requires a terminal state. Terminal states require
an end reason and null next spawn; running states require null end reason, and a
nonempty board's target must exist on that board. Those semantic invariants are
validated separately from the schema. Score can only increase via server rules;
one final result per game. The browser cannot send a score or change a schedule.

Reconnect always starts with a fresh snapshot, not unbounded event replay. Browser
keeps the latest revision; older snapshots cannot rewind visuals. A duplicate
outcome can still acknowledge its command without replacing a newer snapshot.
Disconnect does not pause game time. A server restart marks in-memory games
interrupted and records no completed competitive score. C/W3 settles duration,
overflow versus finite-pack completion eligibility and final state details.

Cross-draft review found that this envelope is not yet implementation-ready:
C's pending-command state and structured receipt (result, applied revision and
rank independent of current snapshot) are missing here. Pending versus miss and
reconnect recovery therefore require W3 reconciliation. End reasons also differ:
C proposes `pack_cleared`, `pack_exhausted`, `event_complete`, while this draft
uses `exhausted`/`duration`. Do not independently implement either draft as frozen.

## Privacy and retention

Confirmed: private accepted/rejected clue attempts are retained for future pack
feedback. This is not permission to show raw clues to creators. Proposed default:
30 days from receipt, configurable by operator, with startup and daily cleanup.
The UI must disclose capture and actual retention before play; never call the data
anonymous. Private game-to-account association enables linkage despite pseudonymous
attempt IDs. Public pack test clues are different data and remain in version history.

Persist only attempt ID, game/command IDs, target ID, receive/resolve timestamps,
bounded clue, legality/rejection code, target rank if computed, clear outcome and
rules/model identity through the game. One attempt per accepted command ID,
including rejected attempts; transport rejects before authenticated game admission
do not capture arbitrary bodies. Do not store cookies, IPs, user agents or password
fields in clue records. Never copy raw clues to app/access logs, telemetry, error
traces or build fixtures. Use safe structured error codes.

No creator or public API exposes attempt rows in v1. Game owner sees their current
command result, not a historical export; admin web role alone does not expose raw
logs. Operator maintenance access is restricted by filesystem/database permissions,
and any future export requires a separate reviewed privacy design. Cleanup deletes
attempt rows and private command-result payloads past their retention; retain only
non-clue deduplication identifiers as needed. Account deletion policy remains open;
it must include linked private attempts and sessions while preserving a defined,
de-identified competition history. W3 records the policy rather than implying it
has been implemented.

Backups containing private rows inherit their retention and access policy. Deleting
live rows cannot guarantee erasure from unmanaged backups; operator procedures must
expire snapshots. Private attempts cannot appear in pack packages or report exports.

## Review boundaries

These are design requirements, not an implemented security system. Stage 2 must
verify cookie/origin/CSRF behavior, password/session lifecycle, concurrent owner
reservation, immutable retries and retention deletion with independent tests.
