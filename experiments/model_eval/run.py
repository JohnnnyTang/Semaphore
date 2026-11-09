"""Offline-first CPU comparison, deliberately separate from the production ranker."""

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = Path(__file__).with_name("candidates.json")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def validate(fixture):
    entries = {e["id"]: e for e in fixture["entries"]}
    assert len(entries) == len(fixture["entries"]) >= 150
    assert len({c["id"] for c in fixture["cases"]}) == len(fixture["cases"])
    held = set()
    legal_per_target = defaultdict(set)
    for case in fixture["cases"]:
        target = entries[case["target_id"]]
        assert case["split"] == target["split"]
        assert case["category"] == target["category"]
        candidates = case["candidate_ids"]
        assert len(candidates) == len(set(candidates)) == 20
        assert set(candidates) <= entries.keys() and target["id"] in candidates
        assert set(case["hard_decoy_ids"]) <= set(candidates)
        assert target["id"] not in case["hard_decoy_ids"]
        assert len(case["clue"]) <= 120
        if case["expected_legal"]:
            # Lexical fixture hygiene only; W3 owns inflection/alias legality.
            assert target["label"].casefold() not in case["clue"].casefold(), case["id"]
            legal_per_target[target["id"]].add(case["clue"])
            if case["split"] == "held_out":
                held.add(target["id"])
        else:
            assert case["clue"] == target["label"]
    assert len(held) >= 60
    assert all(len(legal_per_target[e]) >= 3 for e in entries)
    return {
        "entries": len(entries),
        "held_out_targets": len(held),
        "legal_clues": sum(map(len, legal_per_target.values())),
        "illegal_clues": sum(not c["expected_legal"] for c in fixture["cases"]),
    }


def rank(target, ids, scores):
    if len(ids) != len(set(ids)) or len(scores) != len(ids):
        raise ValueError("scores require unique candidate IDs")
    if not all(math.isfinite(float(v)) for v in scores):
        raise ValueError("nonfinite score")
    ordered = sorted(zip(ids, scores, strict=True), key=lambda pair: (-float(pair[1]), pair[0]))
    return [entry_id for entry_id, _ in ordered].index(target) + 1, ordered


def summarize(ranks):
    return {
        "count": len(ranks),
        "top3_rate": sum(r <= 3 for r in ranks) / len(ranks),
        "median_rank": statistics.median(ranks),
        "mean_rank": statistics.mean(ranks),
    }


def percentile(values, fraction):
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)]


def model_directory(cache, name, config):
    return cache / (name + "-" + config["revision"])


def fetch(args, config):
    from huggingface_hub import snapshot_download

    destination = model_directory(args.cache, args.model, config)
    snapshot_download(
        config["repository"],
        revision=config["revision"],
        local_dir=destination,
        allow_patterns=["*.json", "*.txt", "*.safetensors", "*.model"],
        ignore_patterns=["onnx/*", "openvino/*", "coreml/*"],
    )
    print(destination)


