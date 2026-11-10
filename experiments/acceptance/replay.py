"""Compare observed adapter transitions with fixtures; adapters never receive expectations."""

import copy
import importlib

from experiments.acceptance.common import ROOT, load, result


class OracleAdapter:
    """Offline rules oracle, deliberately labeled plumbing rather than an engine test."""

    def __init__(self, trace):
        self.trace = trace
        self.state = copy.deepcopy(trace["initial_state"])
        self.receipts = {}

    def step(self, event):
        from fixtures.game_traces.validate import apply

        outcome = apply(self.trace, self.state, self.receipts, event)
        return {"result": outcome, "state": copy.deepcopy(self.state)}


def clean(value):
    if isinstance(value, dict):
        return {
            k: clean(v) for k, v in value.items() if k not in {"expected_state", "expected_result"}
        }
    if isinstance(value, list):
        return [clean(item) for item in value]
    return copy.deepcopy(value)


def replay(factory=OracleAdapter, paths=None, *, synthetic=True):
    checks = []
    for path in paths or sorted((ROOT / "fixtures/game_traces").glob("*.json")):
        trace = load(path)
        adapter = factory(clean(trace))
        for n, event in enumerate(trace["events"]):
            actual = adapter.step(clean(event))
            checks.append(
                {
                    "trace": path.name,
                    "event_index": n,
                    "passed": actual
                    == {"result": event["expected_result"], "state": event["expected_state"]},
                }
            )
    return result(
        "trace-replay",
        synthetic=synthetic,
        passed=bool(checks) and all(c["passed"] for c in checks),
        details={"checks": checks, "expectations_withheld": True},
    )


def import_factory(spec):
    module, name = spec.split(":", 1)
    return getattr(importlib.import_module(module), name)


class RevisionObserver:
    """Client observation probe: old delivery may resolve receipts but never roll back state."""

    def __init__(self):
        self.snapshot = None
        self.receipts = {}

    def apply(self, envelope):
        current = envelope["snapshot"]
        if self.snapshot is None or current["revision"] >= self.snapshot["revision"]:
            self.snapshot = copy.deepcopy(current)
        receipt = envelope["receipt"]
        if receipt:
            prior = self.receipts.get(receipt["command_id"])
            # A delayed pending response cannot overwrite an already-final receipt.
            if prior is None or prior["outcome"] == "pending":
                self.receipts[receipt["command_id"]] = copy.deepcopy(receipt)


def reordered_delivery():
    checks = []
    for path in sorted((ROOT / "fixtures/protocol").glob("*.json")):
        frames = load(path)["envelopes"]
        observer = RevisionObserver()
        for frame in [*frames, *reversed(frames), *frames[:2]]:
            observer.apply(frame)
        highest = max(frames, key=lambda f: f["snapshot"]["revision"])["snapshot"]
        checks.append({"fixture": path.name, "passed": observer.snapshot == highest})
    return result(
        "out-of-order-delivery",
        synthetic=True,
        passed=bool(checks) and all(c["passed"] for c in checks),
        details={"checks": checks, "scope": "harness-observer-only; not browser evidence"},
    )
