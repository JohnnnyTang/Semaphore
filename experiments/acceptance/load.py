"""Round-trip HTTP load with concurrent, explicitly configured verification work."""

import concurrent.futures
import json
import math
import subprocess
import threading
import time
from collections import Counter
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from experiments.acceptance.common import ROOT, environment, load, result, summary
from jsonschema import Draft202012Validator


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class HTTPTransport:
    def __init__(self, origin, *, timeout=15):
        self.origin = origin.rstrip("/")
        self.timeout = timeout
        self.validator = Draft202012Validator(load(ROOT / "contracts/events.schema.json"))

    def request(self, method, route, value=None):
        request = Request(
            self.origin + "/experiment/v1" + route,
            method=method,
            data=None if value is None else json.dumps(value).encode(),
            headers={"Content-Type": "application/json"},
        )
        opener = build_opener(ProxyHandler({}), NoRedirect())
        try:
            response = opener.open(request, timeout=self.timeout)
        except HTTPError as exc:
            response = exc
        with response:
            raw = response.read(2 * 1024 * 1024 + 1)
            if len(raw) > 2 * 1024 * 1024:
                raise RuntimeError("response size limit")
            body = json.loads(raw)
            if response.code in {200, 201, 202}:
                self.validator.validate(body)
            return response.code, body, dict(response.headers.items())


def timing(headers, name):
    value = next((v for k, v in headers.items() if k.lower() == name.lower()), None)
    if value is None:
        return None
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise RuntimeError("invalid server timing")
    return number


def pressure_windows(value, expected_fingerprint, start, end):
    metadata = value.get("pressure")
    if not isinstance(metadata, dict) or (
        metadata.get("source") != "ollama"
        or metadata.get("fingerprint_hash") != expected_fingerprint
    ):
        return []
    windows = metadata.get("embedding_windows")
    if not isinstance(windows, list) or not all(
        isinstance(window, list)
        and len(window) == 2
        and all(type(t) in {float, int} for t in window)
        and start <= window[0] < window[1] <= end
        for window in windows
    ):
        return []
    return windows


class PlayerFailure(RuntimeError):
    """Fixed probe-authored reason, safe to include without upstream bodies or clues."""


def player(transport, artifact_id, mode, rounds, gate, *, poll_seconds=0.01, records=None):
    status, frame, _ = transport.request(
        "POST",
        "/games",
        {
            "mode": mode,
            "artifact_id": artifact_id,
        },
    )
    if status != 201:
        raise PlayerFailure("game creation failed")
    game_id = frame["snapshot"]["game_id"]
    route = f"/games/{game_id}"
    records = [] if records is None else records
    gate.wait(timeout=30)
    for n in range(rounds):
        if frame["snapshot"]["status"] != "active":
            raise PlayerFailure("artifact ended before requested sample count")
        command = {
            "command_id": f"load-{n}",
            "expected_revision": frame["snapshot"]["revision"],
            "clue": "distant association",
        }
        start = time.perf_counter()
        status, frame, headers = transport.request("POST", route + "/commands", command)
        if status not in {200, 202} or not frame["receipt"]:
            raise PlayerFailure("missing command receipt")
        expires = time.monotonic() + 30
        while frame["receipt"]["outcome"] == "pending":
            if time.monotonic() > expires:
                raise PlayerFailure("receipt polling deadline")
            time.sleep(poll_seconds)
            status, frame, headers = transport.request("GET", route + f"/receipts/load-{n}")
            if status != 200 or not frame["receipt"]:
                raise PlayerFailure("receipt resolution failed")
        outcome = frame["receipt"]["outcome"]
        end = time.perf_counter()
        records.append(
            {
                "start": start,
                "end": end,
                "round_trip_ms": (end - start) * 1000,
                "outcome": outcome,
                "queue_ms": timing(headers, "X-Semaphore-Queue-Ms"),
                "embedding_ms": timing(headers, "X-Semaphore-Embedding-Ms"),
            }
        )
        # Retry exact payload after terminal resolution: it must not reapply or rerank.
        _, retry, _ = transport.request("POST", route + "/commands", command)
        if retry["receipt"] != frame["receipt"]:
            raise PlayerFailure("terminal retry changed receipt")
        if retry["snapshot"]["score"] != frame["snapshot"]["score"]:
            raise PlayerFailure("terminal retry changed score")
        _, frame, _ = transport.request("GET", route)
    transport.request("POST", route + "/quit")
    return records


