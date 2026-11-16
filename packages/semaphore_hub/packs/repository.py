"""Transaction-scoped SQLite implementation of the frozen pack port."""

import json
import sqlite3
from dataclasses import astuple

from semaphore_hub.repositories import (
    Artifact,
    Conflict,
    Installation,
    NotFound,
    Publication,
    VectorCache,
)


class SQLitePacks:
    def __init__(self, connection):
        self.db = connection

    def row(self, sql, args=()):
        cursor = self.db.execute(sql, args)
        row = cursor.fetchone()
        return (
            None if row is None else dict(zip([c[0] for c in cursor.description], row, strict=True))
        )

    def reserve(self, item):
        owner = self.row("SELECT * FROM packs WHERE pack_id=?", (item.pack_id,))
        if owner and (owner["owner_id"] != item.owner_id or owner["retired_at"] is not None):
            raise Conflict("owner conflict")
        if not self.row(
            "SELECT account_id FROM accounts WHERE account_id=? AND deleted_at IS NULL",
            (item.owner_id,),
        ):
            raise NotFound("owner")
        try:
            prior = self.published(item.pack_id, item.version)
        except NotFound:
            prior = None
        if prior:
            if prior.installation.manifest_digest != item.manifest_digest:
                raise Conflict("version conflict")
            return prior.installation
        if not owner:
            self.db.execute("INSERT INTO packs VALUES (?,?,0,NULL)", (item.pack_id, item.owner_id))
        pending = self.row(
            "SELECT * FROM install_reservations WHERE pack_id=? AND version=? AND state='pending'",
            (item.pack_id, item.version),
        )
        if pending:
            if pending["manifest_digest"] != item.manifest_digest:
                raise Conflict("version conflict")
            return Installation(
                pending["install_id"],
                item.owner_id,
                item.pack_id,
                item.version,
                item.manifest_digest,
            )
        self.db.execute(
            "INSERT INTO install_reservations VALUES (?,?,?,?,'pending',0,NULL)",
            (item.install_id, item.pack_id, item.version, item.manifest_digest),
        )
        return item

    def release(self, install_id, owner_id):
        row = self.row(
            "SELECT i.* FROM install_reservations i JOIN packs p USING(pack_id) WHERE "
            "install_id=? AND owner_id=? AND state='pending'",
            (install_id, owner_id),
        )
        if row is None:
            raise NotFound("installation")
        self.db.execute(
            "UPDATE install_reservations SET state='failed',finished_at=0 WHERE install_id=?",
            (install_id,),
        )

    def publish(self, p):
        i = p.installation
        owner = self.row("SELECT owner_id,retired_at FROM packs WHERE pack_id=?", (i.pack_id,))
        if not owner or owner["owner_id"] != i.owner_id or owner["retired_at"] is not None:
            raise Conflict("owner conflict")
        try:
            old = self.published(i.pack_id, i.version)
        except NotFound:
            old = None
        if old:
            if old.manifest_bytes != p.manifest_bytes:
                raise Conflict("version conflict")
            return old
        reservation = self.row(
            "SELECT * FROM install_reservations WHERE install_id=? AND state='pending'",
            (i.install_id,),
        )
        if not reservation or any(
            reservation[k] != getattr(i, k) for k in ("pack_id", "version", "manifest_digest")
        ):
            raise Conflict("reservation missing")
        if not self.row(
            "SELECT account_id FROM accounts WHERE account_id=? AND deleted_at IS NULL AND "
            "is_operator=1",
            (p.accepted_by,),
        ):
            raise NotFound("operator")
        self.db.execute(
            "INSERT INTO pack_versions VALUES (?,?,?,?,?,?,?,?)",
            (
                p.version_id,
                i.pack_id,
                i.version,
                p.manifest_bytes,
                i.manifest_digest,
                p.semantic_hash,
                p.vector_hash,
                p.accepted_at,
            ),
        )
        for ordinal, entry in enumerate(p.entries_json):
            self.db.execute(
                "INSERT INTO pack_entries VALUES (?,?,?,?)",
                (p.version_id, ordinal, json.loads(entry)["id"], entry),
            )
        self.db.execute(
            "INSERT INTO verification_reports VALUES (?,?,?,?,?,?,?,1,1,?,?)",
            (
                p.report_id,
                p.version_id,
                i.manifest_digest,
                p.semantic_hash,
                p.fingerprint_hash,
                p.protocol_hash,
                p.ruleset_id,
                p.report_json,
                p.accepted_at,
            ),
        )
        self.db.execute(
            "INSERT INTO published_versions VALUES (?,?,?,?,?)",
            (p.version_id, p.report_id, p.accepted_by, p.rights_reference, p.accepted_at),
        )
        self.db.execute(
            "UPDATE install_reservations SET state='published',finished_at=? WHERE install_id=?",
            (p.accepted_at, i.install_id),
        )
        return p

    def published(self, pack_id, version):
        r = self.row(
            "SELECT "
            "v.*,p.owner_id,u.accepted_by,u.rights_reference,u.accepted_at,r.report_id,r.report_json,"
            "r.fingerprint_hash,r.protocol_hash,r.ruleset_id "
            "FROM pack_versions v JOIN packs p USING(pack_id) JOIN published_versions u "
            "USING(version_id) JOIN verification_reports r ON r.report_id=u.report_id WHERE "
            "v.pack_id=? AND v.version=?",
            (pack_id, version),
        )
        if r is None:
            raise NotFound("published version")
        install = self.row(
            "SELECT install_id FROM install_reservations WHERE pack_id=? AND version=? AND "
            "state='published'",
            (pack_id, version),
        )
        entries = tuple(
            x[0]
            for x in self.db.execute(
                "SELECT entry_json FROM pack_entries WHERE version_id=? ORDER BY ordinal",
                (r["version_id"],),
            )
        )
        return Publication(
            r["version_id"],
            Installation(
                install["install_id"], r["owner_id"], pack_id, version, r["manifest_digest"]
            ),
            r["manifest_bytes"],
            r["semantic_hash"],
            r["vector_hash"],
            entries,
            r["report_id"],
            r["report_json"],
            r["fingerprint_hash"],
            r["protocol_hash"],
            r["ruleset_id"],
            r["accepted_by"],
            r["rights_reference"],
            r["accepted_at"],
        )

    def list_published(self, after_version_id, limit):
        if not 1 <= limit <= 100:
            raise ValueError("limit")
        anchor = ("", "")
        if after_version_id is not None:
            row = self.row(
                "SELECT pack_id,version FROM pack_versions JOIN published_versions "
                "USING(version_id) WHERE version_id=?",
                (after_version_id,),
            )
            if row is None:
                raise NotFound("cursor version")
            anchor = (row["pack_id"], row["version"])
        return tuple(
            self.published(*row)
            for row in self.db.execute(
                "SELECT pack_id,version FROM pack_versions JOIN published_versions "
                "USING(version_id) WHERE (pack_id,version)>(?,?) ORDER BY pack_id COLLATE "
                "BINARY,version COLLATE BINARY LIMIT ?",
                (*anchor, limit),
            )
        )

    def add_artifact(self, artifact):
        if (
            self.db.execute(
                "SELECT count(*) FROM artifacts WHERE version_id=?", (artifact.version_id,)
            ).fetchone()[0]
            >= 100
        ):
            raise Conflict("artifact limit")
        try:
            self.db.execute(
                "INSERT INTO artifacts VALUES (?,?,?,?,?,?,?,?,?,?,?)", astuple(artifact)
            )
        except sqlite3.IntegrityError as exc:
            raise Conflict("artifact conflict") from exc

    def artifact(self, artifact_id):
        row = self.db.execute(
            "SELECT * FROM artifacts WHERE artifact_id=?", (artifact_id,)
        ).fetchone()
        if row is None:
            raise NotFound("artifact")
        return Artifact(*row)

    def artifacts_for_version(self, version_id):
        return tuple(
            Artifact(*row)
            for row in self.db.execute(
                "SELECT * FROM artifacts WHERE version_id=? ORDER BY artifact_id COLLATE BINARY",
                (version_id,),
            )
        )

    def put_vectors(self, cache):
        old = self.vectors(cache.vector_hash, cache.fingerprint_hash)
        if old is not None:
            if old != cache:
                raise Conflict("immutable cache")
            return
        self.db.execute("INSERT INTO vector_caches VALUES (?,?,?,?,?,?)", astuple(cache))

    def vectors(self, vector_hash, fingerprint_hash):
        row = self.db.execute(
            "SELECT * FROM vector_caches WHERE vector_hash=? AND fingerprint_hash=?",
            (vector_hash, fingerprint_hash),
        ).fetchone()
        return VectorCache(*row) if row else None
