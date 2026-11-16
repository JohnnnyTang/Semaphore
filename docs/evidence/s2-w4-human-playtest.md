# W4 signed-in human playtest record

Status: one owner-reported real-model round and restart retrieval observed on
November 16, 2026. Automated checks remain separate; unreported usability and
quality observations stay open.

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
| Date/time and timezone | November 16, 2026, Asia/Shanghai |
| Participant alias / consent to play | Owner; explicitly agreed in this chat |
| Application commit / browser | `3c76d66` human-serving code; participant browser not collected |
| Hub host / OS / CPU / RAM | Windows 10, i5-13490F, 10 cores / 16 logical processors, 34,164,101,120 bytes physical RAM; remote model hardware unmeasured |
| Exact HTTP origin | `http://localhost:18747` |
| Pack ID / version / manifest digest | Everyday discoveries 1.0.0; exact digest in W2 installation evidence |
| Artifact ID / config digest | W2 accepted artifact `f321eb5386b446acba1e9a7996d47bf1`; config digest in W2 evidence |
| Model fingerprint / endpoint host identity | Pinned Qwen3-Embedding 4B; fingerprint below; owner-supplied endpoint |
| Real inference readiness evidence | Ollama check passed; PinnedEmbedder in actual serve-durable process |

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
| Signup/login and pack choice understandable | Initial failure; signup corrected | Owner reported generic invalid_request. Visible policy hints and local field validation added; owner then created an account. Ease of pack choice not separately rated. |
| Target and clear-zone ranks understood unaided | Not observed | |
| Real clue response and target movement understandable | Not observed | |
| Rejection/miss/clear feedback, as encountered | Not observed | |
| Natural terminal reason and authoritative score visible | Pass | Owner reported Score 1000, Level 3, pack_exhausted. |
| Exact-artifact board agrees with result | Pass | Owner confirmed 1,000 in both results and board after restart. |
| Same result retrieved after actual host process restart | Pass | Process stopped and replaced; owner reloaded and confirmed both views. Read-only SQL comparison found one unchanged 1,000-point score row. |
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

Disposition: revise within W4 for the failed performance gate; the reported
one-person completion and restart retrieval pass. A one-person successful game may
satisfy this signed-in product observation, but does not close Stage 1's broader
human acceptance, controlled 1/4/8-player latency, 100 ms p95, remote-host offline,
resource-envelope or independent content/source-yield gates. Keep those separate.


## Observed session details

Owner authorized the playtest in this chat and used the local HTTP origin
`http://localhost:18747`. The pinned Qwen3-Embedding 4B provider was confirmed at
fingerprint `657120305f464d0fb6a6006b9dbc8152af04ba30317dadcef1b41af0aa2941a4`.
The separate playtest database reused the exact W2 accepted Everyday discoveries
v1.0.0 manifest/assets/artifact described in [installation evidence](s2-w2-installation.md).
Retained immutable assets stayed at their original absolute path; a copied asset
root correctly failed startup validation before traffic. No synthetic inference
was used. Controlled load did not begin until the owner reported completion.

The corrected signup and 250 ms polling assets were served at `3c76d66`; backend
was unchanged through `b6e8046`. Host process exec sessions changed from `86152`
to `61254` for the restart, with a completed stop before replacement startup.
Before/after private score comparison remains ignored under `data/s2-w4-human/`;
no credentials, participant clue text or key files are retained in Git.

Disposition: the single-person completion/result/restart observation passes.
Target/clear-zone comprehension, perceived delay, enjoyment and signout were not
reported and remain unobserved; broader Stage 1 human acceptance remains open.
