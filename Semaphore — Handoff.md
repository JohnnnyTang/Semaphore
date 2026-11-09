# Semaphore — Handoff

Nov 8, 2026 · @Frankie Miller

## Purpose and vision

We are building Semaphore, a light, playful word-association arcade game, in the spirit of Google's [Semantris](https://research.google.com/semantris/), served on a LAN with one shared leaderboard and a hub where anyone can publish themed word packs.

This doc hands the agreed design to coding agents. Your first job is a detailed implementation plan for v1, not code. Treat "Decisions already made" as fixed; raise anything else under "Open questions".

The product is three things: the **engine** (game + semantic ranking), the **hosting** (one LAN server), and the **community** (packs, leaderboards, play stats). It does not provide LLM capabilities. Creators bring their own coding agents; we give them a skill and a test harness so the packs they make actually play well.

## Decisions already made

These are settled with the product owner. Plan around them; don't re-open them without a strong reason.

| Area | Decision |
| --- | --- |
| Name | Semaphore ("sema-", meaning, plus signalling: players signal meaning with clues) |
| Game modes | Arcade mode only (no Blocks mode) |
| Language | English only |
| Deployment | LAN only, one server machine; no internet needed at runtime |
| Architecture | Tiny server: the embedding model runs server-side, clients are thin browsers |
| Competition | One shared leaderboard per pack, visible to everyone on the LAN |
| Content | Themed word packs (majors like geography or biology, topics like film/TV), selectable by players |
| Community | A hub where users publish and share their own packs |
| AI in the hub | None beyond the embedding model. No local LLM, no LLM API calls from the server |
| Creation | Happens on the creator's machine with their own coding agent, using a skill + CLI we ship |
| Separation | Creating packs is fully separate from playing and hosting |
| Trust | Uploaded test results are re-verified by the hub; self-reported metadata is labelled as such |
| Feel | Light and playful; small footprint, minimal moving parts |

## System architecture

One Python server on the LAN holds the embedding model, the game logic, the pack store and the leaderboards; browsers only render. Pack creation lives entirely on creators' machines and reaches the hub only as an uploaded file.

&#91;embedded content: architecture · creator machine, hub server, players\]

Creators' agents draft and playtest packs locally against the same pinned model, then upload; the hub re-verifies, stores versions and runs every game. In v2, play stats flow back to creators as a feedback file.

| Component | Responsibility | Suggested tech |
| --- | --- | --- |
| Hub server | Game sessions, clue ranking, pack upload + verification, leaderboards, stats, hub API | Python 3.11+, FastAPI, Uvicorn |
| Embedding model | Embed clues live; embed pack words once per pack version | One sentence-embedding model held in memory, CPU is enough. Candidates: `bge-base-en-v1.5`, `gte-base`, `nomic-embed-text`. Pinned by name, revision, query/passage prefix and normalization |
| Storage | Packs, versions, words, sessions, scores, per-word stats | SQLite + pack files on disk; cached word vectors keyed by (pack version, model id) |
| Web client | Arcade game, hub browser, pack pages, leaderboards | Static HTML/JS served by the hub; keep the build light (vanilla, Preact or Svelte) |
| Creator kit | Create, validate, playtest and package packs locally | An agent skill (SKILL.md) wrapping a Python CLI, working name `packtool` |

The model pin is a contract shared by the hub and the creator kit. If the hub ever changes models, every pack is re-verified from its stored test clues (see verification).

## Arcade game design

The server owns every game: it holds the stack, picks targets, ranks clues and computes the score, so no score can be faked from the browser.

**Core loop**

1. Player picks a pack (and optionally a seeded challenge). The server opens a session and sends the starting stack with one highlighted target.
2. New words join the stack over time; the rate rises with level.
3. Player types a clue. The server checks it against clue rules, embeds it, scores it against every word on the stack, and returns the new order.
4. The client animates the re-sort, most related words to the bottom. If the target lands in the bottom zone it clears and a new target is chosen.
5. The game ends when the stack reaches the top. The server records the final score on that pack version's leaderboard.

**Clue rules** (enforced server-side): reject a clue that equals the target, contains it, or is its plural or stem; also reject the pack's per-word forbidden clues.

**Word spawning**

- Diversity: a new word must not be too similar to words already on the stack (cosine threshold, tunable), so one clue doesn't drag several targets down at once.
- Difficulty ramp: early levels spawn clearly unrelated words; later levels deliberately add decoys near the target. Use the pack's difficulty tiers when present.
- Seeded challenges: a deterministic RNG seeded per challenge gives every player the identical word sequence, so scores compare fairly.

**Tunables to expose in config**: stack height, bottom-zone size, spawn-interval curve, diversity and decoy thresholds, scoring (per clear, multi-clear bonus, time or level bonus). Initial values are for the planner to propose.

