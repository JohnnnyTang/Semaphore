import hashlib
import json
from contextlib import closing

import pytest

from semaphore_hub.operations import validate_assets
from semaphore_hub.storage import connect, migrate


def test_asset_readiness_checks_bytes_paths_dimensions_and_missing_files(tmp_path):
    assets = tmp_path / "assets"
    assets.mkdir()
    manifest = b'{"entries": [{"id": "x"}]}'
    manifest_digest = hashlib.sha256(manifest).hexdigest()
    manifest_file = assets / (manifest_digest + ".manifest")
    manifest_file.write_bytes(manifest)
    vectors = json.dumps([[1.0, 0.0]]).encode()
    vector_digest = hashlib.sha256(vectors).hexdigest()
    vector_file = assets / (vector_digest + ".vectors")
    vector_file.write_bytes(vectors)
    with closing(connect(tmp_path / "db.sqlite")) as db:
        migrate(db)
        db.execute("INSERT INTO accounts VALUES ('a','alice','Alice','hash',1,0,NULL)")
        db.execute("INSERT INTO packs VALUES ('p','a',0,NULL)")
        db.execute(
            "INSERT INTO pack_versions VALUES ('v','p','1',?,?,'s','v',0)",
            (manifest, manifest_digest),
        )
        db.execute(
            "INSERT INTO vector_caches VALUES ('v','f',?,?,2,1)",
            (vector_digest, str(vector_file)),
        )
        assert validate_assets(db, assets) == {manifest_file.name, vector_file.name}
        vector_file.write_bytes(b"tampered")
        with pytest.raises(ValueError, match="digest mismatch"):
            validate_assets(db, assets)
        vector_file.write_bytes(vectors)
        manifest_file.unlink()
        with pytest.raises(ValueError, match="missing or unsafe"):
            validate_assets(db, assets)
        manifest_file.write_bytes(manifest)
        db.execute("DELETE FROM vector_caches")
        db.execute(
            "INSERT INTO vector_caches VALUES ('v','f',?,?,3,1)",
            (vector_digest, str(vector_file)),
        )
        with pytest.raises(ValueError, match="invalid immutable vectors"):
            validate_assets(db, assets)
        db.execute("DELETE FROM vector_caches")
        db.execute(
            "INSERT INTO vector_caches VALUES ('v','f',?,?,2,1)",
            (vector_digest, str(tmp_path / vector_file.name)),
        )
        with pytest.raises(ValueError, match="outside configured root"):
            validate_assets(db, assets)
