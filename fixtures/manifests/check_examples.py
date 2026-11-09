"""Offline draft checks, not a production parser, verifier or publication service."""

import copy
import hashlib
import json
import unicodedata
from math import isfinite
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

HERE = Path(__file__).resolve().parent
SCHEMAS = HERE.parents[1] / "docs" / "contracts-drafts"
MAX_BYTES = 8 * 1024 * 1024


def reject_constant(value: str) -> None:
    raise ValueError(f"invalid JSON constant {value}")


def unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def check_tree(value: object, depth: int = 0) -> None:
    if isinstance(value, float) and not isfinite(value):
        raise ValueError("non-finite number")
    if isinstance(value, str):
        if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
            raise ValueError("unpaired surrogate")
    elif isinstance(value, (list, dict)):
        if depth >= 16:
            raise ValueError("nesting limit")
        if isinstance(value, dict):
            for key in value:
                check_tree(key, depth + 1)
            children = value.values()
        else:
            children = value
        for child in children:
            check_tree(child, depth + 1)


def parse(raw: bytes) -> dict:
    if len(raw) > MAX_BYTES:
        raise ValueError("body_too_large")
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError("invalid_json")
    try:
        value = json.loads(
            raw.decode("utf-8"), object_pairs_hook=unique_object, parse_constant=reject_constant
        )
        check_tree(value)
    except (ValueError, RecursionError) as exc:
        raise ValueError("invalid_json") from exc
    if not isinstance(value, dict):
        raise ValueError("invalid_json")
    return value


def normalize(text: str) -> str:
    value = " ".join(unicodedata.normalize("NFKC", text).split())
    if not value or any(unicodedata.category(char).startswith("C") for char in value):
        raise ValueError("hygiene_invalid")
    return value


def semantic_error(pack: dict) -> str | None:
    """Only cross-field/hygiene checks; shared legality and real embeddings await W3."""
    ids = [entry["id"] for entry in pack["entries"]]
    labels = [normalize(entry["text"]).casefold() for entry in pack["entries"]]
    if len(ids) != len(set(ids)) or len(labels) != len(set(labels)):
        return "duplicate_entry"
    if set(ids) != set(pack["test_set"]):
        return "test_coverage"
    for entry in pack["entries"]:
        for key, maximum in [("text", 64), ("embed_text", 256)]:
            if key in entry and len(normalize(entry[key])) > maximum:
                return "hygiene_invalid"
        for key in ["aliases", "forbidden_clues"]:
            values = [normalize(v).casefold() for v in entry.get(key, [])]
            if len(values) != len(set(values)) or any(len(v) > 64 for v in values):
                return "hygiene_invalid"
    for clues in pack["test_set"].values():
        values = [normalize(clue).casefold() for clue in clues]
        if len(set(values)) != len(values):
            return "duplicate_clue"
        if any(len(normalize(clue)) > 120 for clue in clues):
            return "hygiene_invalid"
    return None