**Performance target**: a clue round-trip should feel instant on the LAN. One embedding plus a few dozen dot products on CPU fits well under 100 ms.

## Pack format

A pack is one JSON manifest: pack info, the words, the creator's test clues, the creator's test report and provenance. Vectors are never uploaded; the hub computes them. Publish the schema as a versioned JSON Schema shared by hub and creator kit.

| Section | Contents | Notes |
| --- | --- | --- |
| `spec_version` | Manifest schema version | Lets the format evolve |
| `pack` | `id`, `name`, `version`, `author`, `description`, `tags`, `language` (always `en`), `license` | `id` + `version` identify a leaderboard |
| `entries[]` | `text` (shown), optional `embed_text`, `aliases`, `forbidden_clues`, `tier` | `embed_text` lets a short label be embedded with more context |
| `test_set` | For each entry, several clues written by the creator's agent | The hub re-scores these; it is what makes verification possible |
| `test_report` | The creator's local playtest metrics | Shown as self-reported; the hub computes its own |
| `provenance` | Agent/LLM used, `packtool` version, embedding model id + revision used for testing | Shown as self-reported |

```json
{
  "spec_version": "1",
  "pack": {"id": "physical-geography-101", "name": "Physical Geography 101", "version": "1.0.0",
           "author": "nickname", "description": "Landforms and processes", "tags": ["geography"],
           "language": "en", "license": "CC-BY-4.0"},
  "entries": [
    {"text": "glacier", "forbidden_clues": ["glacial"], "tier": 1},
    {"text": "oxbow lake", "embed_text": "oxbow lake, a cut-off river meander", "tier": 2}
  ],
  "test_set": {"glacier": ["slow river of ice", "ice age", "crevasse"]},
  "test_report": {"reachability": 0.94, "mean_rank": 1.6, "flagged": ["loess"]},
  "provenance": {"agent": "self-reported string", "packtool": "0.1.0", "embedding_model": "<id>@<revision>"}
}
```

Limits for the planner to set: entry count range, max text length, clues per entry, file size. Long entries such as film lines are allowed but crowd the stack UI, so cap their length.

## Upload and verification

The hub trusts nothing it can recompute. On upload it re-runs every deterministic check with its own model, and the pack page shows the hub's numbers as **Verified** next to the creator's as **Self-reported**.

1. **Schema check.** Reject manifests that fail the JSON Schema or the size limits.
2. **Hygiene.** Normalize case and whitespace; reject exact duplicates; enforce length limits.
3. **Embed.** Embed all entries (using `embed_text` when present) with the pinned model; cache by (pack version, model id).
4. **Near-duplicates.** List pairs above the similarity threshold (around 0.8 cosine). Too many pairs fail the upload.
5. **Reachability.** For each entry, rank each of its test clues against the entry plus K decoys sampled from the same pack. An entry is reachable when its typical rank falls inside the game's bottom zone.
6. **Score.** Compute reachability %, mean rank, flagged entries and an overall playability score. Below a minimum score the upload is refused, with the flagged entries listed so the creator's agent can fix them.
7. **Publish.** Store the new version. If self-reported and verified numbers differ a lot, show a note (usually a different model was used locally).

