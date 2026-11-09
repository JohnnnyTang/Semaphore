"""Offline contract examples; reference probes, not the future verifier engine."""

import copy
import hashlib
import json
import math
import unicodedata
from pathlib import Path

import pytest
from fixtures.manifests.check_examples import canonical, normalize, parse, projected_hash
from fixtures.manifests.check_examples import semantic_error as draft_semantic_error
from jsonschema import Draft202012Validator

from semaphore_core.embeddings import fingerprint_hash

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "contracts"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def validator(name):
    schema = load(CONTRACTS / name)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def manifest():
    value = load(ROOT / "fixtures/manifests/valid-structural.json")
    value["spec_version"] = "1-experiment-w3"
    return value


def report():
    lock = load(CONTRACTS / "model-lock.json")
    return {
        "report_version": "experiment-w3",
        "authority": "experiment-recomputed",
        **dict.fromkeys(
            ["manifest_digest", "semantic_hash", "vector_hash", "protocol_hash"], "0" * 64
        ),
        "fingerprint_hash": lock["fingerprint_sha256"],
        "fingerprint": lock["fingerprint"],
        "metrics_version": "bottom3-median-v1",
        "ruleset_id": "synthetic-ruleset",
        "status": "measured",
        "metrics": {
            "entry_count": 40,
            "legal_clue_count": 120,
            "reachable_entries": 0,
            "reachability": 0,
            "playability": 0,
            "mean_rank": 20,
            "duplicate_entry_count": 0,
        },
        "sample_count": 5,
        "numeric_tolerance": 0.00001,
        "flagged_entries": [],
        "flagged_pairs": [],
        "diagnostics_truncated": False,
        "elapsed_ms": 0,
    }


def tokens(text):
    text = normalize(text).casefold()
    separated = "".join(c if unicodedata.category(c)[0] in "LN" else " " for c in text)
    mapping = dict.fromkeys(["car", "cars"], "car")
    mapping.update(dict.fromkeys(["run", "runs", "running", "ran"], "run"))
    return [mapping.get(t, t) for t in separated.split()]


def legal(clue, target):
    clue_tokens = tokens(clue)
    if not clue_tokens:
        return False
    for text in [target["text"], *target.get("aliases", []), *target.get("forbidden_clues", [])]:
        phrase = tokens(text)
        if not phrase:
            raise ValueError("empty lexical phrase")
        if any(clue_tokens[i : i + len(phrase)] == phrase for i in range(len(clue_tokens))):
            return False
    return True


def test_manifest_structure_and_legacy_semantic_fixtures():
    check = validator("manifest.schema.json")
    check.validate(manifest())
    cases = load(ROOT / "fixtures/manifests/cases.json")["cases"]
    for case in cases:
        value = parse((ROOT / "fixtures/manifests" / case["file"]).read_bytes())
        value["spec_version"] = "1-experiment-w3"
        actual = (
            "schema_invalid"
            if list(check.iter_errors(value))
            else (draft_semantic_error(value) or "ok")
        )
        assert actual == case["expected"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("vectors", []),
        ("spec_version", "1-draft-w2"),
        ("injected", True),
    ],
)
def test_manifest_rejects_unknown_or_wrong_version(field, value):
    data = manifest()
    data[field] = value
    assert list(validator("manifest.schema.json").iter_errors(data))


def test_reports_pin_experiment_identity_without_production_claim():
    check = validator("verification.schema.json")
    data = report()
    check.validate(data)
    assert fingerprint_hash(data["fingerprint"]) == data["fingerprint_hash"]
    for path, value in [
        (("status",), "passed"),
        (("authority",), "hub-recomputed"),
        (("fingerprint", "digest"), "0" * 64),
        (("fingerprint", "dimensions"), 1024),
        (("fingerprint", "ollama_version"), "unmeasured"),
        (("fingerprint", "model_details", "quantization_level"), "Q8_0"),
        (("sample_count",), 1),
    ]:
        changed = copy.deepcopy(data)
        obj = changed
        for part in path[:-1]:
            obj = obj[part]
        obj[path[-1]] = value
        assert list(check.iter_errors(changed)), path
    hf = load(CONTRACTS / "verification.schema.json")["$defs"]["hfProductionFingerprint"]
    assert {"revision", "assets", "pooling", "dtype", "runtime"} <= set(hf["required"])
    assert list(Draft202012Validator(hf).iter_errors(data["fingerprint"]))