def evaluate(args, config, fixture):
    # Local assets only. No remote Python or pickle checkpoint loading.
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    import numpy as np
    import psutil
    import torch
    from sentence_transformers import SentenceTransformer

    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    torch.manual_seed(0)
    directory = model_directory(args.cache, args.model, config)
    if not directory.is_dir():
        raise FileNotFoundError(f"Fetch the pinned assets first: {directory}")
    start = time.perf_counter()
    model = SentenceTransformer(
        str(directory),
        device="cpu",
        trust_remote_code=False,
        local_files_only=True,
        model_kwargs={"use_safetensors": True},
    )
    model.float()
    model.max_seq_length = config["max_tokens"]
    model.eval()
    load_seconds = time.perf_counter() - start

    def encode(texts, prefix):
        values = model.encode(
            [prefix + t for t in texts],
            batch_size=16,
            convert_to_tensor=True,
            normalize_embeddings=False,
            show_progress_bar=False,
        )
        if config["postprocess"] == "layernorm-l2":
            values = torch.nn.functional.layer_norm(values, (values.shape[1],))
        return torch.nn.functional.normalize(values, p=2, dim=1).cpu().numpy()

    entries = fixture["entries"]
    lookup = {e["id"]: i for i, e in enumerate(entries)}
    cases = [c for c in fixture["cases"] if c["expected_legal"] and c["split"] == args.split]
    clues = [c["clue"] for c in cases]
    encode(["warm up"], config["query_prefix"])
    timings = []
    for clue in (clues * (args.repeats // len(clues) + 1))[: args.repeats]:
        start = time.perf_counter()
        encode([clue], config["query_prefix"])
        timings.append((time.perf_counter() - start) * 1000)
    start = time.perf_counter()
    queries = encode(clues, config["query_prefix"])
    throughput_seconds = time.perf_counter() - start
    generic = encode(["thing"], config["query_prefix"])[0]
    metrics, details, neighbors, pack_metrics = {}, [], {}, {}
    for text_mode in ("label", "embed_text"):
        vectors = encode([e[text_mode] for e in entries], config["entry_prefix"])
        similarities = queries @ vectors.T
        groups = defaultdict(list)
        pack_ranks = defaultdict(list)
        for ci, case in enumerate(cases):
            for size in (6, 12, 20):
                ids = case["candidate_ids"][:size]
                scores = [similarities[ci, lookup[i]] for i in ids]
                position, ordered = rank(case["target_id"], ids, scores)
                groups[f"{size}/all"].append(position)
                groups[f"{size}/{case['category']}"].append(position)
                details.append(
                    {
                        "case_id": case["id"],
                        "text_mode": text_mode,
                        "stack_size": size,
                        "rank": position,
                        "top3": [i for i, _ in ordered[:3]],
                        "target_score": float(similarities[ci, lookup[case["target_id"]]]),
                    }
                )
            # Five deterministic 19-decoy samples; same-category hard decoys are
            # retained. Median over samples, then over authored clues per entry.
            for pack in fixture["packs"]:
                if case["target_id"] not in pack["entry_ids"]:
                    continue
                target = case["target_id"]
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
                    query = generic if pack["id"] == "weak-generic" else queries[ci]
                    scores = [float(query @ vectors[lookup[i]]) for i in ids]
                    samples.append(rank(target, ids, scores)[0])
                pack_ranks[(pack["id"], target)].append(statistics.median(samples))
        metrics[text_mode] = {key: summarize(values) for key, values in groups.items()}
        for pack in fixture["packs"]:
            values = [
                statistics.median(ranks)
                for (pid, _), ranks in pack_ranks.items()
                if pid == pack["id"]
            ]
            pack_metrics[f"{text_mode}/{pack['id']}"] = summarize(values)
        pairwise = vectors @ vectors.T
        pairs = [
            (float(pairwise[i, j]), entries[i]["id"], entries[j]["id"])
            for i in range(len(entries))
            for j in range(i + 1, len(entries))
        ]
        neighbors[text_mode] = sorted(pairs, reverse=True)[:30]
        assert np.isfinite(vectors).all()
    process = psutil.Process()
    memory = process.memory_info()
    return {
        "format_version": "semantic-measurement-v1",
        "status": "measured",
        "model": args.model,
        "fingerprint": config,
        "split": args.split,
        "fixture_sha256": hashlib.sha256(args.fixture.read_bytes()).hexdigest(),
        "command": sys.argv,
        "environment": {
            "os": platform.platform(),
            "python": sys.version,
            "cpu": platform.processor(),
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(),
            "ram_bytes": psutil.virtual_memory().total,
            "threads": args.threads,
            "interop_threads": 1,
            "device": "cpu",
            "dtype": "float32",
            "dimension": int(queries.shape[1]),
            "packages": {
                p: importlib.metadata.version(p)
                for p in ("torch", "transformers", "sentence-transformers", "numpy", "psutil")
            },
        },
        "performance": {
            "cached_process_cold_load_seconds": load_seconds,
            "warm_single_clue_ms": {
                "n": len(timings),
                "p50": statistics.median(timings),
                "p95": percentile(timings, 0.95),
            },
            "clue_batch_size": 16,
            "clue_embedding_count": len(clues),
            "clue_embedding_seconds": throughput_seconds,
            "clue_embeddings_per_second": len(clues) / throughput_seconds,
            "rss_bytes_after": memory.rss,
            "peak_working_set_bytes": getattr(memory, "peak_wset", None),
            "asset_bytes": sum(
                p.stat().st_size
                for p in directory.rglob("*")
                if p.is_file() and ".cache" not in p.parts
            ),
        },
        "metrics": metrics,
        "pack_metrics": pack_metrics,
        "near_neighbors": neighbors,
        "cases": details,
        "limitations": [
            "synthetic author clues; no human playtest",
            "single process CPU only",
            "no LAN, concurrency, queue, or 5000-entry throughput acceptance",
            "cached model load is not uncached disk or download latency",
            "fixed authored same-category decoys are not mined hard negatives",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("validate", "fetch", "run"))
    parser.add_argument("--model", choices=("bge", "gte", "nomic"), default="bge")
    parser.add_argument("--fixture", type=Path, default=ROOT / "fixtures/semantic/fixture.json")
    parser.add_argument("--cache", type=Path, default=ROOT / "model-cache")
    parser.add_argument("--split", choices=("calibration", "held_out"), default="calibration")
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--repeats", type=int, default=100)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.threads < 1 or args.repeats < 1:
        parser.error("threads and repeats must be positive")
    fixture = read_json(args.fixture)
    summary = validate(fixture)
    config = read_json(CONFIG)["models"][args.model]
    if args.action == "validate":
        print(json.dumps(summary))
    elif args.action == "fetch":
        fetch(args, config)
    else:
        if not args.output:
            parser.error("run requires --output; measurement records must be preserved")
        result = evaluate(args, config, fixture)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(
            json.dumps(
                {
                    "output": str(args.output),
                    "metrics": result["metrics"],
                    "performance": result["performance"],
                }
            )
        )


if __name__ == "__main__":
    main()