**One shared core library.** Ranking, decoy sampling (seeded from the pack's content hash) and metrics live in one Python package used by both the hub and `packtool`. Same code plus same model means a creator's local result matches the hub's.

**Re-verification.** Because test clues are stored, the hub can re-verify every pack in a batch job whenever the model or the scoring code changes.

**Optional scoring endpoint.** A read-only, rate-limited endpoint lets creators on the LAN score clues against the hub's model without downloading it locally.

## Leaderboards and play stats

Each pack version has its own leaderboard, because packs differ in size and difficulty and editing words changes the difficulty.

- **Boards:** all-time and per seeded challenge, per pack version. A pack page shows the latest version's board, with older versions one click away.
- **Scores:** written only by the server at game end, never accepted from the client.
- **Live updates:** boards refresh without reload (polling or WebSocket; planner's call), so people in the same room see each other climb.

**Per-word play stats** are the best test of a pack, and they cost no LLM. For every entry, record how often it appeared as a target, how often it cleared, and the clues needed to clear it.

- The pack page shows its hardest and most-failed words.
- Creators get a "rarely cleared" list to feed back into their agent for the next version.
- Store clue text too: it is the richest signal. Whether clue logs are shown to creators, and how they are anonymized, is an open question.

## Hub features

The hub is where packs are found, judged and played. Each pack page shows the verified score next to the self-reported provenance, so players can tell a good pack before they play it.

| Feature | Phase | Notes |
| --- | --- | --- |
| Pack list, search by name and tag | v1 | Default pack pinned at the top |
| Pack page | v1 | Description, author, version history, verified metrics, self-reported provenance, leaderboard, Play button |
| Upload a pack / new version | v1 | Through the verification pipeline |
| Admin hide / unhide | v1 | Even on a LAN someone uploads something silly |
| Per-word stats on pack page | v2 | Hardest words, clear rates |
| Creator feedback export | v2 | "Rarely cleared" list as a file the creator's agent can read |
| Play counts, likes | v3 |  |
| Fork / remix a pack | v3 | Copies the manifest under a new id, crediting the original |
| Featured packs | v3 | Admin-curated |

**Identity.** The LAN needs just enough identity for leaderboards and pack ownership. A nickname plus a simple per-device token is the lightest option; the planner should confirm what the owner wants.

**Content note.** Quote-based packs (lines from films or TV) are allowed on the LAN. If the hub is ever exposed beyond the LAN, such packs raise copyright issues; titles, characters, places and props are a safer base.

## Creator skill and CLI

We ship a creator kit, not an AI: an agent skill that teaches any coding agent how to make a good pack, wrapping a plain CLI that also works without an agent.

**The CLI (`packtool`)**, built on the shared core library:

| Command | Does |
| --- | --- |
| `packtool init` | Scaffold a manifest with the current `spec_version` |
| `packtool validate` | Schema, duplicates, length limits, near-duplicate pairs |
| `packtool playtest` | Score the manifest's test clues with the pinned model (local, or via the hub's scoring endpoint); write `test_report` |
| `packtool report` | Human-readable summary: flagged entries, weak words, suggestions |
| `packtool package` | Fill `provenance`, stamp versions, produce the upload file |
| `packtool feedback` (v2) | Read the hub's "rarely cleared" export to guide the next version |

**The skill (SKILL.md + references)** tells the agent:

- the pack spec and limits;
- how to choose good entries: common, concrete, distinct, no near-duplicates; how to use `embed_text`, aliases and forbidden clues;
- how to write test clues the way players would: varied, natural, not just synonyms, and never the forbidden ones;
- the loop: draft → validate → playtest → fix flagged entries → repeat → package;
- the content note on quote-based packs.

The kit installs with one command and downloads the pinned model on first use. The skill format should work in any skills-capable agent; the CLI covers everyone else.

## Phasing and v1 scope

v1 is done when a creator makes a themed pack with their own agent and our skill, uploads it, the hub's verified numbers match their local ones, and several people on the LAN compete on its leaderboard.

**v1: engine, hosting, the creator loop**

- [ ] Shared core library: ranking, decoy sampling, metrics, manifest schema
- [ ] Embedding model chosen and pinned, with a small benchmark on candidate models
- [ ] Hub server: sessions, clue ranking, spawning, scoring, seeded challenges
- [ ] Web client: arcade game, pack list, pack page, leaderboard, upload
- [ ] Upload and verification pipeline, with Verified vs Self-reported on pack pages
- [ ] Per-pack-version leaderboards, live-updating
- [ ] Admin hide/unhide
- [ ] Default pack of about 3,000-5,000 words: frequency list (e.g. `wordfreq`) → concreteness ≥ 4 (Brysbaert et al. norms) → nouns (WordNet or spaCy) → model-aware cleanup → manual pass
- [ ] `packtool` (init, validate, playtest, report, package) and the creator skill v1
- [ ] Acceptance run: one themed pack made end-to-end with a coding agent

**v2: learning from play.** Per-word stats, the creator feedback export and `packtool feedback`, and the batch re-verification job.

**v3: community.** Play counts and likes, fork/remix, featured packs.

**What the planning phase should hand back:** repo layout; module breakdown; HTTP API spec; SQLite schema; manifest JSON Schema; model recommendation with benchmark method; proposed tunables; task breakdown with order and estimates; risks.

## Non-goals

Keeping these out is what keeps the app light.

- No LLM inside the hub: no pack generation, no hints, no AI opponents.
- No languages other than English.
- No Blocks mode or other game modes.
- No public internet deployment, accounts system or OAuth in v1.
- No in-browser model inference; clients stay thin.
- No uploading of embeddings or other model outputs by creators.

## Open questions

The planner should propose an answer for each, for the product owner to confirm.

- [ ] Identity: nickname + device token, or light accounts? Who is admin, and how is that set?
- [ ] Upload rights: can anyone on the LAN publish, or only approved creators?
- [ ] Embedding model choice, and the minimum server hardware it implies.
- [ ] Thresholds: bottom-zone size, near-duplicate cutoff, minimum playability score to publish.
- [ ] Clue logs: store them? Show them to pack creators? How to anonymize?
- [ ] Seeded challenges: daily, or started by an admin for an event?
- [ ] Leaderboard resets: never, per season, or admin-triggered?
- [ ] Creator kit distribution on a LAN without internet: should the hub also serve the `packtool` package and the model files for download?
- [ ] Pack license field: required, and with what default?
