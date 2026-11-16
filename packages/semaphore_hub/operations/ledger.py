"""Authenticated external deletion ledger; retained indefinitely, never backed out."""

import hashlib
import hmac
import json
import os
import threading
from dataclasses import asdict
from pathlib import Path

from semaphore_hub.policy import BACKUP_RETENTION_MS
from semaphore_hub.repositories import Deletion


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


class ExternalLedger:
    def __init__(self, path, key, *, create=False):
        if not isinstance(key, bytes) or len(key) != 32:
            raise ValueError("external 32-byte ledger key required")
        self.path, self.key = Path(path), key
        self.lock = threading.RLock()
        if create:
            with self.path.open("xb") as out:
                out.write(b"")
                out.flush()
                os.fsync(out.fileno())
        self.entries()

    def _rows(self):
        if self.path.is_symlink() or self.path.is_junction():
            raise ValueError("unsafe ledger")
        raw = self.path.read_bytes()
        if len(raw) > 16 * 1024 * 1024 or (raw and not raw.endswith(b"\n")):
            raise ValueError("invalid ledger")
        previous = "0" * 64
        rows = []
        for line in raw.splitlines():
            row = json.loads(line)
            item = Deletion(**row["deletion"])
            if (
                item.scope not in {"clues", "account"}
                or item.retain_until < item.requested_at + BACKUP_RETENTION_MS
            ):
                raise ValueError("invalid ledger retention")
            expected = hmac.new(
                self.key, bytes.fromhex(previous) + canonical(row["deletion"]), hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(expected, row["mac"]):
                raise ValueError("ledger authentication failed")
            rows.append(item)
            previous = expected
        return rows, previous

    def entries(self):
        with self.lock:
            return tuple(self._rows()[0])

    def append(self, deletion):
        with self.lock:
            rows, previous = self._rows()
            for row in rows:
                if row.deletion_id == deletion.deletion_id:
                    if row != deletion:
                        raise ValueError("deletion identity conflict")
                    return
            if (
                deletion.scope not in {"clues", "account"}
                or deletion.retain_until < deletion.requested_at + BACKUP_RETENTION_MS
            ):
                raise ValueError("invalid deletion")
            value = asdict(deletion)
            mac = hmac.new(
                self.key, bytes.fromhex(previous) + canonical(value), hashlib.sha256
            ).hexdigest()
            with self.path.open("ab") as out:
                out.write(canonical(dict(deletion=value, mac=mac)) + b"\n")
                out.flush()
                os.fsync(out.fileno())
