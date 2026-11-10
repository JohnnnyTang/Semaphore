"""Explicit test-only binding for legacy authored traces; never reads expectations."""

from .game import ClueCommand, GameArtifact, advance, complete, initial_state, snapshot, submit


def artifact_from_trace(trace):
    initial = trace["initial_state"]
    return GameArtifact(
        mode=trace["mode"],
        identities=dict(
            pack_digest="synthetic-fixture",
            model_fingerprint="synthetic-fixture",
            ruleset_id="experiment-arcade-v1",
            config_digest="synthetic-fixture",
            challenge_digest=trace.get("challenge_id"),
        ),
        entries=trace["entries"],
        initial_board=initial["board"],
        schedule=trace["schedule"],
        deadline_ms=trace["deadline_ms"],
        capacity=trace["config"]["capacity"],
        zone_size=trace["config"]["zone_size"],
        test_mode=True,
        initial_score=initial["score"],
        initial_clears=initial["clears"],
    )


class TraceReplay:
    def __init__(self, trace):
        self.state = initial_state(artifact_from_trace(trace), game_id="trace")

    def step(self, event):
        kind, now = event["kind"], event["at_ms"]
        was_over = self.state.end_reason is not None
        if kind == "admit":
            transition = submit(
                self.state,
                ClueCommand(event["command_id"], event["expected_revision"], event["clue"]),
                now_ms=now,
                inference_slot_available=True,
            )
            result = transition.receipt["outcome"]
        elif kind in ("complete", "fail"):
            transition = complete(
                self.state,
                command_id=event["command_id"],
                now_ms=now,
                scores=event.get("scores"),
                error="inference_failed" if kind == "fail" else None,
            )
            result = (transition.receipt or transition.state.receipts[event["command_id"]])[
                "outcome"
            ]
        else:
            transition = advance(self.state, now_ms=now)
            result = (
                "snapshot"
                if kind in ("read", "disconnect", "reconnect")
                else "ignored_terminal"
                if was_over
                else transition.state.end_reason or "spawn"
            )
        self.state = transition.state
        public = snapshot(self.state, now_ms=now)
        keys = (
            "status",
            "board",
            "target",
            "score",
            "clears",
            "level",
            "revision",
            "next_spawn_index",
            "pending",
            "end_reason",
        )
        return {"result": result, "state": {k: public[k] for k in keys}}