def test_hash_projection_isolation_and_fixed_w2_vectors():
    data = manifest()
    hashes = load(ROOT / "fixtures/manifests/hash-vectors.json")
    assert projected_hash(data) == hashes["semantic_hash"]
    assert projected_hash(data, vectors=True) == hashes["vector_hash"]
    changed = copy.deepcopy(data)
    changed["test_report"] = {"reachability": 1, "mean_rank": 1, "flagged": []}
    changed["pack"]["name"] = "changed"
    assert projected_hash(changed) == projected_hash(data)
    changed["test_set"]["apple"][0] = "different legal clue"
    assert projected_hash(changed) != projected_hash(data)
    assert projected_hash(changed, vectors=True) == projected_hash(data, vectors=True)
    changed["entries"].reverse()
    assert projected_hash(changed, vectors=True) != projected_hash(data, vectors=True)


@pytest.mark.parametrize(
    "clue,target,expected",
    [
        ("cars", {"text": "car"}, False),
        ("carpet", {"text": "car"}, True),
        ("she ran", {"text": "run"}, False),
        ("running", {"text": "run"}, False),
        ("NEW—YORK", {"text": "New York"}, False),
        ("a cab", {"text": "taxi", "aliases": ["cab"]}, False),
        ("fruit", {"text": "apple", "forbidden_clues": ["fruit"]}, False),
        ("!!!", {"text": "car"}, False),
        ("children", {"text": "child"}, True),  # explicitly unsupported morphology
    ],
)
def test_reviewed_legality_subset(clue, target, expected):
    assert legal(clue, target) is expected


def test_total_order_and_deterministic_sampling_reference():
    scores = {"c": 0.200004, "b": 0.2, "a": 0.200003, "d": -0.1}
    ordered = sorted(scores, key=lambda i: (-math.floor(scores[i] / 0.00001 + 0.5), i))
    assert ordered == ["a", "b", "c", "d"]
    # Close raw values can cross bucket boundaries; parity tolerance is not sorting.
    assert math.floor(0.2000049 / 0.00001 + 0.5) != math.floor(0.2000051 / 0.00001 + 0.5)
    ids = [f"word-{i:02}" for i in range(40)]
    target, hard = ids[0], ids[1:6]

    def sample(pool, index):
        rest = [i for i in pool if i != target and i not in hard]
        rest.sort(
            key=lambda i: (
                hashlib.sha256(canonical(["decoy-v1", "0" * 64, target, index, i])).hexdigest(),
                i,
            )
        )
        return hard + rest[:14]

    samples = [sample(ids, i) for i in range(5)]
    assert samples == [sample(list(reversed(ids)), i) for i in range(5)]
    assert all(len(s) == len(set(s)) == 19 and target not in s for s in samples)
    assert len({tuple(s) for s in samples}) == 5


def test_machine_readable_policy_hash_ignores_line_endings():
    policy = load(CONTRACTS / "verification-policy.json")
    encoded = canonical(policy)
    assert hashlib.sha256(encoded).hexdigest() == (
        "910038622a203fbd9ed010d7d0d7169d35ea3a79d76e879a38e8d77de4d97132"
    )
    alternate = json.dumps(policy, indent=4).replace("\n", "\r\n")
    assert canonical(json.loads(alternate)) == encoded


@pytest.mark.parametrize(
    "raw",
    [
        b'{"x":1,"x":2}',
        b'{"x":NaN}',
        b'{"x":1e400}',
        b"\xef\xbb\xbf{}",
        b'{"x":"\\ud800"}',
        b'{"x":' + b"[" * 17 + b"0" + b"]" * 17 + b"}",
    ],
)
def test_strict_parser_rejects_ambiguous_or_unbounded_json(raw):
    with pytest.raises(ValueError, match="invalid_json"):
        parse(raw)
