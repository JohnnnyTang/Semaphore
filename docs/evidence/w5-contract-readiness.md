# W5 contract readiness review

Reviewed November 11, 2026 against `64e3a90`. The [project plan](../../PROJECT_PLAN.md)
sets the exit criteria. Owner decisions on lightweight local accounts, private
clue capture, 6–8 players and development Ollama supersede conflicting
[handoff](../../Semaphore%20%E2%80%94%20Handoff.md) language. The
[W3 closure](../decisions/0004-w3-gate-closure.md) authorized a bounded
prototype and retained the 100 ms target. The W2 platform contracts remain
proposals. The promoted contracts define the experiment.

## Stage 1 gate audit

| Exit criterion | Evidence and remaining work |
| --- | --- |
| A person plays a real-model browser game through game over and sees the server score | The [W4 record](../stages/s1-w4-playable-experiment.md) has an actual HTTP binding browser smoke with a scripted interaction. The W5 real-model run must establish the person, real embedding and terminal-score criteria together. |
| Deterministic replay, challenge independence and retry safety | W4 replays ten frozen traces against the reducer and checks HTTP retry/score boundaries. The frozen challenge schedule remains independent of player actions. Paced casual uses a different ruleset and later tests. Preserve both identities and cover paced transitions when selecting the durable contract. |
| Local and server verification agreement | W4 has fresh-process core/reference parity on fixtures and separate Python/Node real-vector numeric checks. The [creator walkthrough](w5-creator-walkthrough.md) repeats parity on repackaged bytes with synthetic vectors, with 900 sample/clue comparisons at `1e-5`. Integrated real-model parity is W5 evidence. There is no upload verifier in the experiment. |
| Model quality and game feel | [Model evaluation](model-evaluation.md) records 100% contextual top-3 on both general and difficult-biology synthetic held-out views, compared with 94.44% and 91.67% using labels alone. Context and clues share authoring provenance. [W3 protocol results](w3/README.md) separate authored, weak and mixed synthetic manifests. Human play and observation of confusing results remain necessary to decide game feel. The 0.85 protocol value is diagnostic. |
| Warmed p95 at 1/4/8 players with verification pressure | The W3 repeat records adapter p95 of 160/287/475 ms. W4 synthetic load demonstrates orchestration. W5 must record real server round trips, overlap, queue/deadline outcomes and named hardware, then measure again after an explicit tuning or scope decision if p95 exceeds 100 ms. |
| CPU/RAM and offline startup | A configured, cached LAN adapter is the development path. W4 evidence does not establish CPU-only operation on 8 GB or startup with internet removed. Capture process and model-host resource behavior, model residency/offload and cold startup on the selected reference setup. |
| Contracts sufficient to dispatch independent Stage 2 work | Experiment boundaries are executable. Durable transport, identity, privacy and competition decisions below remain open. |
| Default corpus feasibility | [Source and cost review](content-sources.md) supplies a viable authored fallback, source restrictions and planning ranges. Rights for candidate source combinations and usable yield remain unmeasured. |
| Stage decision | **Revise.** Contract review alone cannot close Stage 1. Record W5 measurements and human observations alongside these findings before adjudicating the gate. |

## Interfaces that need a durable decision

