"""Operator-only artifact construction; no client-defined identities or vectors."""

import hashlib
import random
from dataclasses import replace
from pathlib import Path

from semaphore_core.embeddings import fingerprint_hash
from semaphore_core.game import GameArtifact
from semaphore_core.verification import canonical, manifest_hashes, parse_manifest, vector

DEFAULT_MANIFEST = Path(__file__).resolve().parents[2] / "packs/everyday.json"


def sample_round(artifact, *, rng=None):
    """Draw a fresh casual sequence without replacement; events stay identical.

    Sampling the sequence once makes future arrivals and streak refills stable
    across polling, retries and reconnects. All pool entries remain eligible.
    """
    if artifact.mode != "casual":
        return artifact
    count = len(artifact.initial_board)
    ids = (rng or random.SystemRandom()).sample(
        list(artifact.entries), count + len(artifact.schedule)
    )
    return replace(
        artifact,
        initial_board=tuple(ids[:count]),
        schedule=tuple(
            dict(at_ms=spawn["at_ms"], entry_id=ident)
            for spawn, ident in zip(artifact.schedule, ids[count:], strict=True)
        ),
    )


def prepare_artifact(raw, embedder, *, mode="casual", interval_ms=5000):
    value = parse_manifest(raw)
    if type(interval_ms) is not int or interval_ms < 1:
        raise ValueError("invalid interval")
    entries = value.manifest["entries"]
    before = embedder.identity()
    rows = embedder.embed_entries([e.get("embed_text", e["text"]) for e in entries])
    vectors = {e["id"]: vector(row) for e, row in zip(entries, rows, strict=True)}
    if embedder.identity() != before:
        raise ValueError("identity changed")
    # Keep the full pool available while bounding each round to ten minutes.
    round_entries = entries[: 6 + 595000 // interval_ms]
    initial = tuple(e["id"] for e in round_entries[:6])
    schedule = tuple(
        dict(at_ms=(n + 1) * interval_ms, entry_id=e["id"]) for n, e in enumerate(round_entries[6:])
    )
    deadline = (schedule[-1]["at_ms"] if schedule else 0) + 5000
    config = dict(
        capacity=20 if mode == "casual" else 12, zone_size=3, interval_ms=interval_ms, mode=mode
    )
    if mode == "casual":
        config["sampling"] = "uniform-without-replacement-per-game-v1"
        config["special_clear"] = dict(
            streak=5, refill="scheduled_to_five_after_scoring", cascade="legal_target_in_zone"
        )
        config["pacing"] = dict(points_per_level=500, interval_step_percent=10, minimum_percent=40)

    def digest(data):
        return hashlib.sha256(canonical(data)).hexdigest()

    identities = dict(
        pack_digest=manifest_hashes(value).manifest_digest,
        model_fingerprint=fingerprint_hash(before),
        ruleset_id="experiment-arcade-paced-v1" if mode == "casual" else "experiment-arcade-v1",
        config_digest=digest(config),
        challenge_digest=None,
    )
    if mode == "event":
        identities["challenge_digest"] = digest(
            dict(
                initial_board=list(initial),
                schedule=list(schedule),
                deadline_ms=deadline,
                identities=dict(identities),
            )
        )
    artifact = GameArtifact(
        mode=mode,
        identities=identities,
        entries={
            e["id"]: dict(
                label=e["text"],
                aliases=e.get("aliases", []),
                forbidden=e.get("forbidden_clues", []),
            )
            for e in entries
        },
        initial_board=initial,
        schedule=schedule,
        deadline_ms=deadline,
        capacity=config["capacity"],
        score_pacing=mode == "casual",
    )
    return artifact, vectors
