import copy
import json
import math
from pathlib import Path

import pytest

from semaphore_core.embeddings import EmbeddingResponseError, PinnedEmbedder
from semaphore_core.verification import (
    CoreValidationError,
    check_clue,
    load,
    manifest_hashes,
    parse_manifest,
    rank_vectors,
    sample_decoys,
    verify_pack,
)

ROOT = Path(__file__).resolve().parents[2]
UNIT = [1.0] + [0.0] * 2559


def test_packaged_policy_matches_frozen_contracts():
    for name in (
        "manifest.schema.json",
        "verification.schema.json",
        "model-lock.json",
        "verification-policy.json",
        "http.schema.json",
        "events.schema.json",
    ):
        assert load(name) == json.loads((ROOT / "contracts" / name).read_text())


@pytest.mark.parametrize(
    "raw,code",
    [
        (b'{"a":1,"a":2}', "invalid_json"),
        (b'{"a":NaN}', "invalid_json"),
        (b'{"a":1e999}', "invalid_json"),
        (b'{"a":"\\ud800"}', "invalid_json"),
        (b"\xef\xbb\xbf{}", "invalid_json"),
        (b" " * 8388609, "body_too_large"),
    ],
)
def test_strict_parser(raw, code):
    with pytest.raises(CoreValidationError) as caught:
        parse_manifest(raw)
    assert caught.value.code == code
    assert caught.value.path == ()


def test_legality_and_unicode_boundaries():
    assert not check_clue("ＣＡＲＳ!", dict(text="car")).legal
    assert check_clue("carpet", dict(text="car")).legal
    assert not check_clue("already ran", dict(text="run")).legal
    assert not check_clue("!!!", dict(text="car")).legal
    assert check_clue("blue\nSky", dict(text="car")).legal
    for clue in ("a\x00b", "a" * 121):
        with pytest.raises(CoreValidationError):
            check_clue(clue, dict(text="car"))


def test_order_validates_and_buckets():
    ranked = rank_vectors(UNIT, [("z", UNIT), ("a", UNIT)])
    assert [r.entry_id for r in ranked] == ["a", "z"]
    assert [r.rank for r in ranked] == [1, 2]
    for row in ([True] + [0.0] * 2559, [math.nan] + [0.0] * 2559, [0.0] * 2560, [1.0]):
        with pytest.raises(CoreValidationError):
            rank_vectors(row, [("a", UNIT)])
    with pytest.raises(CoreValidationError):
        rank_vectors(UNIT, [("a", UNIT), ("a", UNIT)])


class FakeEmbedder:
    def identity(self):
        return copy.deepcopy(load("model-lock.json")["fingerprint"])

    def embed_entries(self, texts):
        return [[0.0] * n + [1.0] + [0.0] * (2559 - n) for n, _ in enumerate(texts)]

    def embed_queries(self, texts):
        return [UNIT[:] for _ in texts]


def test_verification_matches_reference_and_schema():
    from experiments.w3.verification import measure

    raw = (ROOT / "fixtures/w3/calibration-authored.json").read_bytes()
    parsed = parse_manifest(raw)
    actual = verify_pack(parsed, FakeEmbedder(), "experiment-arcade-v1")
    expected = measure(raw, FakeEmbedder())[0]
    actual.pop("elapsed_ms")
    expected.pop("elapsed_ms")
    assert actual == expected
    assert manifest_hashes(parsed).semantic_hash == expected["semantic_hash"]
    candidates = [(e["id"], UNIT) for e in parsed.manifest["entries"]]
    decoys = sample_decoys(expected["semantic_hash"], candidates[0][0], 0, candidates)
    assert len(set(decoys)) == 19 and candidates[0][0] not in decoys
    parsed.manifest["entries"][0]["text"] = "modified"
    with pytest.raises(CoreValidationError):
        verify_pack(parsed, FakeEmbedder(), "experiment-arcade-v1")


def test_pin_rejects_full_runtime_change():
    class Changed(FakeEmbedder):
        def identity(self):
            value = super().identity()
            value["ollama_version"] = "changed"
            return value

    with pytest.raises(EmbeddingResponseError):
        PinnedEmbedder(Changed()).embed_queries(["private clue"])


def test_duplicate_pair_diagnostics_are_json_arrays():
    class Same(FakeEmbedder):
        def embed_entries(self, texts):
            return [UNIT[:] for _ in texts]

    from jsonschema import Draft202012Validator

    raw = (ROOT / "fixtures/w3/calibration-authored.json").read_bytes()
    report = verify_pack(parse_manifest(raw), Same(), "experiment-arcade-v1")
    assert report["flagged_pairs"] and isinstance(report["flagged_pairs"][0], list)
    Draft202012Validator(load("verification.schema.json")).validate(report)
