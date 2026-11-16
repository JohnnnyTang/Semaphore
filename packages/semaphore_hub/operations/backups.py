"""Bounded authenticated SQLite backups; keys and deletion ledger stay external."""

import base64
import json
import os
import sqlite3
import uuid
from contextlib import closing
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from semaphore_hub.policy import BACKUP_RETENTION_MS
from semaphore_hub.storage import connect

from .ledger import canonical

MAX_BACKUP_BYTES = 256 * 1024 * 1024


class EncryptedBackups:
    def __init__(self, root, key):
        if not isinstance(key, bytes) or len(key) != 32:
            raise ValueError("external 32-byte backup key required")
        self.root = Path(root).absolute()
        self.root.mkdir(parents=True, exist_ok=True)
        self.cipher = AESGCM(key)
        self._safe(self.root)

    @staticmethod
    def _safe(path):
        for candidate in (path, *path.parents):
            if candidate.is_symlink() or candidate.is_junction():
                raise ValueError("unsafe backup path")

    def create(self, database, now_ms):
        if type(now_ms) is not int or now_ms < 0:
            raise ValueError("invalid backup time")
        self.rotate(now_ms)
        self._safe(self.root)
        with closing(connect(database)) as source, closing(sqlite3.connect(":memory:")) as snapshot:
            size = (
                source.execute("PRAGMA page_count").fetchone()[0]
                * source.execute("PRAGMA page_size").fetchone()[0]
            )
            if size > MAX_BACKUP_BYTES:
                raise ValueError("backup size limit")
            source.backup(snapshot)
            raw = snapshot.serialize()
        if len(raw) > MAX_BACKUP_BYTES:
            raise ValueError("backup size limit")
        header = dict(version=1, created_at=now_ms, expires_at=now_ms + BACKUP_RETENTION_MS)
        nonce = os.urandom(12)
        encrypted = self.cipher.encrypt(nonce, raw, canonical(header))
        envelope = dict(
            header=header,
            nonce=base64.b64encode(nonce).decode(),
            ciphertext=base64.b64encode(encrypted).decode(),
        )
        path = self.root / (uuid.uuid4().hex + ".backup")
        temporary = path.with_suffix(".staging")
        try:
            with temporary.open("xb") as output:
                output.write(canonical(envelope))
                output.flush()
                os.fsync(output.fileno())
            os.rename(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
        return path

    def _open(self, path):
        path = Path(path)
        self._safe(path)
        if path.stat().st_size > 2 * MAX_BACKUP_BYTES:
            raise ValueError("backup size limit")
        envelope = json.loads(path.read_bytes())
        header = envelope["header"]
        raw = self.cipher.decrypt(
            base64.b64decode(envelope["nonce"], validate=True),
            base64.b64decode(envelope["ciphertext"], validate=True),
            canonical(header),
        )
        if (
            header.get("version") != 1
            or type(header.get("created_at")) is not int
            or header["created_at"] < 0
            or header.get("expires_at") != header["created_at"] + BACKUP_RETENTION_MS
        ):
            raise ValueError("invalid backup metadata")
        return header, raw

    def rotate(self, now_ms):
        self._safe(self.root)
        for path in self.root.glob("*.backup"):
            header, _ = self._open(path)
            if header["expires_at"] <= now_ms:
                path.unlink()

    def prepare_restore(self, backup, destination, now_ms, recover):
        """recover(temp_path) must replay external ledger, expire, validate keys,
        interrupt and validate retained immutable asset availability before returning.
        Never serve the temporary DB; any exception leaves destination unpublished.
        """
        destination = Path(destination).absolute()
        self._safe(destination)
        if destination.exists():
            raise FileExistsError(destination)
        header, raw = self._open(backup)
        if not header["created_at"] <= now_ms < header["expires_at"]:
            raise ValueError("backup expired or future dated")
        temporary = destination.with_name(destination.name + "." + uuid.uuid4().hex + ".restoring")
        try:
            with closing(sqlite3.connect(":memory:")) as source:
                source.deserialize(raw)
                with closing(connect(temporary)) as target:
                    source.backup(target)
                    if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                        raise ValueError("backup integrity check")
            recover(temporary)
            with closing(connect(temporary)) as checked:
                if checked.execute("PRAGMA foreign_key_check").fetchone() is not None:
                    raise ValueError("backup foreign key check")
                checked.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                checked.execute("PRAGMA journal_mode=DELETE")
            with temporary.open("r+b") as ready:
                os.fsync(ready.fileno())
            self._safe(destination)
            if destination.exists():
                raise FileExistsError(destination)
            os.rename(temporary, destination)
        finally:
            # Recovery may select WAL or fail with journal files still present.
            # These exact generated paths belong to this restore only. Never
            # suppress cleanup errors: an open Windows handle requires operator
            # attention and must not be reported as a clean failed restore.
            for suffix in ("-wal", "-shm", "-journal", ""):
                Path(str(temporary) + suffix).unlink(missing_ok=True)
        return destination
