"""Run with an isolated installed interpreter: python -I installed_smoke.py."""

import json
import subprocess
import sys
import tempfile
from contextlib import closing
from importlib import import_module
from importlib.metadata import version
from importlib.resources import files
from pathlib import Path

from semaphore_core.verification import load as core_resource
from semaphore_hub.contracts import SCHEMAS, load, validator
from semaphore_hub.storage import connect, migrate


def main():
    imports = {}
    for name in (
        "semaphore_core",
        "semaphore_hub",
        "semaphore_hub.durable_host",
        "semaphore_hub.browser_assets",
        "semaphore_hub.operations.readiness",
        "semaphore_hub.runtime",
    ):
        path = Path(import_module(name).__file__).resolve()
        if not path.is_relative_to(Path(sys.prefix).resolve()):
            raise RuntimeError(f"{name} was imported from outside the installed environment")
        imports[name] = str(path)
    for name in SCHEMAS:
        validator(document=name).check_schema(load(name))
    assert load("durable-openapi.json")["openapi"]
    assert core_resource("model-lock.json")["fingerprint_sha256"]
    migrations = sorted(
        p.name for p in files("semaphore_hub.migrations").iterdir() if p.name.endswith(".sql")
    )
    with tempfile.TemporaryDirectory(prefix="semaphore-installed-") as temp:
        database = Path(temp) / "hub.db"
        with closing(connect(database)) as db:
            schema = migrate(db)
            assert schema == 2 and migrate(db) == schema
            assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        for args in (
            ["--smoke"],
            [str(database), "migrate"],
            [str(database), "serve-durable", "--help"],
        ):
            result = subprocess.run(
                [sys.executable, "-I", "-m", "semaphore_hub", *args],
                cwd=temp,
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )
            assert result.stdout
            if args[-1] == "--help":
                assert "--web-root" in result.stdout
    print(
        json.dumps(
            {
                "python": sys.version.split()[0],
                "package": version("semaphore-core"),
                "imports": imports,
                "migrations": migrations,
                "schema": schema,
                "schemas": list(SCHEMAS),
                "cli": ["smoke", "migrate", "serve-durable --help"],
                "model_calls": 0,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
