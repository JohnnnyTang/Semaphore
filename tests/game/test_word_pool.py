import json
import random

import pytest
from experiments.game_server.artifacts import DEFAULT_MANIFEST, prepare_artifact, sample_round
from experiments.game_server.service import GameService
from tests.core.test_verification import FakeEmbedder

from semaphore_core.verification import parse_manifest


@pytest.fixture(scope="module")
def binding():
    return prepare_artifact(DEFAULT_MANIFEST.read_bytes(), FakeEmbedder())


def sequence(artifact):
    return (*artifact.initial_board, *(spawn["entry_id"] for spawn in artifact.schedule))


def test_default_pool_is_valid_and_round_is_bounded(binding):
    # The parser checks normalized uniqueness, coverage and clue legality too.
    manifest = parse_manifest(DEFAULT_MANIFEST.read_bytes()).manifest
    assert len(manifest["entries"]) >= 200
    artifact, vectors = binding
    assert set(vectors) == set(artifact.entries)
    assert len(artifact.initial_board) == 6
    assert len(sequence(artifact)) == 125
    assert artifact.deadline_ms == 600000


def test_sampling_covers_full_pool_without_replacement(binding):
    artifact, _ = binding
    original = sequence(artifact)
    rounds = [sample_round(artifact, rng=random.Random(seed)) for seed in range(20)]
    assert len({sequence(item) for item in rounds}) == len(rounds)
    assert set().union(*(set(sequence(item)) for item in rounds)) == set(artifact.entries)
    for item in rounds:
        assert len(sequence(item)) == len(set(sequence(item))) == len(original)
        assert [s["at_ms"] for s in item.schedule] == [s["at_ms"] for s in artifact.schedule]
        assert item.identities == artifact.identities
        assert item.deadline_ms == artifact.deadline_ms
    assert sequence(artifact) == original
    assert sequence(rounds[0]) == sequence(sample_round(artifact, rng=random.Random(0)))


def test_each_casual_session_samples_once_and_reconnect_keeps_sequence(binding, monkeypatch):
    calls = []

    def draw(artifact):
        result = sample_round(artifact, rng=random.Random(len(calls)))
        calls.append(result)
        return result

    monkeypatch.setattr("experiments.game_server.service.sample_round", draw)
    service = GameService({"default": binding}, FakeEmbedder(), clock=lambda: 0)
    try:
        ids = []
        for _ in range(2):
            status, envelope = service.request(
                "POST",
                "/experiment/v1/games",
                json.dumps(dict(artifact_id="default", mode="casual")).encode(),
            )
            assert status == 201
            ids.append(envelope["snapshot"]["game_id"])
        assert len(calls) == 2
        assert sequence(calls[0]) != sequence(calls[1])
        for ident, artifact in zip(ids, calls, strict=True):
            service.request("GET", f"/experiment/v1/games/{ident}")
            assert service.sessions[ident].state.artifact is artifact
            assert service.sessions[ident].state.board == artifact.initial_board
        assert len(calls) == 2
    finally:
        service.close()


def test_events_keep_fixed_order_and_identity():
    artifact, _ = prepare_artifact(DEFAULT_MANIFEST.read_bytes(), FakeEmbedder(), mode="event")
    assert sample_round(artifact) is artifact
    assert sequence(artifact) == tuple(artifact.entries)[:125]
    assert artifact.identities["challenge_digest"]


def test_small_pool_is_exhausted_without_duplicates():
    raw = DEFAULT_MANIFEST.read_bytes()
    manifest = json.loads(raw)
    manifest["entries"] = manifest["entries"][:40]
    manifest["test_set"] = {e["id"]: manifest["test_set"][e["id"]] for e in manifest["entries"]}
    artifact, _ = prepare_artifact(json.dumps(manifest).encode(), FakeEmbedder())
    result = sample_round(artifact, rng=random.Random(7))
    assert len(sequence(result)) == 40
    assert set(sequence(result)) == set(artifact.entries)
    assert result.deadline_ms == 175000
