"""Packaged schemas must remain exact copies of the coordinator contracts."""

import json
from pathlib import Path

import pytest
from jsonschema import ValidationError

from semaphore_hub.contracts import SCHEMAS, load, validator

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("name", (*SCHEMAS, "durable-openapi.json"))
def test_installed_contract_matches_repository(name):
    assert load(name) == json.loads((ROOT / "contracts" / name).read_text(encoding="utf-8"))


def test_installed_refs_resolve_without_network():
    validator("create", "http.schema.json").validate({"mode": "casual", "artifact_id": "fixture"})
    validator("config").validate(
        {"signup_enabled": True, "clue_retention_days": 30, "backup_retention_days": 30}
    )
    with pytest.raises(ValidationError):
        validator("config").validate(
            {"signup_enabled": True, "clue_retention_days": 31, "backup_retention_days": 30}
        )
    with pytest.raises(ValueError):
        validator("missing")
