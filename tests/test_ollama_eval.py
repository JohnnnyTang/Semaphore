"""Exercise measurement orchestration with scripted vectors, not semantic evidence."""

import copy
import json
from types import SimpleNamespace

import pytest
from experiments.model_eval.ollama_eval import (
    FORMAT,
    check_calibration,
    evaluate,
    main,
    score_vectors,
)

from semaphore_core.embeddings import EmbeddingResponseError, fingerprint_hash


def tiny_fixture():
    entries = [{"id": name, "label": name, "embed_text": name} for name in ("a", "b", "c", "d")]
    return {
        "seed": 42,
        "entries": entries,
        "packs": [
            {"id": "good", "entry_ids": [e["id"] for e in entries]},
            {"id": "weak-generic", "entry_ids": [e["id"] for e in entries]},
        ],
        "cases": [
            {
                "id": "legal",
                "target_id": "d",
                "category": "test",
                "clue": "clue",
                "expected_legal": True,
                "split": "calibration",
                "candidate_ids": ["d", "c", "b", "a"],
                "hard_decoy_ids": ["a", "b"],
            },
            {"id": "illegal", "expected_legal": False, "split": "calibration", "clue": "illegal"},
            {"id": "held", "expected_legal": True, "split": "held_out", "clue": "held-out"},
        ],
    }


class ScriptedClient:
    config = SimpleNamespace(batch_size=16, timeout_seconds=30, expected_digest=None)

    def __init__(self):
        self.inputs = []
        self.identity_calls = 0
        self.change_identity = False

    def identity(self):
        self.identity_calls += 1
        return {
            "digest": "changed" if self.change_identity and self.identity_calls > 1 else "fixed"
        }

    def embed_queries(self, texts):
        self.inputs.extend(texts)
        return [(0.0, 1.0) if t == "thing" else (1.0, 0.0) for t in texts]

    def embed_entries(self, texts):
        return [(1.0, 0.0) if t == "d" else (0.0, 1.0) for t in texts]

    def running_model(self):
        return {"test_stub": True, "digest": "fixed"}


def test_ranking_pack_separation_and_stable_ties():
    fixture = tiny_fixture()
    vectors = [(0.0, 1.0)] * 3 + [(1.0, 0.0)]
    result = score_vectors(
        fixture, fixture["cases"][:1], [(1.0, 0.0)], fixture["entries"], vectors, (0.0, 1.0)
    )
    assert result["metrics"]["20/all"]["top3_rate"] == 1
    assert result["cases"][0]["top3"] == ["d", "a", "b"]
    assert result["pack_metrics"]["good"]["median_rank"] == 1
    assert result["pack_metrics"]["weak-generic"]["top3_rate"] == 0


def test_evaluation_excludes_illegal_and_held_out_clues_and_records_provenance():
    client = ScriptedClient()
    result = evaluate(client, tiny_fixture(), "calibration", 2, 2, "fixture-digest")
    assert "illegal" not in client.inputs and "held-out" not in client.inputs
    assert result["fingerprint_sha256"] == fingerprint_hash({"digest": "fixed"})
    assert result["performance"]["warm_serial_request_ms"]["n"] == 2
    assert result["performance"]["concurrent_request_ms"]["n"] == 2
    assert result["text_modes"]["label"]["metrics"]["20/all"]["count"] == 1


def test_tag_change_invalidates_measurement():
    client = ScriptedClient()
    client.change_identity = True
    with pytest.raises(EmbeddingResponseError, match="identity changed"):
        evaluate(client, tiny_fixture(), "calibration", 1, 1, "fixture-digest")


def test_loaded_model_mismatch_invalidates_measurement(monkeypatch):
    client = ScriptedClient()
    monkeypatch.setattr(client, "running_model", lambda: {"digest": "other"})
    with pytest.raises(EmbeddingResponseError, match="loaded model digest"):
        evaluate(client, tiny_fixture(), "calibration", 1, 1, "fixture-digest")


def test_held_out_requires_matching_calibration_before_embedding():
    client = ScriptedClient()
    with pytest.raises(ValueError, match="matching calibration"):
        evaluate(client, tiny_fixture(), "held_out", 1, 1, "fixture-digest")
    assert not client.inputs
    identity = {"digest": "fixed"}
    report = {
        "format_version": FORMAT,
        "status": "measured",
        "split": "calibration",
        "fingerprint": identity,
        "fingerprint_sha256": fingerprint_hash(identity),
        "fixture_sha256": "fixture-digest",
    }
    check_calibration(report, identity, "fixture-digest")
    for key in ("status", "split", "fixture_sha256", "fingerprint_sha256"):
        invalid = copy.deepcopy(report)
        invalid[key] = "wrong"
        with pytest.raises(ValueError):
            check_calibration(invalid, identity, "fixture-digest")


def test_validate_runs_without_network_or_endpoint(monkeypatch, capsys):
    monkeypatch.delenv("SEMAPHORE_OLLAMA_BASE_URL", raising=False)
    main(["validate"])
    result = json.loads(capsys.readouterr().out)
    assert result["model_contacted"] is False
    assert result["fixture"]["held_out_targets"] == 60


def test_existing_evidence_is_not_overwritten(tmp_path):
    output = tmp_path / "existing.json"
    output.write_text("preserve me")
    with pytest.raises(SystemExit):
        main(["run", "--output", str(output)])
    assert output.read_text() == "preserve me"
