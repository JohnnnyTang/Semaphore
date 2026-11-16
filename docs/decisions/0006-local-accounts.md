# 0006 — Local account and LAN session boundary

November 16, 2026. Adopted W1 implementation contract; production auth is W2 work.
The owner confirmed open local signup (operator-disableable) and LAN-only HTTP.
This decision settles account proposals in the historical platform draft. It does
not close Stage 1 performance/human/offline gates or authorize W2 dispatch.

## Identity and passwords

Login is 3–32 ASCII letters/digits/underscore, lowercased without trimming. It is
unique across live accounts. Public display names are separate: 1–64 code points
before and after NFKC, Unicode whitespace collapsed to ASCII spaces; reject empty
results and remaining category-C characters. Escape names on rendering. Do not
expose login names/account IDs in boards or pack attribution.

Registration/reset passwords contain 12–128 code points; login permits 1–128 for
legacy credentials. Reject lone surrogates. Preserve every other code point;
never trim, normalize, casefold or log a password. A maintained Argon2id library
must produce versioned encoded hashes with random salts. Initial profile is
64 MiB, time cost 3, parallelism 1, 32-byte output and at least 16-byte salt.
Do not implement password hashing in shared policy helpers.

W2 must measure this exact profile on the selected host: record OS/CPU/RAM/library
version, 5 warmups, 30 serial hash and verify samples, then 30 paired-concurrent
samples. Report p50/p95 and peak RSS; check success and wrong-password paths.
Two expensive operations may run concurrently; no unbounded waiting queue. This
is a measurement protocol, not measured performance. Parameter changes return to
the coordinator for a versioned decision and remeasurement, never silent weakening.

Signup is enabled by default and its switch is exposed through GET /api/v1/config.
Disabled signup returns 403 without creating anything; existing login continues.
Successful signup creates an ordinary account and logs it in. The first operator
is created only by an interactive host command, never a default password, public
role field or password CLI argument. Operator reset prompts for a new password
and atomically revokes every session for the account. No public reset or role API.

## Session, request and CSRF lifecycle

Cookie name: `semaphore_session`; opaque 32-random-byte token, base64url encoding.
Encode base64url without padding (43 ASCII characters). Use HttpOnly, SameSite=Strict, Path=/, no Domain. Set Secure only on HTTPS. The
selected LAN HTTP deployment carries passwords and tokens unencrypted and must
not be exposed publicly or described as transport-secure. Session token digests alone
are stored in SQLite: lowercase hexadecimal SHA-256 of the exact 43-character
ASCII bearer token, without decoding or normalization. Absolute expiry is 24 hours from creation; idle expiry is
8 hours from last successfully authenticated request, capped by absolute expiry.
At equality the session is expired. Rejected authentication does not renew it.

POST /api/v1/auth/signup and /auth/login require the exact configured Host and
Origin even before a session exists; absent/null/foreign Origin is rejected.
Successful login revokes the presented prior session, issues a fresh session
cookie and a session-bound 32-random-byte CSRF token; other device sessions remain
valid. Successful signup uses the same issuance flow. Privilege changes revoke
all old sessions; a subsequent login creates a new session. Login responses are
generic for unknown account and wrong password, including bounded dummy hash
verification for unknown accounts after admission to password-work limits.

GET /api/v1/auth/session authenticates the cookie and returns private account
identity, absolute/idle expiry and the current CSRF token. CSRF is stable during
that session, not rotated by every read. Persist only a CSRF digest. Derive the 32-byte CSRF value as HMAC-SHA-256
using the separate 32-random-byte server CSRF key over the byte prefix
`b"semaphore-csrf-v1\0"` followed by the exact ASCII session bearer token.
Encode the result as base64url without padding (43 ASCII characters). Store
lowercase hexadecimal SHA-256 of those 43 ASCII characters in `csrf_digest`.
Never expose the digest as a bearer token. Recompute for session responses and
compare request-token digests in constant time after checking the exact encoding.
Derivation key is separate from command HMAC keys and kept outside SQLite. This
key has a single active version: rotation atomically revokes every session before
new issuance. Missing key fails issuance closed; an explicit operator replacement
revokes all sessions before service resumes. Never silently generate a replacement.
Login/signup return the same session envelope. Session/token responses use
Cache-Control: no-store and are never logged or placed in URLs.

All cookie-authenticated mutations, including logout, require exact configured
Host, exact Origin and X-CSRF-Token equal to the session token under constant-time
comparison. Every request validates Host; reads reject a supplied foreign/null
Origin, while same-origin reads may omit it. Do not trust forwarded Host or Origin
headers; reverse-proxy deployment requires a later explicit trusted-proxy policy.
Reject duplicate security headers at the HTTP parser. No wildcard credentialed
CORS; no cross-origin CSRF issuance. Logout returns 204, revokes that session and
expires the cookie with the same attributes. Missing/expired sessions return 401.

## Bounded abuse controls

Login and signup share admission counters: at most five attempts per normalized
login and twenty per source address in a rolling 60-second window. Source is the
socket peer, not a forwarded header. Bound the combined counter map to 4096 keys;
remove expired entries, then refuse new keys with 429 if full rather than evicting
live limits. Reject before expensive hashing; at most two password operations can
run, with immediate 429 when occupied. Return Retry-After, minimum 1 second.
Counters are process-local and reset on restart; they are not a distributed abuse
control. Never persist source addresses or raw credential bodies in clue records.

Enforce the 16 KiB body cap before JSON parsing, reject unknown fields, malformed
JSON and duplicate keys. Authentication/Origin/CSRF/schema failures have no game,
clue or score side effects. Operator-only host commands are separate from public
HTTP. W2 must test these boundaries before real-service integration.
