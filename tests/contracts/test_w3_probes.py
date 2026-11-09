"""Exercise protocol arithmetic, failure boundaries and independent runtime parity."""

import copy
import hashlib
import json
import math
import shutil
from datetime import datetime

import pytest
from experiments.w3.run import parity
from experiments.w3.verification import (
    ROOT,
    legal,
    load,
    manifest,
    measure,
    order,
    samples,
    vector,
)
from fixtures.manifests.check_examples import canonical, projected_hash

from semaphore_core.embeddings import EmbeddingResponseError


def pack():
    return json.loads((ROOT / "fixtures/w3/held_out-authored.json").read_bytes())


def basis(index=0):
    result = [0.0] * 2560
    result[index] = 1.0
    return result


class FakeEmbedder:
    def __init__(self, value, changed=False):
        self.value = value
        self.calls = 0
        self.changed = changed

    def identity(self):
        self.calls += 1
        result = copy.deepcopy(load("model-lock.json")["fingerprint"])
        if self.changed and self.calls > 1:
            result["ollama_version"] = "changed"
        return result

    def embed_entries(self, texts):
        return [basis(i) for i in range(len(texts))]

    def embed_queries(self, texts):
        return [
            basis(i)
            for i, entry in enumerate(self.value["entries"])
            for _ in self.value["test_set"][entry["id"]]
        ]


def test_exact_protocol_metrics_recompute_instead_of_trusting_self_report():
    value = pack()
    value["test_report"] = {"reachability": 0, "mean_rank": 20, "flagged": []}
    raw = canonical(value)
    report, _ = measure(raw, FakeEmbedder(value))
    assert report["metrics"]["reachability"] == 1
    assert report["metrics"]["mean_rank"] == 1
    assert report["flagged_entries"] == []
    assert report["semantic_hash"] == projected_hash(value)
    assert report["manifest_digest"] == hashlib.sha256(raw).hexdigest()
    with pytest.raises(EmbeddingResponseError, match="changed"):
        measure(raw, FakeEmbedder(value, changed=True))


@pytest.mark.parametrize(
    "change,code",
    [
        ("clue", "illegal_clue"),
        ("duplicate", "duplicate_entry"),
        ("coverage", "test_coverage"),
        ("vectors", "schema_invalid"),
    ],
)
def test_bad_pack_rejected_before_inference(change, code):
    value = pack()
    first = value["entries"][0]
    if change == "clue":
        value["test_set"][first["id"]][0] = first["text"]
    elif change == "duplicate":
        value["entries"][1]["text"] = first["text"]
    elif change == "coverage":
        del value["test_set"][first["id"]]
    else:
        value["vectors"] = []
    embedder = FakeEmbedder(value)
    with pytest.raises(ValueError, match=code):
        measure(canonical(value), embedder)
    assert embedder.calls == 0


@pytest.mark.parametrize(
    "row",
    [[1.0], [True] * 2560, [math.nan] * 2560, [math.inf] * 2560, [0.0] * 2560, [1e300] * 2560],
)
def test_bad_vectors_fail_instead_of_renormalizing(row):
    with pytest.raises(ValueError, match="invalid_vector"):
        vector(row)


def test_sampling_is_pool_order_independent_and_bound_to_semantics():
    vectors = {f"word-{i:02}": basis(i) for i in range(40)}
    actual = samples("a" * 64, "word-00", vectors)
    assert actual == samples("a" * 64, "word-00", dict(reversed(list(vectors.items()))))
    assert actual != samples("b" * 64, "word-00", vectors)
    for sample in actual:
        assert sample[:5] == [f"word-{i:02}" for i in range(1, 6)]
        assert len(set(sample)) == 19
        assert "word-00" not in sample
    with pytest.raises(ValueError):
        samples("a" * 64, "unknown", vectors)


@pytest.mark.skipif(shutil.which("node") is None, reason="Node required for independent parity")
def test_numeric_bucket_boundaries_negative_scores_and_ascii_ties():
    query = basis()
    scores = {"a": 0.2000049, "b": 0.2000051, "c": -0.2000049, "d": -0.2000051, "e": 0.2000049}
    rows = {}
    for entry_id, score in scores.items():
        row = basis(1)
        row[0], row[1] = score, math.sqrt(1 - score * score)
        rows[entry_id] = vector(row)
    result = parity([{"query": query, "entries": rows, "ordered": order(scores)}])
    assert order(scores) == ["b", "a", "e", "c", "d"]
    assert result["ordered_ids_equal"]
    assert result["max_score_error"] == 0


def test_lexical_scope_is_explicit_and_normalization_precedes_matching():
    assert not legal("ＣＡＲＳ", {"text": "car"})
    assert legal("carpet", {"text": "car"})
    assert not legal("a cab", {"text": "taxi", "aliases": ["cab"]})
    assert legal("children", {"text": "child"})  # general morphology remains unsupported
    assert not legal("children", {"text": "child", "aliases": ["children"]})
    for path in (ROOT / "fixtures/w3").glob("*-*.json"):
        manifest(path.read_bytes())


def test_retained_w3_reports_bind_inputs_sources_and_supplemental_evidence():
    evidence = ROOT / "docs/evidence/w3"
    binding = json.loads((evidence / "binding.json").read_bytes())
    plan_path = ROOT / "fixtures/w3/plan.json"
    plan = json.loads(plan_path.read_bytes())
    freeze = json.loads((evidence / "freeze.json").read_bytes())

    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    assert sha(plan_path) == binding["plan_sha256"] == freeze["plan_sha256"]
    assert (
        plan["protocol_hash"]
        == hashlib.sha256(canonical(load("verification-policy.json"))).hexdigest()
    )
    assert plan["fixture_sha256"] == sha(ROOT / "fixtures/semantic/fixture.json")
    assert plan["fingerprint_hash"] == load("model-lock.json")["fingerprint_sha256"]
    assert datetime.fromisoformat(plan["created_at"]) < datetime.fromisoformat(freeze["created_at"])
    assert datetime.fromisoformat(freeze["created_at"]) < datetime.fromisoformat(
        binding["completed_at"]
    )
    for name, digest in plan["inputs"].items():
        assert sha(ROOT / "fixtures/w3" / name) == digest
    for name, digest in binding["sources"].items():
        assert sha(ROOT / "experiments/w3" / name) == digest
    for name, digest in (binding["reports"] | binding["supplemental_reports"]).items():
        assert sha(evidence / name) == digest
    for name, digest in freeze["calibration_reports"].items():
        assert sha(evidence / name) == digest
    for name in binding["reports"]:
        report = json.loads((evidence / name).read_bytes())
        value = manifest((ROOT / "fixtures/w3" / name).read_bytes())
        assert report["semantic_hash"] == projected_hash(value)
        assert report["vector_hash"] == projected_hash(value, vectors=True)
        assert report["manifest_digest"] == plan["inputs"][name]
        assert report["protocol_hash"] == plan["protocol_hash"]
        assert report["fingerprint"] == load("model-lock.json")["fingerprint"]
        assert report["status"] == "measured"
    assert sha(evidence / "freeze.json") == binding["freeze_sha256"]
    latency = json.loads((evidence / "latency.json").read_bytes())
    assert latency["target_passed"] is False
    for summary in latency["concurrency"].values():
        assert summary["requests"] == 100
        assert summary["components"]["/api/embed"]["count"] == 100
