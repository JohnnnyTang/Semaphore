"""Observable transport trust boundaries and command receipt idempotency."""

from experiments.acceptance.common import result
from experiments.acceptance.load import HTTPTransport


def robustness(origin, artifact_id="default", *, synthetic=False):
    client = HTTPTransport(origin)
    status, frame, _ = client.request(
        "POST",
        "/games",
        {
            "artifact_id": artifact_id,
            "mode": "casual",
        },
    )
    if status != 201:
        raise RuntimeError("game creation failed")
    route = "/games/" + frame["snapshot"]["game_id"]
    revision = frame["snapshot"]["revision"]
    checks = []
    command = {
        "command_id": "stale",
        "expected_revision": revision + 100,
        "clue": "distant association",
    }
    _, stale, _ = client.request("POST", route + "/commands", command)
    checks.append(
        {
            "case": "future_revision_rejected",
            "passed": stale["receipt"]["outcome"] == "stale_revision",
        }
    )
    _, retry, _ = client.request("POST", route + "/commands", command)
    checks.append({"case": "rejected_retry_cached", "passed": retry["receipt"] == stale["receipt"]})
    _, conflict, _ = client.request("POST", route + "/commands", {**command, "clue": "changed"})
    checks.append(
        {
            "case": "command_payload_conflict",
            "passed": conflict["receipt"]["outcome"] == "command_conflict",
        }
    )
    status, _, _ = client.request("POST", route + "/commands", {**command, "score": 100000})
    checks.append({"case": "client_score_rejected", "passed": status == 400})
    command = {"command_id": "long", "expected_revision": revision, "clue": "x" * 121}
    status, long, _ = client.request("POST", route + "/commands", command)
    checks.append(
        {
            "case": "oversized_clue_receipt",
            "passed": status == 200 and long["receipt"]["outcome"] == "clue_too_long",
        }
    )
    status, _, _ = client.request("GET", route + "/receipts/unknown")
    checks.append({"case": "unknown_receipt", "passed": status == 404})
    _, quit_frame, _ = client.request("POST", route + "/quit")
    _, quit_retry, _ = client.request("POST", route + "/quit")
    checks.append(
        {
            "case": "quit_retry_noop",
            "passed": (
                quit_frame["snapshot"]["revision"] == quit_retry["snapshot"]["revision"]
                and quit_retry["snapshot"]["status"] == "over"
            ),
        }
    )
    return result(
        "http-robustness",
        synthetic=synthetic,
        passed=all(c["passed"] for c in checks),
        details={"checks": checks},
    )
