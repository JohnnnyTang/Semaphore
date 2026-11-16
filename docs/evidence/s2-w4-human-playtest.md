# W4 signed-in human playtest record

Status: prepared November 16, 2026; **not yet observed**. Do not mark a row passed
until the named person actually performs it. Automated browser runs and generated
clues are separate evidence and cannot fill the observations below.

## Before the participant starts

The coordinator records the exact application commit, host/OS/CPU/RAM, browser,
origin, accepted pack/version/manifest digest, artifact/config digest and pinned
model fingerprint. Confirm real query inference is enabled, installed assets pass
readiness, and no load/verifier pressure run overlaps this human session. The
operator should use a dedicated acceptance database, not a live competition.

Give the participant this short explanation: clues are private but retained up to
30 days; encrypted backups can retain deleted clues for up to 30 additional days.
The connection is local HTTP. Ask them to choose a password in the browser; never
request it in chat or record it in evidence. Record confusing behavior using entry
IDs and aggregate observations rather than raw participant clue text.

| Session field | Observed value |
| --- | --- |
| Date/time and timezone | Pending |
| Participant alias / consent to play | Pending |
| Application commit / browser | Pending |
| Hub host / OS / CPU / RAM | Pending |
| Exact HTTP origin | Pending |
| Pack ID / version / manifest digest | Pending |
| Artifact ID / config digest | Pending |
| Model fingerprint / endpoint host identity | Pending |
| Real inference readiness evidence | Pending |

## Participant flow

1. Open the coordinator-provided durable room URL. Create a local account or sign
   in and read the private-clue disclosure.
2. Choose the accepted round and select the disclosure checkbox. Start a round.
   Identify the target and ranks 1–3 as the clear zone without coaching. Record
   whether the UI made that understandable.
3. Submit several associations. Observe the ranking/result message and target
   changes. Note whether rejection, a miss and a clear are understandable where
   those outcomes occur. Do not force an observation that did not happen.
4. Let the round finish naturally. Do not use End round for the competitive-score
   check. Record the terminal reason and authoritative score from Your results.
5. Open This round's board for the same selected artifact. Confirm the exact score.
6. Tell the coordinator the round has finished. Keep the tab open while the
   coordinator stops and restarts the actual hub process using the same database,
   assets and retained external keys/ledger. Do not substitute a page reload.
7. Reload the page, sign in again only if asked, and use Refresh results and Show
   board. Confirm the result and score survived. The coordinator verifies the
   game ID in the private history and that only one score row exists.
8. Sign out. Confirm private history and game details disappear.

| Observation | Result: pass / fail / not observed | Notes without raw clues |
| --- | --- | --- |
| Signup/login and pack choice understandable | Not observed | |
| Target and clear-zone ranks understood unaided | Not observed | |
| Real clue response and target movement understandable | Not observed | |
| Rejection/miss/clear feedback, as encountered | Not observed | |
| Natural terminal reason and authoritative score visible | Not observed | |
| Exact-artifact board agrees with result | Not observed | |
| Same result retrieved after actual host process restart | Not observed | |
| Signout clears private display | Not observed | |
| Overall enjoyment / confusing associations | Not observed | |

## Coordinator restart and result evidence

Record old and new process IDs, stop/start timestamps, pre-traffic recovery outcome,
game ID, terminal reason, score, exact cohort, completed-at value, and before/after
score-row count. Keep credentials, cookies, CSRF tokens, key files and raw clue
rows out of screenshots, reports and Git. Do not close a failed gate by deleting
an unsuccessful run; retain aggregate errors and explain corrective changes.

The automated runner supports a separate two-phase restart check documented in
[the browser README](../../web/README.md). Its output proves reads across the
chosen boundary only. Pair it with actual operator process-restart evidence; the
browser cannot independently prove that the server process was replaced.

## Disposition

Pending actual participant observations. Record proceed / revise / stop, reasons,
issues and follow-up owners after the session. A one-person successful game may
satisfy this signed-in product observation, but does not close Stage 1's broader
human acceptance, controlled 1/4/8-player latency, 100 ms p95, remote-host offline,
resource-envelope or independent content/source-yield gates. Keep those separate.