| Boundary | Finding and correction needed before dependent implementation |
| --- | --- |
| Accounts and LAN transport | Local accounts are confirmed. [Platform draft](../contracts-drafts/platform.md#accounts-and-transport) covers normalized login, opaque sessions, origin/CSRF checks and operator bootstrap/reset, but open registration, reset/session policy and LAN HTTPS versus explicitly scoped development HTTP are still proposals. Adopt signup and transport policy and bind the browser-facing session/CSRF/origin contract before separating auth and client work. Password-library and parameter measurement can follow in Stage 2. |
| Version identity and storage | The [promoted storage draft](../../contracts/storage.md) gives `unique(owner_id, pack_id, version)`. Taken alone, that key permits two owners for one public pack ID. The [platform storage draft](../contracts-drafts/storage.md) instead uses global pack IDs and `unique(pack_id, version)`, matching ownerless public pack routes. Adopt a single namespace, reservation and immutable-version identity. Bind transaction edges for score finalization, exact retry and restart interruption. Production migrations and publication jobs can follow in their respective stages. |
| API/events | The [promoted API](../../contracts/openapi.json) serves unauthenticated, process-local `/experiment/v1` HTTP commands, snapshots and receipts. The [W2 platform API](../contracts-drafts/openapi.json) proposes authenticated `/api` routes and a WebSocket event transport with different envelopes and receipt behavior. Choose the durable game transport, exact receipt/reconnect semantics and terminal reasons. Publish matching contracts for the account, game and score paths before parallel Stage 2 work. Retain upload and event administration as later-stage surfaces. |
| Private data | Owner-authorized clue retention covers private use for future feedback. The promoted storage draft leaves duration/deletion open and refers to internal operator roles, while the platform draft proposes 30 days, disclosed before play, and filesystem/database access with no raw admin-web endpoint. Specify actual retention and operator access, deletion scope for raw clues and command payloads, and linked account/score handling. A command retry can compare a canonical payload digest after raw-clue deletion if its lifetime exceeds raw payload retention. Define this alongside backups and the retry window. |
| Ruleset and board identity | The default casual artifact carries `experiment-arcade-paced-v1`. The verifier accepts only `experiment-arcade-v1`, although [verification prose](../../contracts/verification.md#sampling-and-metrics) requires the report ID to equal the calling game's pin. The walkthrough reproduced `invalid_ruleset` for the paced ID. Choose an explicit versioned relation between verification policy and playable rules, or support distinct verified rulesets. Separately pin score eligibility/cohorts across mode, pack version, model, ruleset and scoring-relevant configuration. Settle equal-score ordering, one row per game versus best per account, and interruption/quit treatment before durable results. |
| Model portability | [The lock](../../contracts/model-lock.json) pins selected development artifact, Ollama version and exact encoder settings. Full fingerprint equality includes raw `model_details.parent_model`, a host path in the retained evidence. If relocation changes that string, a byte-identical artifact fails today's equality check. Preserve the experiment fingerprint and decide on a separately versioned portable identity with recorded runtime details and independent-device parity. A release hardware selection and creator bundle remain later acceptance. |
| Verification cost | Current adapter HTTP batches bound each request, but the callable verifier retains all returned query vectors and scores each clue against every entry before selecting sample subsets. At the schema maximum this alone means 125 million 2,560-component dots (320 billion component products), before hard-decoy and duplicate-pair passes. These are operation counts from the implementation. Adopt a supported work budget and isolate game-priority inference before binding large-pack acceptance or publishing limits. Benchmark runtime and memory on a bounded pilot, including cancellation and contention, before Stage 3 publication. |

## Prototype inventory

| Retain | Scope and replacement boundary |
| --- | --- |
| Shared manifest, hashing, lexical and verification core, packaged schemas, ranking and deterministic sampling | Retain tested normalization, numeric rules and trust checks. Evolve identities and budget through versioned changes. Lexical subset and 0.85 diagnostic are experiment choices. |
| Pure reducer, immutable artifact identity, retry ordering and replay tests | Carry forward authoritative scoring, monotonic ordering, deterministic event timing and command idempotency. Pin the durable game mode and configuration before scoring cohorts begin. |
| Thin browser, accessible controls, responsive stack and reduced-motion behavior | Reuse interaction and state-ordering logic. Bind transport, account/game ownership, durable result and interruption UI to the adopted production contract. |
| Frozen reference verifier, semantic/manifest/replay fixtures and independent probes | Retain as regression and measurement tooling. Generated vectors, tutorial/practice artifacts and synthetic metrics remain development inputs. |
| Experimental server binding, process-local game registry, tombstones and FIFO worker | Retain behaviors and instrumentation as evidence. Replace the disposable session, auth-free routing, receipt retention and game-only queue with bounded durable boundaries. |

## Corpus risk and bounded correction

The W2 fixture has 150 authored entries and 450 clues. It proves shape and
coverage on a deliberately balanced sample. The [source review](content-sources.md)
identifies a WordNet notice obligation, wordfreq data terms that differ from its
code license, and unresolved redistribution rights for the concreteness dataset.
Do not bundle unresolved source data. Preserve notices, source snapshots and
rights statements for any source selected. At 3–5 clues per entry, 3,000–5,000
entries require 9,000–25,000 clues. The 40–60% candidate survival assumption and
380–480 review hours for a 3,000-entry scenario are planning estimates.

A bounded Stage 1 correction would collect the outstanding real-model, offline
and human evidence and resolve the account, durable game/score and privacy
interface decisions above. Use a small independent clue/pack pilot to inspect
human confusion and declared-test overfitting. The 500-candidate rights-cleared
yield and review-timing probe in the source review should precede full corpus
staffing. Keep full publication calibration, real independent creator acceptance
and maximum-size production verification as later gates. If a remaining Stage 1
criterion still fails, record its specific failure and next bounded test before
expanding Stage 2.