def load_probe(
    origin,
    artifact_id,
    verification_command,
    *,
    rounds=10,
    synthetic=False,
    mode="casual",
    poll_seconds=0.01,
):
    if (
        rounds < 1
        or not verification_command
        or not all(isinstance(arg, str) for arg in verification_command)
    ):
        raise ValueError("positive rounds and an explicit verification argv are required")
    groups = []
    expected_fingerprint = load(ROOT / "contracts/model-lock.json")["fingerprint_sha256"]
    for players in [1, 4, 8]:
        gate = threading.Barrier(players + 1)
        stop = threading.Event()
        runs = []
        failures = []

        def pressure(gate=gate, stop=stop, runs=runs):
            gate.wait(timeout=30)
            while not stop.is_set():
                start = time.perf_counter()
                windows = []
                try:
                    completed = subprocess.run(
                        verification_command,
                        cwd=ROOT,
                        env=environment(),
                        capture_output=True,
                        timeout=300,
                        check=False,
                    )
                    # Require a structured measured result; an arbitrary successful command
                    # is not evidence that any verification work occurred.
                    value = json.loads(completed.stdout)
                    ok = (
                        completed.returncode == 0
                        and isinstance(value, dict)
                        and value.get("status") == "measured"
                    )
                    if ok and not synthetic:
                        windows = pressure_windows(
                            value, expected_fingerprint, start, time.perf_counter()
                        )
                        ok = bool(windows)
                except (subprocess.TimeoutExpired, ValueError):
                    ok = False
                runs.append(
                    {"start": start, "end": time.perf_counter(), "passed": ok, "windows": windows}
                )
                if not ok:
                    break

        with concurrent.futures.ThreadPoolExecutor(max_workers=players + 1) as pool:
            background = pool.submit(pressure)
            samples_by_player = [[] for _ in range(players)]
            tasks = [
                (
                    pool.submit(
                        player,
                        HTTPTransport(origin),
                        artifact_id,
                        mode,
                        rounds,
                        gate,
                        poll_seconds=poll_seconds,
                        records=samples,
                    ),
                    samples,
                )
                for samples in samples_by_player
            ]
            records = []
            for task, samples in tasks:
                try:
                    task.result(timeout=360)
                except Exception as exc:
                    failures.append(
                        str(exc) if isinstance(exc, PlayerFailure) else type(exc).__name__
                    )
                finally:
                    records.extend(samples)
            stop.set()
            try:
                background.result(timeout=310)
            except Exception as exc:
                failures.append(type(exc).__name__)
        successful = [r for r in records if r["outcome"] in {"clear", "miss"}]
        windows = [
            window
            for run in runs
            if run["passed"]
            for window in ([[run["start"], run["end"]]] if synthetic else run["windows"])
        ]
        overlapping_samples = sum(
            any(start < record["end"] and end > record["start"] for start, end in windows)
            for record in successful
        )
        overlap = overlapping_samples > 0
        failures += [f"outcome:{r['outcome']}" for r in records if r not in successful]
        if not runs or not all(r["passed"] for r in runs) or not overlap:
            failures.append("verification_pressure_failed_or_no_overlap")
        components = {
            field: summary([r[field] for r in successful if r[field] is not None])
            for field in ["round_trip_ms", "queue_ms", "embedding_ms"]
        }
        target_passed = None
        if not synthetic and not failures:
            if components["round_trip_ms"]["p95_ms"] > 100:
                target_passed = False
            elif all(part["count"] == len(successful) for part in components.values()):
                target_passed = True
        groups.append(
            {
                "players": players,
                "requested_samples": players * rounds,
                "recorded_samples": len(records),
                "outcome_counts": dict(Counter(r["outcome"] for r in records)),
                "successful_samples": len(successful),
                "verification_runs": len(runs),
                "verification_overlap": overlap,
                "verification_overlapping_samples": overlapping_samples,
                "failures": failures,
                "components": None if synthetic else components,
                "target_100ms_passed": target_passed,
            }
        )
    return result(
        "http-load",
        synthetic=synthetic,
        passed=all(not g["failures"] for g in groups),
        details={
            "groups": groups,
            "poll_seconds": poll_seconds,
            "pressure_scope": "synthetic verifier process interval"
            if synthetic
            else "pinned Ollama verifier adapter calls; configure the same origin for gameplay",
            "timing_source": "optional server headers; missing components remain unknown",
        },
    )