def canonical(value: object) -> bytes:
    def check(item: object) -> None:
        if item is None or isinstance(item, (bool, str)):
            return
        if isinstance(item, int) and abs(item) <= 2**53 - 1:
            return
        if isinstance(item, list):
            for child in item:
                check(child)
            return
        if isinstance(item, dict) and all(isinstance(key, str) for key in item):
            for child in item.values():
                check(child)
            return
        raise ValueError("unsupported canonical value")

    check(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def projected_hash(pack: dict, *, vectors: bool = False) -> str:
    entries = []
    for entry in pack["entries"]:
        item = {"id": entry["id"], "embed_text": normalize(entry.get("embed_text", entry["text"]))}
        if not vectors:
            item.update(
                text=normalize(entry["text"]),
                aliases=sorted(normalize(v) for v in entry.get("aliases", [])),
                forbidden_clues=sorted(normalize(v) for v in entry.get("forbidden_clues", [])),
                tier=entry.get("tier", 1),
            )
        entries.append(item)
    projection = {"canonicalization": "semaphore-c14n-draft-w2", "entries": entries}
    if not vectors:
        projection["test_set"] = {
            key: sorted(normalize(clue) for clue in clues)
            for key, clues in pack["test_set"].items()
        }
    domain = b"semaphore-vectors-draft-w2\0" if vectors else b"semaphore-semantic-draft-w2\0"
    return hashlib.sha256(domain + canonical(projection)).hexdigest()


def publication_decision(owner: str, actor: str, existing: str | None, incoming: str) -> str:
    if owner != actor:
        return "owner_conflict"
    if existing is None:
        return "enqueue"
    return "idempotent" if existing == incoming else "version_conflict"


def state_error(state: dict) -> str | None:
    """Proposed snapshot invariants outside JSON Schema's structural checks."""
    ids = [entry["entry_id"] for entry in state["board"]]
    if len(set(ids)) != len(ids):
        return "duplicate_board_entry"
    if ids and state["target_id"] not in ids:
        return "target_not_on_board"
    if not ids and state["target_id"] is not None:
        return "target_on_empty_board"
    if state["status"] == "running":
        if state["end_reason"] is not None:
            return "running_with_end_reason"
    elif state["end_reason"] is None or state["next_spawn_ms"] is not None:
        return "invalid_terminal_state"
    return None


def main() -> None:
    documents = {
        path.name: json.loads(path.read_text(encoding="utf-8"))
        for path in SCHEMAS.glob("*.schema.json")
    }
    # Only preloaded resources; missing refs fail rather than fetching the network.
    registry = Registry().with_resources(
        (doc["$id"], Resource.from_contents(doc)) for doc in documents.values()
    )
    for doc in documents.values():
        Draft202012Validator.check_schema(doc)
    validator = Draft202012Validator(documents["manifest.schema.json"], registry=registry)
    cases = json.loads((HERE / "cases.json").read_text(encoding="utf-8"))["cases"]
    for case in cases:
        raw = (HERE / case["file"]).read_bytes()
        pack = parse(raw)
        actual = (
            "schema_invalid" if list(validator.iter_errors(pack)) else semantic_error(pack) or "ok"
        )
        assert actual == case["expected"], (case["file"], actual, case["expected"])
    raw = (HERE / "valid-structural.json").read_bytes()
    pack = parse(raw)
    sh, vh = projected_hash(pack), projected_hash(pack, vectors=True)
    vector = json.loads((HERE / "hash-vectors.json").read_text(encoding="utf-8"))
    assert vector == {
        "manifest_digest": hashlib.sha256(raw).hexdigest(),
        "semantic_hash": sh,
        "vector_hash": vh,
    }
    changed = copy.deepcopy(pack)
    changed["test_report"] = {"reachability": 1.0, "mean_rank": 1.0, "flagged": []}
    changed["provenance"]["agent"] = "a different self report"
    changed["pack"]["description"] = "metadata change"
    assert projected_hash(changed) == sh
    assert projected_hash(changed, vectors=True) == vh
    assert hashlib.sha256(json.dumps(changed).encode()).hexdigest() != vector["manifest_digest"]
    assert hashlib.sha256(canonical(pack)).hexdigest() != hashlib.sha256(raw).hexdigest()
    changed = copy.deepcopy(pack)
    changed["test_set"]["apple"][0] = "fruit from a tree"
    assert projected_hash(changed) != sh
    assert projected_hash(changed, vectors=True) == vh
    changed = copy.deepcopy(pack)
    changed["entries"].reverse()
    assert projected_hash(changed) != sh and projected_hash(changed, vectors=True) != vh
    changed = copy.deepcopy(pack)
    changed["entries"][0]["embed_text"] = "apple fruit from an orchard"
    assert projected_hash(changed) != sh and projected_hash(changed, vectors=True) != vh
    changed = copy.deepcopy(pack)
    changed["test_set"]["apple"].reverse()
    assert projected_hash(changed) == sh
    for invalid, expected in [
        (b'{"a":1,"a":2}', "invalid_json"),
        (b'{"a":NaN}', "invalid_json"),
        (b'{"a":1e400}', "invalid_json"),
        (b"\xef\xbb\xbf{}", "invalid_json"),
        (b'{"a":"\\ud800"}', "invalid_json"),
        (b'{"a":' + b"[" * 17 + b"0" + b"]" * 17 + b"}", "invalid_json"),
        (b" " * (MAX_BYTES + 1), "body_too_large"),
    ]:
        try:
            parse(invalid)
        except ValueError as exc:
            assert str(exc) == expected
        else:
            raise AssertionError("invalid parser fixture accepted")
    assert publication_decision("alice", "bob", "a", "a") == "owner_conflict"
    assert publication_decision("alice", "alice", "a", "a") == "idempotent"
    assert publication_decision("alice", "alice", "a", "b") == "version_conflict"
    assert publication_decision("alice", "alice", None, "a") == "enqueue"
    samples = json.loads((HERE / "protocol-examples.json").read_text(encoding="utf-8"))
    for sample in samples:
        doc = documents[sample["schema"]]
        payload_validator = Draft202012Validator(
            {"$ref": doc["$id"] + sample.get("fragment", "")}, registry=registry
        )
        valid = not list(payload_validator.iter_errors(sample["payload"]))
        if valid and sample["schema"] == "events.schema.json" and "state" in sample["payload"]:
            valid = state_error(sample["payload"]["state"]) is None
        assert valid == sample["valid"], sample["name"]
    print(f"PASS: {len(documents)} schemas, {len(cases)} manifests, {len(samples)} protocol cases")
    print("PASS: strict parsing, fixed hashes, hash isolation, owner/version retry decision table")
    print("UNMEASURED: legality/stemming, embeddings, quality, concurrency, HTTP server behavior")


if __name__ == "__main__":
    main()
