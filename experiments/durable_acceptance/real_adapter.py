"""Real SQLite/service probe adapter; synthetic installation/inference only.

Fault hooks wrap actual transaction commits, selected by observed SQL changes.
No reducer, recovery, receipt, deletion, board, or backup behavior is substituted.
"""

import base64
import json
from contextlib import closing, contextmanager
from pathlib import Path
from unittest.mock import patch

from semaphore_core.verification import load, manifest_hashes
from semaphore_hub.application import Application
from semaphore_hub.auth.service import AuthError, AuthService, digest, encoded
from semaphore_hub.games import GameService
from semaphore_hub.operations import EncryptedBackups, ExternalLedger, Operations
from semaphore_hub.packs import PackService
from semaphore_hub.results import ResultsService
from semaphore_hub.runtime import FileCommandKeys, StripedGameLocks
from semaphore_hub.runtime_testing import ManualInference
from semaphore_hub.storage import connect, migrate, transaction


class Clock:
    now = 0

    def utc_ms(self):
        return 1_800_000_000_000 + self.now

    def monotonic_ms(self):
        return self.now


class RealAdapter:
    def __init__(self, root, checkpoint):
        self.root, self.checkpoint = root, checkpoint
        self.meta_path = root / "fixture.json"
        self.meta = json.loads(self.meta_path.read_text()) if self.meta_path.exists() else {}
        self.path = Path(self.meta.get("database", root / "hub.db"))
        self.phase = None
        self.clock = Clock()
        self.clock.now = self.meta.get("now", 0)
        if self.meta:
            self.compose()

    def save(self):
        self.meta.update(database=str(self.path), now=self.clock.now)
        self.meta_path.write_text(json.dumps(self.meta))

    @staticmethod
    def signature(db):
        return (
            db.execute("SELECT count(*) FROM commands").fetchone()[0],
            db.execute("SELECT count(*) FROM commands WHERE state='final'").fetchone()[0],
            db.execute("SELECT count(*) FROM games WHERE status='over'").fetchone()[0],
        )

    @contextmanager
    def tx(self):
        with closing(connect(self.path)) as db:
            before = self.signature(db) if self.phase else None
            with transaction(db):
                yield db
                after = self.signature(db) if self.phase else None
                index = {"admission": 0, "completion": 1, "terminal": 2}.get(self.phase)
                fault = index is not None and after[index] > before[index]
                if fault:
                    self.checkpoint(self.phase + ".before_commit")
            if fault:
                self.checkpoint(self.phase + ".after_commit")

    def compose(self):
        self.keys = FileCommandKeys(self.root / "keys.json")
        self.locks = StripedGameLocks()
        adapter = self

        class CountingInference(ManualInference):
            def submit(self, request, complete):
                adapter.meta["inference_calls"] += 1
                adapter.save()
                return super().submit(request, complete)

        self.inference = CountingInference()
        self.packs = PackService(self.tx, self.root / "assets", None)
        self.games = GameService(self.tx, self.inference, self.keys, self.locks, clock=self.clock)
        self.ledger = ExternalLedger(self.root / "ledger.jsonl", b"l" * 32)
        self.backups = EncryptedBackups(self.root / "backups", b"b" * 32)
        self.ops = Operations(
            self.tx,
            self.locks,
            self.games,
            self.keys,
            self.ledger,
            self.packs.clean_orphan_assets,
            self.clock,
            self.backups.rotate,
        )
        self.auth = AuthService(self.tx, None, b"c" * 32, self.clock)

    def fixture(self, phase):
        with closing(connect(self.path)) as db:
            migrate(db)
            with transaction(db):
                for ident, operator in (("owner", 0), ("other", 0), ("admin", 1)):
                    db.execute(
                        "INSERT INTO accounts VALUES (?,?,?,?,?,0,NULL)",
                        (ident, ident, ident, "unused", operator),
                    )
                now = self.clock.utc_ms()
                token = encoded(b"s" * 32)
                db.execute(
                    "INSERT INTO sessions VALUES (?,?,?,?,?,?,?)",
                    ("session", "owner", digest(token), digest(token), now, now, now + 86400000),
                )
        (self.root / "keys.json").write_text(
            json.dumps(
                {"active": "probe-v1", "keys": {"probe-v1": base64.b64encode(b"k" * 32).decode()}}
            )
        )
        ExternalLedger(self.root / "ledger.jsonl", b"l" * 32, create=True)
        self.compose()
        with self.tx() as db:
            db.execute("UPDATE sessions SET csrf_digest=?", (digest(self.auth.csrf(token)),))

        def measured(value, embedder, ruleset):
            hashes = manifest_hashes(value)
            target = min(e["id"] for e in value.manifest["entries"][:5])
            embedder.entry_vectors = [
                [-1.0 if e["id"] == target else 1.0] + [0.0] * 2559
                for e in value.manifest["entries"]
            ]
            return dict(
                manifest_digest=hashes.manifest_digest,
                semantic_hash=hashes.semantic_hash,
                vector_hash=hashes.vector_hash,
                fingerprint_hash=load("model-lock.json")["fingerprint_sha256"],
                protocol_hash="a" * 64,
                ruleset_id=ruleset,
                status="measured",
                metrics=dict(reachability=1.0),
            )

        manifest = json.loads(Path("packs/everyday.json").read_bytes())
        manifest["pack"]["tags"] = []
        with patch("semaphore_hub.packs.service.verify_pack", measured):
            published = self.packs.install(
                json.dumps(manifest).encode(),
                owner_id="owner",
                operator_id="admin",
                rights_reference="synthetic probe only",
                accept=True,
            )
        entries = [json.loads(row)["id"] for row in published.entries_json]
        args = (published.installation.pack_id, published.installation.version)
        accepted = self.packs.accept_casual_artifact(
            *args, operator_id="admin", initial_board=entries[:5], schedule=[]
        )
        other = self.packs.accept_casual_artifact(
            *args, operator_id="admin", initial_board=entries[1:6], schedule=[]
        )
        self.meta.update(artifact=accepted.artifact_id, other=other.artifact_id, inference_calls=0)
        self.meta["gid"] = self.games.create(
            "owner", dict(mode="casual", artifact_id=accepted.artifact_id)
        )["snapshot"]["game_id"]
        self.save()
        if phase in ("completion", "terminal"):
            self.execute("admission", {})
        if phase == "terminal":
            self.execute("completion", {})

    def command(self, variant="exact"):
        payload = dict(
            command_id="probe-command", expected_revision=0, clue="mysterious association"
        )
        if variant == "clue_case":
            payload["clue"] = payload["clue"].upper()
        elif variant == "clue_whitespace":
            payload["clue"] += " "
        elif variant == "expected_revision":
            payload["expected_revision"] = 1
        return payload

    def recover(self):
        with closing(connect(self.path)) as db:
            app = Application(db, self.clock, self.ops)
            app.start()
            return {"ready": app.ready}

    def observe(self):
        with self.tx() as db:
            gid = self.meta["gid"]
            status, reason = db.execute(
                "SELECT status,end_reason FROM games WHERE game_id=?", (gid,)
            ).fetchone()
            rows = db.execute(
                "SELECT state,receipt_json FROM commands WHERE game_id=?", (gid,)
            ).fetchall()
            score = db.execute("SELECT display_name FROM scores WHERE game_id=?", (gid,)).fetchall()
            return dict(
                status=status,
                end_reason=reason,
                command_count=len(rows),
                pending_count=sum(row[0] == "pending" for row in rows),
                receipt_outcome=json.loads(rows[0][1])["outcome"] if rows else None,
                score_count=len(score),
                display_name=(score[0][0] or "Deleted player") if score else None,
                raw_count=db.execute(
                    "SELECT count(*) FROM clue_attempts WHERE raw_clue IS NOT NULL"
                ).fetchone()[0],
                session_count=db.execute("SELECT count(*) FROM sessions").fetchone()[0],
                published_count=db.execute("SELECT count(*) FROM published_versions").fetchone()[0],
                namespace_reserved=bool(db.execute("SELECT count(*) FROM packs").fetchone()[0]),
                inference_calls=self.meta["inference_calls"],
            )

    def execute(self, operation, payload):
        if operation == "fixture_setup":
            self.fixture(payload["phase"])
            return {"ready": True}
        gid = self.meta["gid"]
        if operation in {"admission", "completion", "terminal"}:
            self.phase = operation
            try:
                if operation == "admission":
                    self.games.command("owner", gid, self.command())
                elif operation == "completion":
                    self.inference.finish(gid, "probe-command", tuple([1.0] + [0.0] * 2559))
                else:
                    self.clock.now += 5000
                    self.games.tick()
            finally:
                self.phase = None
            self.save()
        elif operation == "recover":
            return self.recover()
        elif operation == "observe":
            return self.observe()
        elif operation == "retry":
            try:
                self.auth.authenticate(encoded(b"s" * 32))
            except AuthError as exc:
                return {"status": exc.status}
            envelope = self.games.command("owner", gid, self.command(payload["variant"]))
            return {"status": 200, "receipt": envelope["receipt"]}
        elif operation == "foreign_receipt":
            try:
                self.games.receipt(
                    "other", gid, "probe-command" if payload["known_command"] else "unknown"
                )
            except LookupError:
                return {"status": 404}
            return {"status": 200}
        elif operation == "delete_clues":
            self.ops.delete_clues("owner")
        elif operation == "board":
            if not self.meta.get("ties"):
                # Real reducer creates two equal terminal records in a separate cohort.
                for ident in ("tie-a", "tie-b"):
                    with patch("semaphore_hub.games.service.secrets.token_hex", return_value=ident):
                        self.games.create(
                            "other", dict(mode="casual", artifact_id=self.meta["other"])
                        )
                    self.clock.now += 5000
                    self.games.tick()
                    self.clock.now -= 5000
                self.meta["ties"] = True
                self.save()
            artifact = (
                self.meta["other"] if payload["cohort"] == "accepted" else self.meta["artifact"]
            )
            try:
                result = ResultsService(self.tx).board(
                    artifact, payload.get("cursor"), payload.get("limit", 20)
                )
            except ValueError:
                return {"status": 400}
            return {
                "items": [row["game_id"] for row in result["items"]],
                "next_cursor": result["next_cursor"],
            }
        elif operation == "backup":
            self.meta["backup"] = str(self.backups.create(self.path, self.clock.utc_ms()))
            self.save()
        elif operation == "delete_account":
            self.ops.delete_account("owner")
        elif operation == "restore":

            def recovery(path):
                self.path = path
                self.compose()
                self.recover()

            self.path = self.backups.prepare_restore(
                self.meta["backup"], self.root / "restored.db", self.clock.utc_ms(), recovery
            )
            self.compose()
            self.save()
        else:
            raise ValueError("unknown operation")
        return {"ready": True}


def open_adapter(workspace, checkpoint):
    return RealAdapter(workspace, checkpoint)
