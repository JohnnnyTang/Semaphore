from pathlib import Path

import pytest
from experiments.durable_acceptance.harness import (
    ProbeFailure,
    ProcessAdapter,
    behavior_probe,
    crash_probe,
)

ADAPTER_DIR = Path(__file__).parent.resolve()


def adapter(tmp_path, fault=None):
    if fault:
        (tmp_path / "fault.txt").write_text(fault)
    return ProcessAdapter("fake_probe_adapter", tmp_path, pythonpath=(ADAPTER_DIR,))


@pytest.mark.parametrize("phase", ["admission", "completion", "terminal"])
@pytest.mark.parametrize("edge", ["before", "after"])
def test_subprocess_crash_oracle(tmp_path, phase, edge):
    assert crash_probe(adapter(tmp_path), phase, edge)["passed"]


def test_behavior_oracle(tmp_path):
    assert behavior_probe(adapter(tmp_path))["passed"]


@pytest.mark.parametrize(
    "fault,code",
    [
        ("changed_retry", "changed_retry_accepted"),
        ("foreign_access", "foreign_receipt_disclosure"),
        ("retain_clues", "clue_deletion_failed"),
        ("retry_inference", "retry_reran_inference"),
        ("cohort_leak", "cohort_cursor_leak"),
        ("tie_skip", "board_full_tie_key"),
        ("ledger_ignored", "restore_resurrected_private_data"),
    ],
)
def test_behavior_detects_faulty_adapters(tmp_path, fault, code):
    with pytest.raises(ProbeFailure, match=code):
        behavior_probe(adapter(tmp_path, fault))


@pytest.mark.parametrize(
    "fault,code",
    [
        ("commit_before_hook", "admission_atomicity"),
        ("recovery_scores", "score_atomicity"),
    ],
)
def test_crash_detects_faulty_adapters(tmp_path, fault, code):
    with pytest.raises(ProbeFailure, match=code):
        crash_probe(adapter(tmp_path, fault), "admission", "before")


def test_missing_checkpoint_is_failure(tmp_path):
    with pytest.raises(ProbeFailure, match="checkpoint_not_reached"):
        adapter(tmp_path).call("fixture_setup", {"phase": "behavior"}, crash_at="unknown")
