"""Build and audit an authored pilot; no model or network calls."""

import argparse
import collections
import csv
import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path

from semaphore_core.verification import check_clue, parse_manifest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "fixtures/content-pilot"


def build():
    with (SOURCE / "authored.psv").open(encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream, delimiter="|"))
    entries, clues = [], {}
    for n, row in enumerate(rows, 1):
        ident = f"pilot-{n:02d}"
        entries.append(dict(id=ident, text=row["label"], embed_text=row["context"]))
        clues[ident] = [row[f"clue{i}"] for i in range(1, 4)]
    manifest = dict(
        spec_version="1-experiment-w3",
        pack=dict(
            id="everyday-authoring-pilot",
            name="Everyday authoring pilot",
            version="0.1.0",
            author="Semaphore agent-authored pilot",
            description="Unreviewed feasibility sample",
            tags=["pilot", "everyday"],
            language="en",
            license="MIT",
        ),
        entries=entries,
        test_set=clues,
        provenance=dict(agent="Codex; original authoring; no imported dataset rows"),
    )
    raw = (json.dumps(manifest, indent=2) + "\n").encode()
    parse_manifest(raw)
    return rows, raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    start = time.perf_counter()
    rows, raw = build()
    rejected = json.loads((SOURCE / "rejections.json").read_text(encoding="utf-8-sig"))
    manifest = json.loads(raw)
    counts = collections.Counter(r["reason"] for r in rejected)
    remaining = len(rows) + len(rejected)
    stages = []
    for reason in (
        "normalized_duplicate",
        "duplicate_sense",
        "proper_name",
        "abstract",
        "unresolved_sense",
        "specialist",
    ):
        remaining -= counts[reason]
        stages.append(dict(filter=reason, rejected=counts[reason], remaining=remaining))
    report = dict(
        measured_utc=datetime.now(UTC).isoformat(),
        selection="purposive authored sample with deliberate rejection controls; not random",
        candidates=len(rows) + len(rejected),
        accepted_for_automated_check=len(rows),
        filter_ledger=stages,
        categories=dict(collections.Counter(r["category"] for r in rows)),
        legal_clues=sum(map(len, manifest["test_set"].values())),
        exact_label_controls_rejected=sum(
            not check_clue(e["text"], e).legal for e in manifest["entries"]
        ),
        manifest_sha256=hashlib.sha256(raw).hexdigest(),
        source_sha256={
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(SOURCE.iterdir())
            if p.is_file()
        },
        build_validation_seconds=time.perf_counter() - start,
        human_review_seconds=None,
        human_reviewers=0,
        semantic_quality="not measured by this command",
        production_yield_established=False,
    )
    (args.output_dir / "manifest.json").write_bytes(raw)
    (args.output_dir / "audit.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
