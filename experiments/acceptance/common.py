"""Result and process boundaries shared by the probes."""

import hashlib
import json
import math
import os
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(path):
    return json.loads(Path(path).read_bytes())


def environment():
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT / "packages"), str(ROOT)])
    return env


def run_process(argv, *, stdin=None, timeout=300):
    completed = subprocess.run(
        argv,
        input=stdin,
        capture_output=True,
        cwd=ROOT,
        env=environment(),
        timeout=timeout,
        check=False,
    )
    if completed.returncode:
        # Worker errors may include private input or upstream bodies; do not echo either stream.
        raise RuntimeError(f"probe subprocess failed (exit {completed.returncode})")
    return json.loads(completed.stdout)


def worker(backend, raw, *, ollama_url=None, parse_only=False):
    argv = [sys.executable, "-m", "experiments.acceptance.verify_worker", "--backend", backend]
    if ollama_url:
        argv += ["--ollama-url", ollama_url]
    if parse_only:
        argv += ["--parse-only"]
    return run_process(argv, stdin=raw)


def result(kind, *, synthetic, passed, details):
    return {
        "result_version": "s1-w4-probes-v1",
        "probe": kind,
        "evidence": "synthetic-plumbing" if synthetic else "implementation-probe",
        "acceptance_established": False,
        "passed": passed,
        "runtime": {"python": platform.python_version(), "platform": platform.platform()},
        "details": details,
    }


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def summary(values):
    if not values:
        return {"count": 0, "p50_ms": None, "p95_ms": None, "max_ms": None}
    ordered = sorted(values)
    return {
        "count": len(values),
        "p50_ms": ordered[math.ceil(len(values) * 0.50) - 1],
        "p95_ms": ordered[math.ceil(len(values) * 0.95) - 1],
        "max_ms": ordered[-1],
    }
