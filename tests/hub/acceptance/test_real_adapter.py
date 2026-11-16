"""Independent probes against actual durable SQLite services in killed processes."""

import pytest
from experiments.durable_acceptance.harness import ProcessAdapter, behavior_probe, crash_probe


@pytest.fixture
def real_adapter(tmp_path):
    adapter = ProcessAdapter("experiments.durable_acceptance.real_adapter", tmp_path)
    try:
        yield adapter
    finally:
        adapter.close()


@pytest.mark.parametrize("phase", ["admission", "completion", "terminal"])
@pytest.mark.parametrize("edge", ["before", "after"])
def test_real_commit_window(real_adapter, phase, edge):
    assert crash_probe(real_adapter, phase, edge)["passed"]


def test_real_ownership_retry_cohort_deletion_restore(real_adapter):
    assert behavior_probe(real_adapter)["passed"]
