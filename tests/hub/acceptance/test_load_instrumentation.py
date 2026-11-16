from experiments.durable_acceptance.load import LoadRecorder


def test_load_recorder_captures_timing_not_exception_content():
    import pytest

    times = iter([0, 1_000_000, 2_000_000, 4_000_000])
    recorder = LoadRecorder(lambda: next(times))
    with recorder.measure("query_embed", batch_size=1):
        pass
    with pytest.raises(RuntimeError), recorder.measure("load", batch_size=1):
        raise RuntimeError("private exception content")
    result = recorder.summary()
    assert result["successful"] == 1
    assert result["p95_ms"] == 1
    assert result["samples"][1]["success"] is False
    assert "private" not in str(result)
    assert result["measured_model_acceptance"] is False
