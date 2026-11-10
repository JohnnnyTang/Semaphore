"""Strict shared parsing, normalization and content-addressed projections."""

import hashlib
import json
import unicodedata
from math import isfinite

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
