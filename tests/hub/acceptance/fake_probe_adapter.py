"""Deliberately fake oracle self-check only; NEVER service acceptance evidence."""

import json


class Fake:
    def __init__(self, root, checkpoint):
        self.root, self.checkpoint = root, checkpoint
        self.path = root / "fake-state.json"
        self.state = json.loads(self.path.read_text()) if self.path.exists() else {}
        self.fault = (root / "fault.txt").read_text() if (root / "fault.txt").exists() else ""

    def save(self):
        temporary = self.root / "fake-state.tmp"
        temporary.write_text(json.dumps(self.state))
        temporary.replace(self.path)

    def execute(self, operation, payload):
        s = self.state
        if operation == "fixture_setup":
            phase = payload["phase"]
            self.state = dict(
                status="active",
                pending_count=int(phase == "completion"),
                command_count=int(phase in {"completion", "terminal"}),
                score_count=0,
                end_reason=None,
                receipt_outcome="completed" if phase == "terminal" else "pending",
                raw_count=1,
                inference_calls=1,
                session_count=1,
                display_name="Player",
                published_count=1,
                namespace_reserved=True,
            )
        elif operation in {"admission", "completion", "terminal"}:
            if self.fault == "commit_before_hook":
                s["command_count"] = 1
                self.save()
            self.checkpoint(f"{operation}.before_commit")
            if operation == "admission":
                s.update(command_count=1, pending_count=1, receipt_outcome="pending")
            elif operation == "completion":
                s.update(pending_count=0, receipt_outcome="completed")
            else:
                s.update(status="over", end_reason="pack_cleared", score_count=1)
            self.save()
            self.checkpoint(f"{operation}.after_commit")
        elif operation == "recover":
            if s["status"] == "active":
                s.update(status="over", end_reason="interrupted")
                if s["pending_count"]:
                    s.update(pending_count=0, receipt_outcome="game_over")
            if self.fault == "recovery_scores":
                s["score_count"] = 1
        elif operation == "observe":
            return s
        elif operation == "retry":
            if not s["session_count"]:
                return {"status": 401}
            if self.fault == "retry_inference":
                s["inference_calls"] += 1
                self.save()
            if payload["variant"] != "exact" and self.fault != "changed_retry":
                return {"status": 409}
            return {"status": 200, "receipt": {"id": "synthetic", "outcome": "completed"}}
        elif operation == "foreign_receipt":
            return {"status": 200 if self.fault == "foreign_access" else 404}
        elif operation == "delete_clues":
            if self.fault != "retain_clues":
                s["raw_count"] = 0
        elif operation == "board":
            if payload["cohort"] == "other":
                return {"status": 200 if self.fault == "cohort_leak" else 400}
            second = bool(payload.get("cursor")) and self.fault != "tie_skip"
            return {
                "items": ["tie-b" if second else "tie-a"],
                "next_cursor": None if second else "bound",
            }
        elif operation == "backup":
            (self.root / "fake-backup.json").write_text(json.dumps(s))
        elif operation == "delete_account":
            (self.root / "fake-ledger.json").write_text('{"deleted":true}')
            s.update(raw_count=0, command_count=0, session_count=0, display_name="Deleted player")
        elif operation == "restore":
            self.state = json.loads((self.root / "fake-backup.json").read_text())
            if self.fault != "ledger_ignored" and (self.root / "fake-ledger.json").exists():
                self.state.update(
                    raw_count=0, command_count=0, session_count=0, display_name="Deleted player"
                )
        else:
            raise ValueError("unknown operation")
        self.save()
        return {"ready": True}


def open_adapter(workspace, checkpoint):
    return Fake(workspace, checkpoint)
