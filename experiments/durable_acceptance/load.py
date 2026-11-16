"""Opt-in W4 timing recorder. Does not load or call a model on import."""

import math
import time
from contextlib import contextmanager


class LoadRecorder:
    def __init__(self, monotonic_ns=time.monotonic_ns):
        self.clock = monotonic_ns
        self.samples = []

    @contextmanager
    def measure(self, phase, *, batch_size):
        if phase not in {"load", "entry_embed", "query_embed"}:
            raise ValueError("invalid phase")
        if type(batch_size) is not int or not 1 <= batch_size <= 500:
            raise ValueError("invalid batch size")
        start = self.clock()
        success = False
        try:
            yield
            success = True
        finally:
            self.samples.append(
                dict(
                    phase=phase,
                    batch_size=batch_size,
                    elapsed_ms=max(0, self.clock() - start) / 1_000_000,
                    success=success,
                )
            )

    def summary(self):
        durations = sorted(s["elapsed_ms"] for s in self.samples if s["success"])
        return dict(
            samples=list(self.samples),
            successful=len(durations),
            p95_ms=durations[math.ceil(len(durations) * 0.95) - 1] if durations else None,
            measured_model_acceptance=False,
        )
