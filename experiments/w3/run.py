"""Bounded W3 closure probes. Run prepare before run; outputs are append-only."""

import argparse
import hashlib
import json
import os
import statistics
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from experiments.model_eval.run import percentile
from experiments.w3.verification import ROOT, legal, load, manifest, measure
from fixtures.manifests.check_examples import canonical

from semaphore_core.embeddings import OllamaConfig, OllamaEmbedder, fingerprint_hash

HERE = Path(__file__).resolve().parent


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(destination):
    fixture_path = ROOT / "fixtures/semantic/fixture.json"
    fixture = json.loads(fixture_path.read_bytes())
    files = {}
    for split in ["calibration", "held_out"]:
        entries = [
            {"id": e["id"], "text": e["label"], "embed_text": e["embed_text"]}
            for e in fixture["entries"]
            if e["split"] == split
        ]
        clues = {
            e["id"]: [
                c["clue"]
                for c in fixture["cases"]
                if c["target_id"] == e["id"] and c["expected_legal"]
            ]
            for e in entries
        }
        for mode in ["authored", "weak", "mixed"]:
            tests = {}
            for index, entry in enumerate(entries):
                if mode == "weak":
                    selected = ["thing", "something", "a general concept"]
                elif mode == "mixed" and index % 3 == 0:
                    selected = next(
                        clues[e["id"]]
                        for e in entries
                        if e != entry and all(legal(c, entry) for c in clues[e["id"]])
                    )
                else:
                    selected = clues[entry["id"]]
                tests[entry["id"]] = selected
            value = {
                "spec_version": "1-experiment-w3",
                "pack": {
                    "id": f"w3-{split.replace('_', '-')}-{mode}",
                    "version": "0.0.1",
                    "name": "W3 synthetic protocol probe",
                    "author": "Semaphore",
                    "description": "Agent-authored synthetic; not human reviewed or publishable",
                    "tags": ["synthetic"],
                    "language": "en",
                    "license": "MIT",
                },
                "entries": entries,
                "test_set": tests,
            }
            filename = f"{split}-{mode}.json"
            raw = canonical(value)
            manifest(raw)
            path = destination / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                stream.write(raw)
            files[filename] = sha(path)
    write(
        destination / "plan.json",
        {
            "created_at": datetime.now(UTC).isoformat(),
            "fixture_sha256": sha(fixture_path),
            "inputs": files,
            "protocol_hash": hashlib.sha256(
                canonical(load("verification-policy.json"))
            ).hexdigest(),
            "fingerprint_hash": load("model-lock.json")["fingerprint_sha256"],
            "threshold": "0.85 diagnostic only; unchanged regardless of results",
            "mixed_policy": "every third target uses first other legal target's authored clues",
            "limitations": [
                "Synthetic reused vocabulary; prior held-out results already viewed",
                "No independent authors or marginal-pack labels; no publication calibration",
            ],
        },
    )


def parity(cases):
    result = subprocess.run(
        ["node", str(HERE / "parity.cjs")],
        input=json.dumps(cases),
        text=True,
        capture_output=True,
        check=True,
        timeout=30,
    )
    other = json.loads(result.stdout)
    if len(other) != len(cases):
        raise ValueError("parity case count mismatch")
    max_error = 0.0
    for case, actual in zip(cases, other, strict=True):
        from experiments.w3.verification import dot

        if actual["ordered"] != case["ordered"]:
            raise ValueError("numeric rank disagreement")
        for entry_id, row in case["entries"].items():
            error = abs(dot(case["query"], row) - actual["scores"][entry_id])
            max_error = max(max_error, error)
            if error > 1e-5:
                raise ValueError("numeric score disagreement")
    return {
        "cases": len(cases),
        "ordered_ids_equal": True,
        "max_score_error": max_error,
        "scope": "Python and Node binary64; not independent creator packaging parity",
    }


class TimedEmbedder(OllamaEmbedder):
    def __init__(self, config):
        super().__init__(config)
        self.timings = []

    def _request(self, path, payload=None):
        start = time.perf_counter()
        result = super()._request(path, payload)
        self.timings.append(
            {
                "path": path,
                "wall_ms": 1000 * (time.perf_counter() - start),
                "service_ms": (
                    result["total_duration"] / 1e6 if "total_duration" in result else None
                ),
                "inference_ms": (
                    result["prompt_eval_duration"] / 1e6
                    if "prompt_eval_duration" in result
                    else None
                ),
            }
        )
        return result


