"""Validate frozen HTTP examples and all local references without network access."""

import copy
import json
from pathlib import Path
from urllib.parse import urljoin

import pytest
from jsonschema import Draft202012Validator, ValidationError
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[3]
BASE = "https://semaphore.invalid/contracts/"
DOCUMENTS = {
    name: json.loads((ROOT / "contracts" / name).read_text(encoding="utf-8"))
    for name in ("durable-http.schema.json", "http.schema.json", "events.schema.json")
}
REGISTRY = Registry().with_resources(
    (BASE + name, Resource.from_contents(document)) for name, document in DOCUMENTS.items()
)
API = json.loads((ROOT / "contracts/durable-openapi.json").read_text())
CASES = json.loads((ROOT / "fixtures/durable/payloads.json").read_text())["cases"]


def validator(reference):
    return Draft202012Validator({"$ref": urljoin(BASE, reference)}, registry=REGISTRY)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_fixture_payloads(case):
    validator(case["schema"]).validate(case["value"])


def references(value):
    if isinstance(value, dict):
        if "$ref" in value:
            yield value["$ref"]
        for child in value.values():
            yield from references(child)
    elif isinstance(value, list):
        for child in value:
            yield from references(child)


def test_every_schema_and_external_reference_resolves_locally():
    for name, document in DOCUMENTS.items():
        Draft202012Validator.check_schema(document)
        resolver = REGISTRY.resolver(BASE + name)
        for reference in references(document):
            assert resolver.lookup(reference).contents is not None
    resolver = REGISTRY.resolver(BASE + "durable-openapi.json")
    for reference in references(API):
        assert resolver.lookup(reference).contents is not None


def test_routes_security_and_frozen_game_contract():
    assert API["openapi"] == "3.1.0"
    operations = set()
    for path, methods in API["paths"].items():
        assert path.startswith("/api/v1/")
        for method, operation in methods.items():
            assert operation["operationId"] not in operations
            operations.add(operation["operationId"])
            public = path in {"/api/v1/config", "/api/v1/auth/signup", "/api/v1/auth/login"}
            assert operation["security"] == ([] if public else [{"sessionCookie": []}])
            params = operation.get("parameters", [])
            required = {p["name"] for p in params if p.get("required")}
            for segment in path.split("/"):
                if segment.startswith("{"):
                    assert segment[1:-1] in required
            if method == "post":
                assert "Origin" in required
                if not public:
                    assert "X-CSRF-Token" in required
    create = API["paths"]["/api/v1/games"]["post"]
    assert "do not automatically retry" in create["description"]
    assert create["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "http.schema.json#/$defs/create"
    }
    assert "requestBody" not in API["paths"]["/api/v1/games/{game_id}/quit"]["post"]
    assert "410" not in API["paths"]["/api/v1/games/{game_id}"]["get"]["responses"]
    assert (
        "410" in API["paths"]["/api/v1/games/{game_id}/receipts/{command_id}"]["get"]["responses"]
    )


@pytest.mark.parametrize("field", ["account_id", "login_name", "clue", "receipt", "session_token"])
def test_public_board_rejects_private_fields(field):
    value = copy.deepcopy(next(c["value"] for c in CASES if c["name"] == "board"))
    value["items"][0][field] = "must not escape"
    with pytest.raises(ValidationError):
        validator("durable-http.schema.json#/$defs/board").validate(value)


def test_cohort_is_complete_and_casual_identity_is_unambiguous():
    value = copy.deepcopy(next(c["value"] for c in CASES if c["name"] == "artifact"))
    for field in value["cohort"]:
        missing = copy.deepcopy(value)
        del missing["cohort"][field]
        with pytest.raises(ValidationError):
            validator("durable-http.schema.json#/$defs/artifact").validate(missing)
    value["cohort"]["challenge_digest"] = "d" * 64
    with pytest.raises(ValidationError):
        validator("durable-http.schema.json#/$defs/artifact").validate(value)


def test_interrupted_history_cannot_claim_competitive_result():
    result = copy.deepcopy(next(c["value"] for c in CASES if c["name"] == "history"))
    result["items"][1]["competitive"] = True
    with pytest.raises(ValidationError):
        validator("durable-http.schema.json#/$defs/history").validate(result)


def test_bounded_pages_and_cursors():
    result = {"items": [], "next_cursor": "x" * 201}
    with pytest.raises(ValidationError):
        validator("durable-http.schema.json#/$defs/history").validate(result)
    pack = next(c["value"] for c in CASES if c["name"] == "pack")
    with pytest.raises(ValidationError):
        validator("durable-http.schema.json#/$defs/packs").validate(
            {"items": [pack] * 101, "next_cursor": None}
        )


SCENARIOS = json.loads((ROOT / "fixtures/durable/scenarios.json").read_text())


@pytest.mark.parametrize("scenario", SCENARIOS["scenarios"], ids=lambda s: s["name"])
def test_http_scenarios_match_operation_schemas(scenario):
    cases = {case["name"]: case for case in CASES}
    op = API["paths"][scenario["path"]][scenario["method"]]
    if "request_case" in scenario:
        schema = op["requestBody"]["content"]["application/json"]["schema"]
        validator(schema["$ref"]).validate(cases[scenario["request_case"]]["value"])
    response = op["responses"][str(scenario["status"])]
    if "response_case" in scenario:
        schema = response["content"]["application/json"]["schema"]
        validator(schema["$ref"]).validate(cases[scenario["response_case"]]["value"])
    else:
        assert scenario["status"] == 204 and "content" not in response


def test_uncertain_create_fixture_never_silently_retries():
    assert SCENARIOS["uncertain_create"]["automatic_retry"] is False
    assert SCENARIOS["uncertain_create"]["transport_outcome"] == "response_lost"


@pytest.mark.parametrize(
    "mode,reason",
    [("casual", "event_complete"), ("event", "pack_cleared"), ("event", "pack_exhausted")],
)
def test_result_terminal_reason_matches_mode(mode, reason):
    result = copy.deepcopy(next(c["value"] for c in CASES if c["name"] == "history"))
    row = result["items"][0]
    row["cohort"]["mode"] = mode
    row["cohort"]["challenge_digest"] = "d" * 64 if mode == "event" else None
    row["end_reason"] = reason
    with pytest.raises(ValidationError):
        validator("durable-http.schema.json#/$defs/history").validate(result)


def test_natural_durable_result_is_competitive():
    result = copy.deepcopy(next(c["value"] for c in CASES if c["name"] == "history"))
    result["items"][0]["competitive"] = False
    with pytest.raises(ValidationError):
        validator("durable-http.schema.json#/$defs/history").validate(result)
