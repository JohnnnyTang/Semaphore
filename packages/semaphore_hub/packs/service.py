"""Host-only bounded installation and public installed-pack projections.

The host supplies a real locked embedder. No caller report, remote URL or vector
file is accepted. Authentication/Host validation wraps read handlers at composition.
"""

import base64
import hashlib
import json
import os
import re
import stat
import threading
import time
import uuid
from pathlib import Path

from semaphore_core.verification import load, manifest_hashes, parse_manifest, vector, verify_pack
from semaphore_hub.policy import INSTALL_DEADLINE_MS
from semaphore_hub.repositories import Conflict, Installation, NotFound, Publication, VectorCache

from .repository import SQLitePacks

_INSTALL_LOCK = threading.Lock()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class DeadlineEmbedder:
    def __init__(self, inner, check):
        self.inner, self.check = inner, check
        self.entry_vectors = None

    def identity(self):
        self.check()
        value = self.inner.identity()
        self.check()
        return value

    def embed_entries(self, texts):
        self.check()
        value = self.inner.embed_entries(texts)
        self.entry_vectors = [vector(row) for row in value]
        self.check()
        return value

    def embed_queries(self, texts):
        self.check()
        value = self.inner.embed_queries(texts)
        self.check()
        return value


class PackService:
    def __init__(self, transactions, asset_root, embedder, *, now_ms=None, monotonic=None):
        self.transactions = transactions
        self.root = Path(asset_root).absolute()
        self.embedder = embedder
        self.now_ms = now_ms or (lambda: time.time_ns() // 1_000_000)
        self.monotonic = monotonic or (lambda: time.monotonic_ns() // 1_000_000)
        self.root.mkdir(parents=True, exist_ok=True)
        self._safe_root()

    def _safe_root(self):
        for path in (self.root, *self.root.parents):
            info = path.lstat()
            if (
                path.is_symlink()
                or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
            ):
                raise ValueError("unsafe asset root")

    @staticmethod
    def _authority(db, owner_id, operator_id):
        if not db.execute(
            "SELECT 1 FROM accounts WHERE account_id=? AND deleted_at IS NULL", (owner_id,)
        ).fetchone():
            raise NotFound("owner")
        if not db.execute(
            "SELECT 1 FROM accounts WHERE account_id=? AND is_operator=1 AND deleted_at IS NULL",
            (operator_id,),
        ).fetchone():
            raise PermissionError("operator required")

    def install(
        self,
        raw,
        *,
        owner_id,
        operator_id,
        rights_reference,
        accept,
        ruleset_id="experiment-arcade-paced-v1",
    ):
        if (
            accept is not True
            or not isinstance(rights_reference, str)
            or not rights_reference.strip()
        ):
            raise ValueError("explicit rights acceptance required")
        value = parse_manifest(raw)
        entries = value.manifest["entries"]
        clues = value.manifest["test_set"]
        if (
            not 40 <= len(entries) <= 500
            or any(len(c) > 5 for c in clues.values())
            or sum(map(len, clues.values())) > 2500
        ):
            raise ValueError("installation budget")
        # Synthetic/tutorial fixtures are never published by the operator path.
        tags = value.manifest["pack"].get("tags", [])
        if any(t.casefold() in {"synthetic", "practice", "test", "tutorial"} for t in tags):
            raise ValueError("noncompetitive content")
        hashes = manifest_hashes(value)
        pack = value.manifest["pack"]
        item = Installation(
            uuid.uuid4().hex, owner_id, pack["id"], pack["version"], hashes.manifest_digest
        )
        if not _INSTALL_LOCK.acquire(blocking=False):
            raise Conflict("installer busy")
        reserved = False
        try:
            with self.transactions() as db:
                self._authority(db, owner_id, operator_id)
                repo = SQLitePacks(db)
                actual = repo.reserve(item)
                try:
                    prior = repo.published(item.pack_id, item.version)
                except NotFound:
                    prior = None
                if prior is not None:
                    if prior.manifest_bytes != raw:
                        raise Conflict("version bytes conflict")
                    return prior
                if actual != item:
                    raise Conflict("installation pending recovery")
            reserved = True
            start = self.monotonic()

            def check():
                if self.monotonic() - start >= INSTALL_DEADLINE_MS:
                    raise TimeoutError("verification deadline")

            recording = DeadlineEmbedder(self.embedder, check)
            report = verify_pack(value, recording, ruleset_id)
            check()
            if report["metrics"]["reachability"] < float(
                load("verification-policy.json")["thresholds"]["reachability"]
            ):
                raise ValueError("verification threshold")
            for name in ("manifest_digest", "semantic_hash", "vector_hash"):
                if report[name] != getattr(hashes, name):
                    raise ValueError("report pin mismatch")
            # Preserve measured authority verbatim; publication is a separate explicit decision.
            publication = Publication(
                uuid.uuid4().hex,
                item,
                raw,
                hashes.semantic_hash,
                hashes.vector_hash,
                tuple(json.dumps(e, ensure_ascii=False) for e in entries),
                uuid.uuid4().hex,
                json.dumps(report, ensure_ascii=False, allow_nan=False),
                report["fingerprint_hash"],
                report["protocol_hash"],
                ruleset_id,
                operator_id,
                rights_reference,
                self.now_ms(),
            )
            self._stage(item.manifest_digest, raw)
            if recording.entry_vectors is None or len(recording.entry_vectors) != len(entries):
                raise ValueError("missing verified vectors")
            vectors_raw = json.dumps(
                recording.entry_vectors, separators=(",", ":"), allow_nan=False
            ).encode()
            vectors_digest = digest(vectors_raw)
            self._stage(vectors_digest, vectors_raw, extension="vectors")
            cache = VectorCache(
                hashes.vector_hash,
                report["fingerprint_hash"],
                vectors_digest,
                str(self.root / (vectors_digest + ".vectors")),
                2560,
                len(entries),
            )
            check()
            with self.transactions() as db:
                self._authority(db, owner_id, operator_id)
                repo = SQLitePacks(db)
                repo.put_vectors(cache)
                result = repo.publish(publication)
            return result
        except BaseException:
            if reserved:
                with self.transactions() as db:
                    try:
                        SQLitePacks(db).release(item.install_id, owner_id)
                    except NotFound:
                        pass
            raise
        finally:
            _INSTALL_LOCK.release()

    def _stage(self, key, raw, *, extension="manifest"):
        self._safe_root()
        target = self.root / (key + "." + extension)
        temporary = self.root / (uuid.uuid4().hex + ".staging")
        if target.exists() or target.is_symlink():
            if target.is_symlink() or target.is_junction() or digest(target.read_bytes()) != key:
                raise Conflict("asset conflict")
            return
        try:
            with temporary.open("xb") as out:
                out.write(raw)
                out.flush()
                os.fsync(out.fileno())
            if digest(temporary.read_bytes()) != key:
                raise ValueError("asset digest")
            self._safe_root()
            os.rename(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)

    def clean_orphan_assets(self):
        """Pre-traffic recovery only; serialized with installations in this process."""
        with _INSTALL_LOCK:
            self._safe_root()
            with self.transactions() as db:
                live = {
                    r[0] + ".manifest"
                    for r in db.execute(
                        "SELECT manifest_digest FROM pack_versions JOIN published_versions "
                        "USING(version_id)"
                    )
                }
                live.update(
                    r[0] + ".vectors"
                    for r in db.execute("SELECT ordered_vectors_digest FROM vector_caches")
                )
                db.execute(
                    "UPDATE install_reservations SET state='failed',finished_at=? WHERE "
                    "state='pending'",
                    (self.now_ms(),),
                )
            for path in self.root.iterdir():
                if (
                    re.fullmatch(
                        r"(?:[a-f0-9]{32}\.staging|[a-f0-9]{64}\.(?:manifest|vectors))", path.name
                    )
                    and path.name not in live
                ):
                    if path.is_symlink() or path.is_junction():
                        raise ValueError("unsafe asset")
                    path.unlink()

    @staticmethod
    def _project(repo, p):
        artifacts = repo.artifacts_for_version(p.version_id)
        if len(artifacts) > 100:
            raise ValueError("artifact listing exceeds contract")
        return dict(
            pack_id=p.installation.pack_id,
            version=p.installation.version,
            title=json.loads(p.manifest_bytes)["pack"]["name"],
            manifest_digest=p.installation.manifest_digest,
            artifacts=[
                dict(
                    artifact_id=a.artifact_id,
                    cohort=dict(
                        mode=a.mode,
                        pack_id=p.installation.pack_id,
                        version=p.installation.version,
                        manifest_digest=p.installation.manifest_digest,
                        fingerprint_hash=a.fingerprint_hash,
                        ruleset_id=a.ruleset_id,
                        config_digest=a.config_digest,
                        challenge_digest=a.challenge_digest,
                    ),
                )
                for a in artifacts
            ],
        )

    def get_pack(self, pack_id, version):
        with self.transactions() as db:
            repo = SQLitePacks(db)
            return self._project(repo, repo.published(pack_id, version))

    def list_packs(self, cursor=None, limit=20):
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("invalid limit")
        anchor = None
        if cursor is not None:
            if not isinstance(cursor, str) or not re.fullmatch("[A-Za-z0-9_-]{1,200}", cursor):
                raise ValueError("invalid cursor")
            try:
                anchor = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode("ascii")
            except (ValueError, UnicodeError):
                raise ValueError("invalid cursor") from None
            if not re.fullmatch("[a-f0-9]{32}", anchor):
                raise ValueError("invalid cursor")
        with self.transactions() as db:
            repo = SQLitePacks(db)
            try:
                rows = repo.list_published(anchor, limit)
            except NotFound:
                raise ValueError("invalid cursor") from None
            more = bool(rows and repo.list_published(rows[-1].version_id, 1))
            next_cursor = (
                base64.urlsafe_b64encode(rows[-1].version_id.encode()).decode().rstrip("=")
                if more
                else None
            )
            return dict(items=[self._project(repo, p) for p in rows], next_cursor=next_cursor)

    def accept_casual_artifact(
        self,
        pack_id,
        version,
        *,
        operator_id,
        initial_board,
        schedule,
        seed=None,
        generator_policy=None,
    ):
        """Host-only acceptance of a fully pinned bounded casual round."""
        from semaphore_core.game import GameArtifact, thaw
        from semaphore_core.verification import canonical
        from semaphore_hub.repositories import Artifact

        with self.transactions() as db:
            repo = SQLitePacks(db)
            p = repo.published(pack_id, version)
            self._authority(db, p.installation.owner_id, operator_id)
        if p.ruleset_id != "experiment-arcade-paced-v1":
            raise ValueError("casual ruleset")
        deadline = (schedule[-1]["at_ms"] if schedule else 0) + 5000
        config = dict(
            initial_board=list(initial_board),
            schedule=list(schedule),
            seed=seed,
            generator_policy=generator_policy,
            deadline_ms=deadline,
            capacity=20,
            zone_size=3,
            score_pacing=True,
            initial_score=0,
            initial_clears=0,
            mode="casual",
            special_clear=dict(
                streak=5, refill="scheduled_to_five_after_scoring", cascade="legal_target_in_zone"
            ),
            pacing=dict(points_per_level=500, interval_step_percent=10, minimum_percent=40),
        )
        config_raw = canonical(config)
        identities = dict(
            pack_digest=p.installation.manifest_digest,
            model_fingerprint=p.fingerprint_hash,
            ruleset_id=p.ruleset_id,
            config_digest=digest(config_raw),
            challenge_digest=None,
        )
        entries = [json.loads(e) for e in p.entries_json]
        game = GameArtifact(
            mode="casual",
            identities=identities,
            entries={
                e["id"]: dict(
                    label=e["text"],
                    aliases=e.get("aliases", []),
                    forbidden=e.get("forbidden_clues", []),
                )
                for e in entries
            },
            initial_board=tuple(initial_board),
            schedule=tuple(schedule),
            deadline_ms=deadline,
            capacity=20,
            score_pacing=True,
        )
        body = dict(
            mode=game.mode,
            identities=thaw(game.identities),
            entries=thaw(game.entries),
            initial_board=list(game.initial_board),
            schedule=thaw(game.schedule),
            deadline_ms=game.deadline_ms,
            capacity=20,
            zone_size=3,
            score_pacing=True,
            test_mode=False,
            initial_score=0,
            initial_clears=0,
        )
        raw = canonical(body)
        artifact = Artifact(
            uuid.uuid4().hex,
            p.version_id,
            p.report_id,
            "casual",
            p.fingerprint_hash,
            p.ruleset_id,
            digest(config_raw),
            config_raw.decode(),
            digest(raw),
            raw.decode(),
        )
        with self.transactions() as db:
            self._authority(db, p.installation.owner_id, operator_id)
            SQLitePacks(db).add_artifact(artifact)
        return artifact

    def get_artifact(self, artifact_id):
        with self.transactions() as db:
            repo = SQLitePacks(db)
            a = repo.artifact(artifact_id)
            row = db.execute(
                "SELECT pack_id,version FROM pack_versions WHERE version_id=?", (a.version_id,)
            ).fetchone()
            p = repo.published(*row)
            return next(
                item
                for item in self._project(repo, p)["artifacts"]
                if item["artifact_id"] == artifact_id
            )