def latency(embedder):
    before = embedder.identity()
    summaries = {}
    # Fixed synthetic calibration clue; no semantic or prompt search.
    clue = "orchard snack"
    embedder.embed_queries([clue])
    for workers in [1, 4, 8]:
        embedder.timings.clear()

        def request(_):
            start = time.perf_counter()
            embedder.embed_queries([clue])
            return 1000 * (time.perf_counter() - start)

        with ThreadPoolExecutor(max_workers=workers) as pool:
            elapsed = list(pool.map(request, range(100)))
        groups = {}
        for path in ["/api/version", "/api/tags", "/api/embed"]:
            rows = [r for r in embedder.timings if r["path"] == path]
            groups[path] = {
                "count": len(rows),
                "wall_p50_ms": statistics.median(r["wall_ms"] for r in rows),
                "wall_p95_ms": percentile([r["wall_ms"] for r in rows], 0.95),
            }
            if path == "/api/embed":
                service = [r["service_ms"] for r in rows if r["service_ms"] is not None]
                inference = [r["inference_ms"] for r in rows if r["inference_ms"] is not None]
                residual = [
                    r["wall_ms"] - r["service_ms"] for r in rows if r["service_ms"] is not None
                ]
                groups[path].update(
                    service_duration_count=len(service),
                    inference_duration_count=len(inference),
                    service_p95_ms=percentile(service, 0.95) if service else None,
                    inference_p95_ms=percentile(inference, 0.95) if inference else None,
                    residual_p95_ms=percentile(residual, 0.95) if residual else None,
                )
        summaries[str(workers)] = {
            "requests": 100,
            "p50_ms": statistics.median(elapsed),
            "p95_ms": percentile(elapsed, 0.95),
            "components": groups,
        }
    if embedder.identity() != before:
        raise ValueError("identity changed during latency probe")
    return {
        "fingerprint_hash": fingerprint_hash(before),
        "concurrency": summaries,
        "target_ms": 100,
        "target_passed": all(s["p95_ms"] < 100 for s in summaries.values()),
        "scope": "Pinned adapter requests, not game/player load; no game queue exists yet",
        "timing_note": "service-reported durations; residual includes HTTP, JSON and client work",
    }


def run(source, output):
    plan = json.loads((source / "plan.json").read_bytes())
    if (
        plan["protocol_hash"]
        != hashlib.sha256(canonical(load("verification-policy.json"))).hexdigest()
    ):
        raise ValueError("protocol changed since prepare")
    for name, digest in plan["inputs"].items():
        if sha(source / name) != digest:
            raise ValueError("input changed since prepare")
    if plan["fingerprint_hash"] != load("model-lock.json")["fingerprint_sha256"]:
        raise ValueError("model lock changed since prepare")
    if plan["fixture_sha256"] != sha(ROOT / "fixtures/semantic/fixture.json"):
        raise ValueError("source fixture changed since prepare")
    config = OllamaConfig.from_env()
    if config.expected_digest != load("model-lock.json")["fingerprint"]["digest"]:
        raise ValueError("configure the exact model digest pin")
    embedder = TimedEmbedder(config)
    bindings = {}
    for split in ["calibration", "held_out"]:
        for mode in ["authored", "weak", "mixed"]:
            name = f"{split}-{mode}.json"
            report, cases = measure((source / name).read_bytes(), embedder)
            write(output / name, report)
            write(output / f"{split}-{mode}-parity.json", parity(cases))
            bindings[name] = sha(output / name)
            print(f"{name}: {report['metrics']}", flush=True)
        if split == "calibration":
            write(
                output / "freeze.json",
                {
                    "created_at": datetime.now(UTC).isoformat(),
                    "plan_sha256": sha(source / "plan.json"),
                    "calibration_reports": dict(bindings),
                    "policy": "unchanged; no threshold selection",
                },
            )
    write(output / "latency.json", latency(embedder))
    write(
        output / "binding.json",
        {
            "completed_at": datetime.now(UTC).isoformat(),
            "plan_sha256": sha(source / "plan.json"),
            "reports": bindings,
            "supplemental_reports": {
                p.name: sha(p) for p in sorted(output.glob("*.json")) if p.name not in bindings
            },
            "freeze_sha256": sha(output / "freeze.json"),
            "sources": {
                p.name: sha(p)
                for p in [HERE / "verification.py", HERE / "run.py", HERE / "parity.cjs"]
            },
            "python": os.sys.version,
            "node": subprocess.check_output(["node", "--version"], text=True).strip(),
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "run"])
    parser.add_argument("--inputs", type=Path, default=ROOT / "fixtures/w3")
    parser.add_argument("--output", type=Path, default=ROOT / "data/w3")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.inputs)
    else:
        run(args.inputs, args.output)
