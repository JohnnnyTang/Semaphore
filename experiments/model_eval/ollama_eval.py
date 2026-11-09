"""Validate fixtures offline, or explicitly probe/evaluate the selected LAN model.

Run from the repository root with python -m experiments.model_eval.ollama_eval.
The local CPU runner remains a separate historical experiment.
"""

import argparse
import hashlib
import json
import platform
import statistics
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from operator import mul
from pathlib import Path

from experiments.model_eval.run import ROOT, percentile, rank, read_json, summarize, validate

from semaphore_core.embeddings import (
    DIMENSIONS,
    MODEL,
    EmbeddingError,
    EmbeddingResponseError,
    OllamaConfig,
    OllamaEmbedder,
    fingerprint_hash,
)

FORMAT = "ollama-semantic-measurement-v1"


def dot(left, right):
    if len(left) != len(right):
        raise ValueError("vector dimensions differ")
    return sum(map(mul, left, right))


def score_vectors(fixture, cases, queries, entries, vectors, generic):
    """Same authored candidates and pack sampling as the historical CPU experiment."""
    lookup = {entry["id"]: index for index, entry in enumerate(entries)}
    groups, pack_ranks = defaultdict(list), defaultdict(list)
    details = []
    generic_scores = [dot(generic, vector) for vector in vectors]
    for case, query in zip(cases, queries, strict=True):
        similarities = [dot(query, vector) for vector in vectors]
        for size in (6, 12, 20):
            ids = case["candidate_ids"][:size]
            position, ordered = rank(case["target_id"], ids, [similarities[lookup[i]] for i in ids])
            groups[f"{size}/all"].append(position)
            groups[f"{size}/{case['category']}"].append(position)
            details.append(
                {
                    "case_id": case["id"],
                    "stack_size": size,
                    "rank": position,
                    "top3": [i for i, _ in ordered[:3]],
                    "target_score": similarities[lookup[case["target_id"]]],
                }
            )
        for pack in fixture["packs"]:
            target = case["target_id"]
            if target not in pack["entry_ids"]:
                continue
            pool = [i for i in pack["entry_ids"] if i != target]
            samples = []
            for sample in range(5):
                hard = [i for i in case["hard_decoy_ids"] if i in pool]
                rest = [i for i in pool if i not in hard]
                rest.sort(
                    key=lambda i: hashlib.sha256(
                        f"{fixture['seed']}:{target}:{sample}:{i}".encode()
                    ).hexdigest()
                )
                ids = [target, *hard, *rest[: 19 - len(hard)]]
                scores = generic_scores if pack["id"] == "weak-generic" else similarities
                samples.append(rank(target, ids, [scores[lookup[i]] for i in ids])[0])
            pack_ranks[(pack["id"], target)].append(statistics.median(samples))
    packs = {}
    for pack in fixture["packs"]:
        values = [
            statistics.median(ranks) for (pid, _), ranks in pack_ranks.items() if pid == pack["id"]
        ]
        if values:
            packs[pack["id"]] = summarize(values)
    pairs = [
        (dot(vectors[i], vectors[j]), entries[i]["id"], entries[j]["id"])
        for i in range(len(entries))
        for j in range(i + 1, len(entries))
    ]
    return {
        "metrics": {key: summarize(values) for key, values in groups.items()},
        "pack_metrics": packs,
        "near_neighbors": sorted(pairs, reverse=True)[:30],
        "cases": details,
    }


def latency_summary(values):
    return {"n": len(values), "p50": statistics.median(values), "p95": percentile(values, 0.95)}


def check_calibration(report, identity, fixture_sha256):
    if (
        not isinstance(report, dict)
        or report.get("format_version") != FORMAT
        or report.get("status") != "measured"
        or report.get("split") != "calibration"
        or report.get("fingerprint") != identity
        or report.get("fingerprint_sha256") != fingerprint_hash(identity)
        or report.get("fixture_sha256") != fixture_sha256
    ):
        raise ValueError("held-out run requires a matching calibration report and encoding policy")


def loaded_snapshot(client, identity):
    running = client.running_model()
    if running.get("digest") != identity["digest"]:
        raise EmbeddingResponseError("loaded model digest differs from installed model identity")
    return running


def smoke_check(client):
    before = client.identity()
    started = time.perf_counter()
    queries = client.embed_queries(["sailing across the sea"])
    entries = client.embed_entries(["ocean", "violin"])
    elapsed = time.perf_counter() - started
    running = loaded_snapshot(client, before)
    if client.identity() != before:
        raise EmbeddingResponseError("model identity changed during smoke check")
    return {
        "status": "connected",
        "fingerprint": before,
        "fingerprint_sha256": fingerprint_hash(before),
        "dimensions": len(queries[0]),
        "smoke_seconds": elapsed,
        "sample_cosines": [dot(queries[0], entry) for entry in entries],
        "running_model": running,
        "limitations": ["sample scores are diagnostics, not a semantic-quality pass"],
    }


