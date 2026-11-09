"""Executable W3 protocol reference; not a publication service or W4 core.

Uses the existing strict fixture parser and projections to preserve hash identity.
No uploaded vectors or self-reported metrics are used.
"""

import hashlib
import json
import math
import re
import statistics
import time
import unicodedata
from pathlib import Path

from fixtures.manifests.check_examples import canonical, normalize, parse, projected_hash
from jsonschema import Draft202012Validator

from semaphore_core.embeddings import EmbeddingResponseError, fingerprint_hash

ROOT = Path(__file__).resolve().parents[2]
ID = re.compile(r"[a-z][a-z0-9-]{0,63}\Z")


def load(name):
    return json.loads((ROOT / "contracts" / name).read_text(encoding="utf-8"))


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
            raise ValueError("hygiene_invalid")
        if any(clue_tokens[i : i + len(phrase)] == phrase for i in range(len(clue_tokens))):
            return False
    return True


def manifest(raw):
    value = parse(raw)
    validator = Draft202012Validator(load("manifest.schema.json"))
    if next(validator.iter_errors(value), None) is not None:
        raise ValueError("schema_invalid")
    for entry in value["entries"]:
        for key, limit in [("text", 64), ("embed_text", 256)]:
            if key in entry:
                entry[key] = normalize(entry[key])
                if len(entry[key]) > limit:
                    raise ValueError("hygiene_invalid")
        for key in ["aliases", "forbidden_clues"]:
            entry[key] = [normalize(t) for t in entry.get(key, [])]
            if any(len(t) > 64 or not tokens(t) for t in entry[key]):
                raise ValueError("hygiene_invalid")
            if len({t.casefold() for t in entry[key]}) != len(entry[key]):
                raise ValueError("hygiene_invalid")
        if not tokens(entry["text"]):
            raise ValueError("hygiene_invalid")
    ids = [e["id"] for e in value["entries"]]
    if any(not ID.fullmatch(i) for i in ids):
        raise ValueError("schema_invalid")
    labels = [e["text"].casefold() for e in value["entries"]]
    if len(set(ids)) != len(ids) or len(set(labels)) != len(labels):
        raise ValueError("duplicate_entry")
    if set(ids) != set(value["test_set"]):
        raise ValueError("test_coverage")
    for entry in value["entries"]:
        clues = [normalize(c) for c in value["test_set"][entry["id"]]]
        if any(len(c) > 120 for c in clues):
            raise ValueError("hygiene_invalid")
        if len({c.casefold() for c in clues}) != len(clues):
            raise ValueError("duplicate_clue")
        if not all(legal(c, entry) for c in clues):
            raise ValueError("illegal_clue")
        value["test_set"][entry["id"]] = clues
    return value


def vector(row):
    if len(row) != 2560 or any(type(v) not in (float, int) for v in row):
        raise ValueError("invalid_vector")
    try:
        row = tuple(float(v) for v in row)
        norm = math.sqrt(dot(row, row))
    except (ValueError, OverflowError):
        raise ValueError("invalid_vector") from None
    if not math.isfinite(norm) or abs(norm - 1) > 0.001:
        raise ValueError("invalid_vector")
    return row


def dot(left, right):
    result = 0.0
    for a, b in zip(left, right, strict=True):
        result += a * b
    return result


def order(scores):
    if any(not ID.fullmatch(i) or not math.isfinite(s) for i, s in scores.items()):
        raise ValueError("invalid_scores")
    return sorted(scores, key=lambda i: (-math.floor(scores[i] / 0.00001 + 0.5), i))


def samples(semantic_hash, target, entry_vectors):
    if target not in entry_vectors or len(entry_vectors) < 40:
        raise ValueError("invalid_candidates")
    hard = order(
        {i: dot(entry_vectors[target], v) for i, v in entry_vectors.items() if i != target}
    )[:5]
    rest = set(entry_vectors) - {target, *hard}
    return [
        hard
        + sorted(
            rest,
            key=lambda i: (
                hashlib.sha256(canonical(["decoy-v1", semantic_hash, target, s, i])).digest(),
                i,
            ),
        )[:14]
        for s in range(5)
    ]


def measure(raw, embedder):
    start = time.perf_counter()
    value = manifest(raw)  # fail before any inference
    lock = load("model-lock.json")
    before = embedder.identity()
    if before != lock["fingerprint"] or fingerprint_hash(before) != lock["fingerprint_sha256"]:
        raise EmbeddingResponseError("W3 fingerprint mismatch")
    entries = value["entries"]
    rows = embedder.embed_entries([e.get("embed_text", e["text"]) for e in entries])
    entry_vectors = {e["id"]: vector(v) for e, v in zip(entries, rows, strict=True)}
    clue_keys = [(e["id"], c) for e in entries for c in value["test_set"][e["id"]]]
    rows = embedder.embed_queries([c for _, c in clue_keys])
    semantic_hash = projected_hash(value)
    decoys = {i: samples(semantic_hash, i, entry_vectors) for i in entry_vectors}
    ranks = {i: [] for i in entry_vectors}
    parity_cases = []
    for (target, _), row in zip(clue_keys, rows, strict=True):
        query = vector(row)
        scores = {i: dot(query, v) for i, v in entry_vectors.items()}
        ranks[target].append(
            statistics.median(
                order({i: scores[i] for i in [target, *sample]}).index(target) + 1
                for sample in decoys[target]
            )
        )
        # In-memory numeric parity input, never included in the reviewed report.
        if len(parity_cases) < 10:
            parity_cases.append(
                {"query": query, "entries": entry_vectors, "ordered": order(scores)}
            )
    medians = {i: statistics.median(r) for i, r in ranks.items()}
    flagged = sorted(i for i, r in medians.items() if r > 3)
    ids = sorted(entry_vectors)
    pairs = [
        (a, b)
        for n, a in enumerate(ids)
        for b in ids[n + 1 :]
        if dot(entry_vectors[a], entry_vectors[b]) >= 0.95
    ]
    if embedder.identity() != before:
        raise EmbeddingResponseError("W3 identity changed during verification")
    reachable = len(entries) - len(flagged)
    report = {
        "report_version": "experiment-w3",
        "authority": "experiment-recomputed",
        "manifest_digest": hashlib.sha256(raw).hexdigest(),
        "semantic_hash": semantic_hash,
        "vector_hash": projected_hash(value, vectors=True),
        "fingerprint_hash": fingerprint_hash(before),
        "fingerprint": before,
        "metrics_version": "bottom3-median-v1",
        "protocol_hash": hashlib.sha256(canonical(load("verification-policy.json"))).hexdigest(),
        "ruleset_id": "experiment-arcade-v1",
        "status": "measured",
        "metrics": {
            "entry_count": len(entries),
            "legal_clue_count": len(clue_keys),
            "reachable_entries": reachable,
            "reachability": reachable / len(entries),
            "playability": 100 * reachable / len(entries),
            "mean_rank": statistics.mean(medians.values()),
            "duplicate_entry_count": 0,
        },
        "sample_count": 5,
        "numeric_tolerance": 0.00001,
        "flagged_entries": flagged[:1000],
        "flagged_pairs": pairs[:1000],
        "diagnostics_truncated": len(flagged) > 1000 or len(pairs) > 1000,
        "elapsed_ms": round((time.perf_counter() - start) * 1000),
    }
    Draft202012Validator(load("verification.schema.json")).validate(report)
    return report, parity_cases
