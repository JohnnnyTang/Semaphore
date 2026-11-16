"""Contract assertions independent of the E/F service implementations."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path


class ProbeFailure(AssertionError):
    pass


def require(condition, code):
    if not condition:
        raise ProbeFailure(code)


class ProcessAdapter:
    def __init__(self, module, workspace, *, timeout=15, pythonpath=()):
        self.module = module
        self.root = Path(workspace).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.pythonpath = tuple(map(str, pythonpath))

    def close(self):
        process = getattr(self, "process", None)
        if process is not None:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)
            process.stdin.close()
            self.process = None

    def __del__(self):
        self.close()

    def _start(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join([*self.pythonpath, os.getcwd()])
        command = [
            sys.executable,
            "-m",
            "experiments.durable_acceptance.worker",
            self.module,
            str(self.root),
        ]
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
        )

    def call(self, operation, payload=None, *, crash_at=None):
        for name in ("checkpoint.json", "result.json", "failure.json"):
            (self.root / name).unlink(missing_ok=True)
        if getattr(self, "process", None) is None:
            self._start()
        process = self.process
        try:
            request = dict(operation=operation, payload=payload or {}, fault=crash_at)
            process.stdin.write((json.dumps(request) + "\n").encode())
            process.stdin.flush()
            until = time.monotonic() + self.timeout
            while True:
                if crash_at and (self.root / "checkpoint.json").exists():
                    marker = json.loads((self.root / "checkpoint.json").read_text())
                    self.close()
                    require(marker == {"checkpoint": crash_at}, "wrong_checkpoint")
                    return {"killed_at": crash_at}
                if (self.root / "result.json").exists():
                    require(not crash_at, "checkpoint_not_reached")
                    result = json.loads((self.root / "result.json").read_text())
                    require(isinstance(result, dict), "invalid_observation")
                    return result
                require(process.poll() is None, "adapter_failed")
                require(time.monotonic() < until, "adapter_timeout")
                time.sleep(0.01)
        except BaseException:
            self.close()
            raise


def crash_probe(adapter, phase, edge):
    """Setup chooses one active synthetic game, completing prerequisites without faults."""
    adapter.call("fixture_setup", {"phase": phase})
    checkpoint = f"{phase}.{edge}_commit"
    adapter.call(phase, crash_at=checkpoint)
    adapter.call("recover")
    state = adapter.call("observe")
    require(state["status"] == "over", "active_after_recovery")
    require(state["pending_count"] == 0, "pending_after_recovery")
    require(
        state["command_count"] == (0 if phase == "admission" and edge == "before" else 1),
        "admission_atomicity",
    )
    natural = phase == "terminal" and edge == "after"
    require(state["score_count"] == int(natural), "score_atomicity")
    require(
        state["end_reason"] == ("pack_cleared" if natural else "interrupted"), "terminal_outcome"
    )
    if state["command_count"]:
        expected = (
            "completed"
            if phase == "terminal" or (phase == "completion" and edge == "after")
            else "game_over"
        )
        require(state["receipt_outcome"] == expected, "receipt_atomicity")
    again = adapter.call("recover")
    require(again.get("ready") is True, "recovery_not_ready")
    require(adapter.call("observe") == state, "recovery_not_idempotent")
    return {"probe": checkpoint, "passed": True}


def behavior_probe(adapter):
    adapter.call("fixture_setup", {"phase": "behavior"})
    adapter.call("admission")
    adapter.call("completion")
    adapter.call("terminal")
    original = adapter.call("retry", {"variant": "exact"})
    require(original["status"] == 200, "exact_retry_failed")
    for variant in ("clue_case", "clue_whitespace", "expected_revision"):
        changed = adapter.call("retry", {"variant": variant})
        require(
            changed.get("status") == 200
            and changed.get("receipt", {}).get("outcome") == "command_conflict",
            "changed_retry_accepted",
        )
    for known in (True, False):
        require(
            adapter.call("foreign_receipt", {"known_command": known}) == {"status": 404},
            "foreign_receipt_disclosure",
        )
    adapter.call("delete_clues")
    require(adapter.call("observe")["raw_count"] == 0, "clue_deletion_failed")
    require(adapter.call("retry", {"variant": "exact"}) == original, "retry_changed_after_deletion")
    require(adapter.call("observe")["inference_calls"] == 1, "retry_reran_inference")
    board = adapter.call("board", {"cohort": "accepted", "limit": 1})
    require(board["items"] == ["tie-a"], "board_first_tie")
    second = adapter.call(
        "board", {"cohort": "accepted", "limit": 1, "cursor": board["next_cursor"]}
    )
    require(second["items"] == ["tie-b"], "board_full_tie_key")
    require(
        adapter.call("board", {"cohort": "other", "cursor": board["next_cursor"]})["status"] == 400,
        "cohort_cursor_leak",
    )
    adapter.call("backup")
    adapter.call("delete_account")
    adapter.call("restore")
    state = adapter.call("observe")
    require(
        state["raw_count"] == state["command_count"] == state["session_count"] == 0,
        "restore_resurrected_private_data",
    )
    require(
        state["score_count"] == 1 and state["display_name"] == "Deleted player",
        "account_anonymization",
    )
    require(state["published_count"] == 1 and state["namespace_reserved"], "shared_pack_deleted")
    require(adapter.call("retry", {"variant": "exact"})["status"] == 401, "deleted_account_access")
    return {"probe": "ownership-retry-deletion-cohort-restore", "passed": True}
