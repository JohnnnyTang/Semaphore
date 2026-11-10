"""Two independent process paths: frozen W3 oracle versus callable W4 core."""

import copy
import json
import math

from experiments.acceptance.common import digest, result, worker


def compare(left, right):
    failures = []
    if left["status"] != right["status"]:
        return ["status"]
    if left["status"] == "rejected":
        return [] if left["code"] == right["code"] else ["rejection_code"]
    a, b = copy.deepcopy(left["report"]), copy.deepcopy(right["report"])
    a.pop("elapsed_ms", None)
    b.pop("elapsed_ms", None)
    if a != b:
        failures.append("report_fields_or_threshold_decision")
    if len(left["audit"]) != len(right["audit"]) or not left["audit"]:
        failures.append("audit_coverage")
    for n, (a, b) in enumerate(zip(left["audit"], right["audit"], strict=False)):
        if {k: v for k, v in a.items() if k != "scores"} != {
            k: v for k, v in b.items() if k != "scores"
        }:
            failures.append(f"rank_or_sample:{n}")
        if a["scores"].keys() != b["scores"].keys() or any(
            not math.isfinite(v)
            or not math.isfinite(b["scores"].get(k, math.nan))
            or abs(v - b["scores"].get(k, math.inf)) > 1e-5
            for k, v in a["scores"].items()
        ):
            failures.append(f"numeric:{n}")
    return failures


def parity(raw, *, backend="core", ollama_url=None):
    left = worker("reference", raw, ollama_url=ollama_url)
    right = worker(backend, raw, ollama_url=ollama_url)
    failures = compare(left, right)
    return result(
        "parity",
        synthetic=not ollama_url,
        passed=not failures,
        details={
            "paths": ["fresh-process:w3-reference", f"fresh-process:{backend}"],
            "independent_implementation": backend == "core",
            "manifest_sha256": digest(raw),
            "sample_clue_cases": len(left.get("audit", [])),
            "failures": failures,
            "status": left["status"],
            "tolerance": 1e-5,
            "diagnostic_threshold_only": True,
        },
    )


def invalid_cases(raw):
    base = json.loads(raw)
    vectors = copy.deepcopy(base)
    vectors["vectors"] = [[1]]
    illegal = copy.deepcopy(base)
    first = illegal["entries"][0]
    illegal["test_set"][first["id"]][0] = first["text"]
    missing = copy.deepcopy(base)
    missing["pack"].pop("license")
    return [
        ("malformed", b"{", "invalid_json"),
        ("oversized", b" " * (8 * 1024 * 1024 + 1), "body_too_large"),
        ("duplicate_json_key", b'{"id":"a","id":"b"}', "invalid_json"),
        ("uploaded_vectors", json.dumps(vectors).encode(), "schema_invalid"),
        ("missing_license", json.dumps(missing).encode(), "schema_invalid"),
        ("illegal_clue", json.dumps(illegal).encode(), "illegal_clue"),
    ]


def invalid(raw, *, backend="core"):
    checks = []
    for name, candidate, code in invalid_cases(raw):
        actual = worker(backend, candidate, parse_only=True)
        checks.append(
            {
                "case": name,
                "expected_code": code,
                "actual": actual,
                "passed": actual.get("code") == code and actual["embedding_calls"] == 0,
            }
        )
    return result(
        "manifest-rejection",
        synthetic=True,
        passed=all(c["passed"] for c in checks),
        details={"checks": checks},
    )
