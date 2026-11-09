"""Ensure integrated model contracts bind the actual preserved research evidence."""

import hashlib
import json
from datetime import datetime
from pathlib import Path

from semaphore_core.embeddings import fingerprint_hash

ROOT = Path(__file__).resolve().parents[2]


def test_model_lock_and_frozen_policy_bind_preserved_reports():
    evidence = ROOT / "docs/evidence/ollama"
    raw = (evidence / "qwen4b-calibration.json").read_bytes()
    calibration = json.loads(raw)
    held_out = json.loads((evidence / "qwen4b-held-out.json").read_bytes())
    freeze = json.loads((evidence / "policy-freeze.json").read_bytes())
    lock = json.loads((ROOT / "contracts/model-lock.json").read_bytes())
    digest = hashlib.sha256(raw).hexdigest()
    assert freeze["calibration_report_sha256"] == digest
    assert held_out["calibration_report_sha256"] == digest
    for report in (calibration, held_out):
        assert report["fingerprint"] == lock["fingerprint"]
        assert report["fingerprint_sha256"] == fingerprint_hash(lock["fingerprint"])
        assert report["fixture_sha256"] == freeze["fixture_sha256"]
    assert freeze["fingerprint_sha256"] == lock["fingerprint_sha256"]
    assert calibration["split"] == "calibration"
    assert held_out["split"] == "held_out"
    assert (
        datetime.fromisoformat(calibration["created_at"])
        < datetime.fromisoformat(freeze["frozen_at"])
        < datetime.fromisoformat(held_out["created_at"])
    )
