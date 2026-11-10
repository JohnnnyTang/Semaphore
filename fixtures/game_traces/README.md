# W2 game traces

These synthetic, author-authored examples are covered by the repository's MIT
license. They contain no participant clues or measured embedding scores. Every
trace uses fixture version `s1-w2-game-trace-1`, seed 1729, stable entry IDs,
display labels, a complete initial state and complete expected state after each
ordered event. Scripted scores are passed through the W1 `FakeRanker` interface.
The seed is context, not an assertion that the W2 fixture schedule was generated
by a frozen production RNG. The explicit schedule is authoritative.

Run from the repository root with the W1 development environment installed:

```sh
uv run --no-sync python fixtures/game_traces/validate.py
uv run --no-sync python -m unittest discover -s fixtures/game_traces -p 'test_*.py'
uv run --no-sync ruff check fixtures/game_traces
uv run --no-sync ruff format --check fixtures/game_traces
```

`validate.py` loads the core package directly from this checkout, so a plain
Python 3.12 executable works too. It has no third-party dependency beyond the W1
package. It asserts event results and full state equality, validates unique
finite spawns and event ordering, and compares the shared challenge pair. Test
failures retain the trace name and event index. Run without Python's `-O`, which
would disable assertions. Static expectations were authored as state transitions;
the validator does not regenerate or overwrite the expected results.

| Trace | Meaning |
| --- | --- |
| `legality-and-target-only-clear` | NFKC/case/punctuation, aliases, explicit forbidden and inflection forms, empty/long/control input, legal unrelated substring, finite pack clear |
| `exact-ties-and-miss` | Descending scores, ID ties, miss before clear |
| `inference-spawn-retry-and-reconnect` | New entries participate in pending inference; pending/final retries, conflicting payload, busy/stale rejection, inference failure, disconnect/reconnect, finite exhaustion |
| `equal-time-overflow-beats-inference` | Reaching capacity ends immediately; same-time completion cannot rescue the target |
| `empty-board-waits-for-event` | No target between spawns, late spawn resumes play, common event deadline |
| `event-player-clears` / `event-player-waits` | Identical initial state, schedule and end time; divergent actions, boards and scores; deadline beats completion |
| `fifth-clear-advances-level` | Fifth target clear increments level without other bonuses |
| `bottom-three-target-only` | All three words are reachable, but only highlighted target clears; another visible label is a legal clue |
| `equal-time-spawn-before-admission` | A nonterminal same-time spawn makes an old revision stale; a fresh command uses updated state |

The expected board is **bottom first**, unlike screen order. Target uses the
lexicographically smallest surviving entry ID. `complete.scores` must cover the
entire board at completion time, including intervening spawns. A receipt result
such as `clear` belongs to its command; the associated expected state is current
state, so an old receipt never rewinds the game. `disconnect`, `reconnect` and
`read` return snapshots without pausing or advancing revision. Timer events are
explicit: no test depends on wall-clock sleeps.

The local oracle exists to expose contradictions in the draft. It is not the W4
engine, does not test HTTP/WebSocket transport, auth, storage or model quality,
and must not be imported into production. W4 should independently implement the
frozen W3 rules and consume these static states (or explicitly version revised
fixtures). `test_validate.py` deliberately corrupts expectations and scheduling
to ensure the validator rejects those errors.

The draft does not implement production morphology or casual adaptive sampling.
`inflections` is finite fixture data, not an approved manifest field. Casual
traces supply chosen spawns explicitly; model thresholds, RNG and tier policy
remain W3 decisions. No near-tie tolerance is guessed from synthetic floats.
