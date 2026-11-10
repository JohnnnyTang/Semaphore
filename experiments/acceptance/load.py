"""Round-trip HTTP load with concurrent, explicitly configured verification work."""

import concurrent.futures
import json
import math
import subprocess
import threading
import time
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


def player(transport, artifact_id, mode, rounds, gate, *, poll_seconds=0.01):
    status, frame, _ = transport.request(
        "POST",
        "/games",
        {
            "mode": mode,
            "artifact_id": artifact_id,
        },
    )
    if status != 201:
        raise RuntimeError("game creation failed")
    game_id = frame["snapshot"]["game_id"]
    route = f"/games/{game_id}"
    records = []
    gate.wait(timeout=30)
    for n in range(rounds):
        if frame["snapshot"]["status"] != "active":
            raise RuntimeError("artifact ended before requested sample count")
        command = {
            "command_id": f"load-{n}",
            "expected_revision": frame["snapshot"]["revision"],
            "clue": "distant association",
        }
        start = time.perf_counter()
        status, frame, headers = transport.request("POST", route + "/commands", command)
        if status not in {200, 202} or not frame["receipt"]:
            raise RuntimeError("missing command receipt")
        expires = time.monotonic() + 30
        while frame["receipt"]["outcome"] == "pending":
            if time.monotonic() > expires:
                raise RuntimeError("receipt polling deadline")
            time.sleep(poll_seconds)
            status, frame, headers = transport.request("GET", route + f"/receipts/load-{n}")
            if status != 200 or not frame["receipt"]:
                raise RuntimeError("receipt resolution failed")
        outcome = frame["receipt"]["outcome"]
        records.append(
            {
                "round_trip_ms": (time.perf_counter() - start) * 1000,
                "outcome": outcome,
                "queue_ms": timing(headers, "X-Semaphore-Queue-Ms"),
                "embedding_ms": timing(headers, "X-Semaphore-Embedding-Ms"),
            }
        )
        # Retry exact payload after terminal resolution: it must not reapply or rerank.
        _, retry, _ = transport.request("POST", route + "/commands", command)
        if retry["receipt"] != frame["receipt"]:
            raise RuntimeError("terminal retry changed receipt")
        if retry["snapshot"]["score"] != frame["snapshot"]["score"]:
            raise RuntimeError("terminal retry changed score")
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
    for players in [1, 4, 8]:
        gate = threading.Barrier(players + 1)
        stop = threading.Event()
        runs = []
        failures = []

        def pressure(gate=gate, stop=stop, runs=runs):
            gate.wait(timeout=30)
            while not stop.is_set():
                start = time.perf_counter()
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
                    ok = completed.returncode == 0 and value.get("status") == "measured"
                except (subprocess.TimeoutExpired, ValueError):
                    ok = False
                runs.append({"start": start, "end": time.perf_counter(), "passed": ok})
                if not ok:
                    break

        with concurrent.futures.ThreadPoolExecutor(max_workers=players + 1) as pool:
            background = pool.submit(pressure)
            tasks = [
                pool.submit(
                    player,
                    HTTPTransport(origin),
                    artifact_id,
                    mode,
                    rounds,
                    gate,
                    poll_seconds=poll_seconds,
                )
                for _ in range(players)
            ]
            measured_start = time.perf_counter()
            records = []
            for task in tasks:
                try:
                    records.extend(task.result(timeout=360))
                except Exception as exc:
                    failures.append(type(exc).__name__)
            measured_end = time.perf_counter()
            stop.set()
            try:
                background.result(timeout=310)
            except Exception as exc:
                failures.append(type(exc).__name__)
        overlap = any(r["start"] < measured_end and r["end"] > measured_start for r in runs)
        successful = [r for r in records if r["outcome"] in {"clear", "miss"}]
        failures += [f"outcome:{r['outcome']}" for r in records if r not in successful]
        if not runs or not all(r["passed"] for r in runs) or not overlap:
            failures.append("verification_pressure_failed_or_no_overlap")
        components = {
            field: summary([r[field] for r in successful if r[field] is not None])
            for field in ["round_trip_ms", "queue_ms", "embedding_ms"]
        }
        groups.append(
            {
                "players": players,
                "requested_samples": players * rounds,
                "successful_samples": len(successful),
                "verification_runs": len(runs),
                "verification_overlap": overlap,
                "failures": failures,
                "components": None if synthetic else components,
                "target_100ms_passed": None
                if synthetic or failures
                else (components["round_trip_ms"]["p95_ms"] <= 100),
            }
        )
    return result(
        "http-load",
        synthetic=synthetic,
        passed=all(not g["failures"] for g in groups),
        details={
            "groups": groups,
            "poll_seconds": poll_seconds,
            "pressure_scope": "separate-process; shared model contention must be confirmed",
            "timing_source": "optional server headers; missing components remain unknown",
        },
    )