def evaluate(client, fixture, split, repeats, concurrency, fixture_sha256, calibration=None):
    before = client.identity()
    if split == "held_out":
        check_calibration(calibration or {}, before, fixture_sha256)
    cases = [c for c in fixture["cases"] if c["expected_legal"] and c["split"] == split]
    clues = [c["clue"] for c in cases]
    if not clues:
        raise ValueError("no legal clues in selected split")
    started = time.perf_counter()
    client.embed_queries(["warm up"])
    first_request_seconds = time.perf_counter() - started

    def timed_query(clue):
        start = time.perf_counter()
        client.embed_queries([clue])
        return (time.perf_counter() - start) * 1000

    serial = [timed_query(clues[i % len(clues)]) for i in range(repeats)]
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        concurrent = list(pool.map(timed_query, [clues[i % len(clues)] for i in range(repeats)]))
    concurrent_seconds = time.perf_counter() - started
    started = time.perf_counter()
    queries = client.embed_queries(clues)
    batch_seconds = time.perf_counter() - started
    generic = client.embed_queries(["thing"])[0]
    modes = {}
    for mode in ("label", "embed_text"):
        entries = fixture["entries"]
        vectors = client.embed_entries([e[mode] for e in entries])
        modes[mode] = score_vectors(fixture, cases, queries, entries, vectors, generic)
    running = loaded_snapshot(client, before)
    if client.identity() != before:
        raise EmbeddingResponseError("model identity changed during evaluation; discard this run")
    return {
        "format_version": FORMAT,
        "status": "measured",
        "created_at": datetime.now(UTC).isoformat(),
        "model": MODEL,
        "split": split,
        "fixture_sha256": fixture_sha256,
        "fingerprint": before,
        "fingerprint_sha256": fingerprint_hash(before),
        "client_environment": {"os": platform.platform(), "python": sys.version},
        "running_model": running,
        "performance": {
            "first_request_seconds": first_request_seconds,
            "warm_serial_request_ms": latency_summary(serial),
            "concurrent_request_ms": latency_summary(concurrent),
            "concurrency": concurrency,
            "concurrent_wall_seconds": concurrent_seconds,
            "batch_size": client.config.batch_size,
            "timeout_seconds": client.config.timeout_seconds,
            "digest_pin_checked_per_operation": client.config.expected_digest is not None,
            "clue_embedding_count": len(clues),
            "clue_embedding_seconds": batch_seconds,
            "clue_embeddings_per_second": len(clues) / batch_seconds,
        },
        "text_modes": modes,
        "limitations": [
            "synthetic authored clues; no independent human playtest",
            "HTTP timings include network and service queue time; not game round trips",
            "first request can use an already loaded model; not a cold-load measurement",
            "concurrency probe excludes uploads and full gameplay",
            "GPU model, driver and host hardware must be recorded separately by the operator",
            "inventory cannot detect a tag changed and restored mid-run; freeze the server",
            "experiment fingerprint is not the draft publication verification contract",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("validate", "check", "run"))
    parser.add_argument("--fixture", type=Path, default=ROOT / "fixtures/semantic/fixture.json")
    parser.add_argument("--split", choices=("calibration", "held_out"), default="calibration")
    parser.add_argument("--repeats", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--calibration-report", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.repeats < 1 or not 1 <= args.concurrency <= 8:
        parser.error("repeats must be positive and concurrency must be between 1 and 8")
    if args.action == "run" and args.output is None:
        parser.error("run requires --output to preserve measurement evidence")
    if args.output and args.output.exists():
        parser.error("output already exists; choose a new path to preserve prior evidence")
    if args.action == "run" and args.split == "held_out" and not args.calibration_report:
        parser.error("held_out requires --calibration-report; freeze policy after calibration")
    try:
        fixture = read_json(args.fixture)
        summary = validate(fixture)
        fixture_sha = hashlib.sha256(args.fixture.read_bytes()).hexdigest()
        if args.action == "validate":
            result = {
                "status": "offline-validated",
                "model": MODEL,
                "dimensions": DIMENSIONS,
                "fixture_sha256": fixture_sha,
                "fixture": summary,
                "model_contacted": False,
            }
        else:
            calibration = read_json(args.calibration_report) if args.calibration_report else None
            client = OllamaEmbedder(OllamaConfig.from_env())
            if args.action == "check":
                result = smoke_check(client)
            else:
                result = evaluate(
                    client,
                    fixture,
                    args.split,
                    args.repeats,
                    args.concurrency,
                    fixture_sha,
                    calibration,
                )
                if args.calibration_report:
                    result["calibration_report_sha256"] = hashlib.sha256(
                        args.calibration_report.read_bytes()
                    ).hexdigest()
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8") as output:
                output.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
            print(json.dumps({"output": str(args.output), "status": result["status"]}))
        else:
            print(json.dumps(result, indent=2, allow_nan=False))
    except (EmbeddingError, ValueError, OSError, AssertionError) as exc:
        parser.exit(1, f"Ollama experiment failed: {exc}\n")


if __name__ == "__main__":
    main()
