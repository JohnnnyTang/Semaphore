"""Build the authored, model-independent semantic fixture; never tune on held-out data."""

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "fixtures/semantic"


def build():
    with (DEST / "authored.tsv").open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="|"))
    entries, cases = [], []
    counts = Counter()
    for row in rows:
        category = row["category"]
        index = counts[category]
        counts[category] += 1
        entry_id = f"{category}-{index:02}"
        entries.append(
            {
                "id": entry_id,
                "label": row["label"],
                "embed_text": row["context"],
                "category": category,
                "split": "held_out" if index % 5 < 2 else "calibration",
                "forbidden_clues": [row["label"]],
                "provenance": "authored-synthetic-v1",
            }
        )
        for n in range(1, 4):
            cases.append(
                {
                    "id": f"{entry_id}-c{n}",
                    "target_id": entry_id,
                    "clue": row[f"clue{n}"],
                    "expected_legal": True,
                }
            )
        cases.append(
            {
                "id": f"{entry_id}-illegal",
                "target_id": entry_id,
                "clue": row["label"],
                "expected_legal": False,
            }
        )
    for case in cases:
        target = next(e for e in entries if e["id"] == case["target_id"])
        same = [
            e["id"]
            for e in entries
            if e["category"] == target["category"] and e["id"] != target["id"]
        ]
        hard = sorted(same, key=lambda s: hashlib.sha256((target["id"] + s).encode()).hexdigest())[
            :2
        ]
        rest = [e["id"] for e in entries if e["id"] not in [target["id"], *hard]]
        rest.sort(key=lambda s: hashlib.sha256((case["id"] + s).encode()).hexdigest())
        case.update(
            split=target["split"],
            category=target["category"],
            hard_decoy_ids=hard,
            candidate_ids=[target["id"], *hard, *rest[:17]],
            provenance="authored-synthetic-v1",
        )
    fixture = {
        "format_version": "semantic-fixture-v1",
        "seed": "semaphore-w2-2026-11-08",
        "provenance": {
            "kind": "agent-authored synthetic",
            "license": "MIT",
            "human_reviewed": False,
            "third_party_rows": 0,
        },
        "entries": entries,
        "cases": cases,
        "packs": [
            {
                "id": "general-intended-good",
                "entry_ids": [
                    e["id"]
                    for e in entries
                    if e["category"] in ("concrete", "geography", "multiword")
                ],
                "clue_policy": "authored",
                "expected": "hypothesis: higher reachability",
            },
            {
                "id": "biology-difficult",
                "entry_ids": [e["id"] for e in entries if e["category"] == "biology"],
                "clue_policy": "authored",
                "expected": "hypothesis: specialized knowledge required",
            },
            {
                "id": "weak-generic",
                "entry_ids": [e["id"] for e in entries],
                "clue_policy": "the same clue for every target: thing",
                "expected": "hypothesis: low reachability; not a valid publication pack",
            },
        ],
    }
    output = json.dumps(fixture, ensure_ascii=False, indent=2) + "\n"
    (DEST / "fixture.json").write_text(output, encoding="utf-8", newline="\n")
    digest = hashlib.sha256(output.encode()).hexdigest()
    (DEST / "fixture.sha256").write_text(digest + "\n", encoding="ascii")
    print(
        json.dumps(
            {"entries": len(entries), "cases": len(cases), "categories": counts, "sha256": digest}
        )
    )


if __name__ == "__main__":
    build()
