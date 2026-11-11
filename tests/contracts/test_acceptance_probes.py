"""Adversarial checks that probes detect disagreement, incomplete work and fake evidence."""

import copy
import json
import sys

import pytest
from experiments.acceptance.common import ROOT, summary, worker
from experiments.acceptance.fake import fake_server
from experiments.acceptance.load import load_probe, pressure_windows, timing
from experiments.acceptance.parity import compare, invalid
from experiments.acceptance.replay import OracleAdapter, clean, reordered_delivery, replay
from experiments.acceptance.robustness import robustness
from experiments.acceptance.verify_worker import SyntheticEmbedder, execute


def measured():
    return {
        "status": "measured",
        "report": {"metrics": {"reachability": 0.5}, "elapsed_ms": 1},
        "audit": [
            {
                "target": "a",
                "sample": 0,
                "clue_index": 0,
                "ordered_ids": ["a", "b"],
                "target_rank": 1,
                "scores": {"a": 0.5, "b": 0.4},
            }
        ],
    }


def test_parity_surfaces_rank_disagreement_inside_numeric_tolerance():
    left = measured()
    right = copy.deepcopy(left)
    right["audit"][0]["ordered_ids"] = ["b", "a"]
    right["audit"][0]["scores"]["a"] += 0.000001
    assert "rank_or_sample:0" in compare(left, right)
    assert "numeric:0" not in compare(left, right)


def test_parity_cannot_pass_empty_audits_or_a_threshold_disagreement():
    left, right = measured(), measured()
    right["audit"] = []
    right["report"]["metrics"]["reachability"] = 0.9
    assert set(compare(left, right)) == {"audit_coverage", "report_fields_or_threshold_decision"}


def test_parity_checks_all_scores_and_nonfinite_values():
    left, right = measured(), measured()
    right["audit"][0]["scores"]["b"] = float("nan")
    assert "numeric:0" in compare(left, right)


def test_elapsed_time_does_not_cause_false_numeric_failure():
    left, right = measured(), measured()
    right["report"]["elapsed_ms"] = 999
    assert compare(left, right) == []


def test_fixture_expectations_withheld_and_bad_adapter_fails():
    class WrongAdapter(OracleAdapter):
        def __init__(self, trace):
            assert "expected_state" not in json.dumps(trace)
            super().__init__(trace)

        def step(self, event):
            assert "expected_state" not in event and "expected_result" not in event
            answer = super().step(event)
            answer["state"]["score"] += 1
            return answer

    assert not replay(WrongAdapter)["passed"]
    assert clean({"expected_revision": 2, "expected_state": {}}) == {"expected_revision": 2}
    assert replay()["passed"]
    assert reordered_delivery()["passed"]


def test_manifest_rejection_fresh_processes_do_not_embed_or_expose_inputs():
    report = invalid(
        (ROOT / "fixtures/w3/held_out-authored.json").read_bytes(), backend="reference"
    )
    assert report["passed"] and report["evidence"] == "synthetic-plumbing"
    assert all(c["actual"]["embedding_calls"] == 0 for c in report["details"]["checks"])
    assert "orchard snack" not in json.dumps(report)
    rejected = worker("reference", b'{"private-clue-canary": invalid}', parse_only=True)
    assert rejected == {"status": "rejected", "code": "invalid_json", "embedding_calls": 0}


def test_synthetic_embedder_only_depends_on_text_and_is_explicitly_fake():
    model = SyntheticEmbedder()
    assert model.embed_queries(["one"])[0] == model.embed_entries(["one"])[0]
    assert model.embed_entries(["one"])[0] != model.embed_entries(["two"])[0]


def test_configured_ollama_does_not_receive_invalid_manifest():
    assert execute(b"{", "core", ollama_url="http://127.0.0.1:1", parse_only=True) == {
        "status": "rejected",
        "code": "invalid_json",
        "embedding_calls": 0,
    }


@pytest.fixture
def origin():
    server = fake_server()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()


def test_fake_http_exercises_retry_stale_conflict_and_score_boundaries(origin):
    report = robustness(origin, synthetic=True)
    assert report["passed"]
    assert not report["acceptance_established"]


def test_load_drives_1_4_8_players_and_suppresses_fake_timings(origin):
    command = [sys.executable, "-c", 'print(\'{"status":"measured"}\')']
    report = load_probe(origin, "default", command, rounds=1, synthetic=True)
    assert report["passed"]
    groups = report["details"]["groups"]
    assert [g["successful_samples"] for g in groups] == [1, 4, 8]
    assert all(g["components"] is None and g["target_100ms_passed"] is None for g in groups)
    assert all(g["verification_overlap"] for g in groups)


def test_load_does_not_accept_successful_process_without_verification(origin):
    report = load_probe(
        origin, "default", [sys.executable, "-c", "print('{}')"], rounds=1, synthetic=True
    )
    assert not report["passed"]
    assert all(
        "verification_pressure_failed_or_no_overlap" in g["failures"]
        for g in report["details"]["groups"]
    )


def test_real_load_does_not_count_a_measured_status_as_model_pressure(origin):
    command = [sys.executable, "-c", 'print(\'{"status":"measured"}\')']
    report = load_probe(origin, "default", command, rounds=1)
    assert not report["passed"]
    assert all(
        group["verification_overlapping_samples"] == 0 and group["target_100ms_passed"] is None
        for group in report["details"]["groups"]
    )


def test_pressure_requires_real_matching_fingerprint_and_bounded_intervals():
    metadata = {
        "source": "ollama",
        "fingerprint_hash": "pinned",
        "embedding_windows": [[1.25, 1.5]],
    }
    value = {"pressure": metadata}
    assert pressure_windows(value, "pinned", 1, 2) == [[1.25, 1.5]]
    assert not pressure_windows(value, "other", 1, 2)
    assert not pressure_windows(value, "pinned", 1.3, 2)
    metadata["source"] = "synthetic"
    assert not pressure_windows(value, "pinned", 1, 2)


def test_missing_instrumentation_is_unknown_and_invalid_duration_fails():
    assert timing({}, "X-Semaphore-Queue-Ms") is None
    assert summary([])["p95_ms"] is None
    assert summary([2, 1, 3])["p95_ms"] == 3
    with pytest.raises(RuntimeError):
        timing({"X-Semaphore-Queue-Ms": "nan"}, "X-Semaphore-Queue-Ms")
