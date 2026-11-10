"""Regenerate the clearly labelled browser recording from the real arcade reducer."""

import json
from pathlib import Path

from semaphore_core.game import ClueCommand, GameArtifact, complete, initial_state, snapshot, submit


def recording():
    labels = [
        "moon",
        "telescope",
        "midnight",
        "ocean",
        "compass",
        "lighthouse",
        "orbit",
        "forest",
        "cloud",
        "piano",
        "river",
        "mountain",
        "garden",
        "rain",
        "window",
        "lantern",
        "island",
        "sunrise",
        "train",
        "snow",
        "bridge",
        "paper",
        "wind",
        "kite",
    ]
    entries = {f"word-{n:02}": {"label": label} for n, label in enumerate(labels)}
    ids = list(entries)
    artifact = GameArtifact(
        mode="casual",
        identities=dict(
            pack_digest="recorded-practice",
            model_fingerprint="scripted-not-real-model",
            ruleset_id="experiment-arcade-paced-v1",
            config_digest="spacious-arcade-20-3",
            challenge_digest=None,
        ),
        entries=entries,
        initial_board=tuple(ids[:6]),
        schedule=tuple(dict(at_ms=(n + 1) * 5000, entry_id=i) for n, i in enumerate(ids[6:])),
        deadline_ms=95000,
        capacity=20,
        zone_size=3,
        score_pacing=True,
        test_mode=True,
    )
    state = initial_state(artifact, game_id="spacious-arcade")
    frames = []

    def append(receipt=None):
        frames.append(
            dict(
                protocol="experiment-v1",
                sequence=len(frames),
                kind="receipt" if receipt else "snapshot",
                snapshot=snapshot(state, now_ms=state.elapsed_ms),
                receipt=receipt,
            )
        )

    append()
    for n in range(10):
        now = (n + 1) * 3000
        # A read first keeps command revisions consistent with arrivals.
        from semaphore_core.game import advance

        state = advance(state, now_ms=now).state
        append()
        command = ClueCommand(f"practice-{n}", state.revision, "a recorded association")
        admitted = submit(state, command, now_ms=now, inference_slot_available=True)
        state = admitted.state
        append(admitted.receipt)
        ranked = [i for i in state.board if i != state.target]
        ranked.insert(min(2, len(ranked)), state.target)
        result = complete(
            state,
            command_id=command.command_id,
            now_ms=now,
            scores={i: float(len(ranked) - j) for j, i in enumerate(ranked)},
        )
        state = result.state
        append(result.receipt)
    return dict(
        fixture_version="experiment-v1",
        provenance="Engine-generated scripted practice; clues do not determine outcomes",
        envelopes=frames,
    )


if __name__ == "__main__":
    path = Path(__file__).resolve().parents[2] / "web/practice/spacious-arcade.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(recording(), indent=2) + "\n")
