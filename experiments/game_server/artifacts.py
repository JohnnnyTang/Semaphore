"""Operator-only artifact construction; no client-defined identities or vectors."""

import hashlib

from semaphore_core.embeddings import fingerprint_hash
from semaphore_core.game import GameArtifact
from semaphore_core.verification import canonical, manifest_hashes, parse_manifest, vector


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
    initial = tuple(e["id"] for e in entries[:6])
    schedule = tuple(
        dict(at_ms=(n + 1) * interval_ms, entry_id=e["id"]) for n, e in enumerate(entries[6:])
    )
    deadline = (schedule[-1]["at_ms"] if schedule else 0) + 5000
    config = dict(capacity=12, zone_size=3, interval_ms=interval_ms, mode=mode)

    def digest(data):
        return hashlib.sha256(canonical(data)).hexdigest()

    identities = dict(
        pack_digest=manifest_hashes(value).manifest_digest,
        model_fingerprint=fingerprint_hash(before),
        ruleset_id="experiment-arcade-v1",
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
    )
    return artifact, vectors
