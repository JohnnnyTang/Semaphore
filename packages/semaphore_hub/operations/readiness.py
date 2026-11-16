"""Concrete immutable asset readiness for live and restored databases."""

import hashlib
import json
import math
import re
from pathlib import Path


def validate_assets(connection, asset_root):
    """Verify retained manifests, vector files and artifact pins; return file names.

    The same root is used by the host and restored database. Stored vector paths
    must name that root, so a moved deployment needs an explicit asset migration.
    No file is removed and no model call is made.
    """
    root = Path(asset_root).absolute()
    for candidate in (root, *root.parents):
        if candidate.is_symlink() or candidate.is_junction():
            raise ValueError("unsafe asset root")
    retained = set()

    def read(digest, extension):
        if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise ValueError("invalid asset digest")
        path = root / (digest + extension)
        if path.is_symlink() or path.is_junction() or not path.is_file():
            raise ValueError("missing or unsafe immutable asset")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError("immutable asset digest mismatch")
        retained.add(path.name)
        return raw

    for digest, manifest in connection.execute(
        "SELECT manifest_digest,manifest_bytes FROM pack_versions"
    ):
        if read(digest, ".manifest") != manifest:
            raise ValueError("immutable manifest mismatch")

    for digest, stored_path, dimensions, count in connection.execute(
        "SELECT ordered_vectors_digest,asset_path,dimensions,entry_count FROM vector_caches"
    ):
        expected = root / (digest + ".vectors")
        if Path(stored_path).absolute() != expected:
            raise ValueError("vector asset outside configured root")
        rows = json.loads(read(digest, ".vectors"))
        if not isinstance(rows, list) or len(rows) != count:
            raise ValueError("vector entry count mismatch")
        for row in rows:
            if (
                not isinstance(row, list)
                or len(row) != dimensions
                or any(type(value) not in (int, float) or not math.isfinite(value) for value in row)
            ):
                raise ValueError("invalid immutable vectors")

    if connection.execute(
        "SELECT 1 FROM published_versions p JOIN pack_versions v USING(version_id) "
        "JOIN verification_reports r ON r.report_id=p.report_id "
        "LEFT JOIN vector_caches c ON c.vector_hash=v.vector_hash "
        "AND c.fingerprint_hash=r.fingerprint_hash WHERE c.vector_hash IS NULL LIMIT 1"
    ).fetchone():
        raise ValueError("published version missing immutable vectors")

    for config, config_digest, artifact, artifact_digest in connection.execute(
        "SELECT config_json,config_digest,artifact_json,artifact_digest FROM artifacts"
    ):
        if (
            hashlib.sha256(config.encode()).hexdigest() != config_digest
            or hashlib.sha256(artifact.encode()).hexdigest() != artifact_digest
        ):
            raise ValueError("immutable artifact digest mismatch")
    if connection.execute(
        "SELECT 1 FROM games g LEFT JOIN artifacts a ON a.artifact_id=g.artifact_id "
        "WHERE a.artifact_id IS NULL LIMIT 1"
    ).fetchone():
        raise ValueError("game missing immutable artifact")
    return frozenset(retained)
