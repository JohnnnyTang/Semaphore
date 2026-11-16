"""One bounded real installation into a new ignored local directory; no listener."""

import argparse
import hashlib
import json
import secrets
from contextlib import closing
from pathlib import Path

from semaphore_core.embeddings import OllamaConfig, OllamaEmbedder, PinnedEmbedder
from semaphore_core.verification import load
from semaphore_hub.auth import AuthService
from semaphore_hub.foundation import FoundationDatabase
from semaphore_hub.packs import PackService
from semaphore_hub.policy import TransportPolicy
from semaphore_hub.storage import connect, migrate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data_root = Path(__file__).resolve().parents[2] / "data"
    args.output = args.output.resolve()
    if args.output == data_root or not args.output.is_relative_to(data_root):
        parser.error("output must be a new subdirectory of the ignored repository data directory")
    args.output.mkdir(parents=True, exist_ok=False)
    path = args.output / "hub.sqlite"
    with closing(connect(path)) as db:
        migrate(db)
    database = FoundationDatabase(path)
    auth = AuthService(
        database.transaction, TransportPolicy("http://localhost:8080"), secrets.token_bytes(32)
    )
    owner = auth.bootstrap(
        "installation_operator", "Installation operator", secrets.token_urlsafe(32)
    )
    config = OllamaConfig.from_env()
    provider = PinnedEmbedder(
        OllamaEmbedder(
            OllamaConfig(
                config.base_url,
                timeout_seconds=30,
                batch_size=16,
                expected_digest=load("model-lock.json")["fingerprint"]["digest"],
            )
        )
    )
    service = PackService(database.transaction, args.output / "assets", provider)
    raw = Path("packs/everyday.json").read_bytes()
    publication = service.install(
        raw,
        owner_id=owner,
        operator_id=owner,
        rights_reference=(
            "packs/README.md; repository LICENSE; original authored MIT content; "
            "bounded local W2 acceptance authorized November 16, 2026"
        ),
        accept=True,
    )
    entries = json.loads(raw)["entries"]
    ids = [e["id"] for e in entries[:18]]
    artifact = service.accept_casual_artifact(
        "everyday",
        "1.0.0",
        operator_id=owner,
        initial_board=ids[:6],
        schedule=[dict(at_ms=(n + 1) * 5000, entry_id=e) for n, e in enumerate(ids[6:])],
    )
    report = json.loads(publication.report_json)
    (args.output / "verification-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    retry = service.install(
        raw, owner_id=owner, operator_id=owner, rights_reference="packs/README.md", accept=True
    )
    assert retry == publication
    # Fresh service/connection proves committed visibility independent of installer objects.
    reopened = PackService(FoundationDatabase(path).transaction, args.output / "assets", provider)
    assert reopened.get_artifact(artifact.artifact_id)["artifact_id"] == artifact.artifact_id
    result = dict(
        manifest_sha256=hashlib.sha256(raw).hexdigest(),
        entries=len(entries),
        clues=sum(map(len, json.loads(raw)["test_set"].values())),
        artifact_id=artifact.artifact_id,
        report_id=publication.report_id,
        fingerprint_hash=publication.fingerprint_hash,
        protocol_hash=publication.protocol_hash,
        ruleset_id=publication.ruleset_id,
        config_digest=artifact.config_digest,
        artifact_digest=artifact.artifact_digest,
        metrics=report["metrics"],
        exact_retry=True,
        reopened_visibility=True,
    )
    (args.output / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
