"""Collect pinned real-model parity and instrumented HTTP load on one configured origin."""

import argparse
import json
import platform
import subprocess
import sys
import threading
from datetime import UTC, datetime
from pathlib import Path

from experiments.acceptance.common import ROOT, digest
from experiments.acceptance.load import load_probe
from experiments.acceptance.parity import parity
from experiments.game_server.__main__ import make_server
from experiments.game_server.artifacts import prepare_artifact
from experiments.game_server.service import GameService

from semaphore_core.embeddings import OllamaConfig, OllamaEmbedder, PinnedEmbedder, fingerprint_hash
from semaphore_core.game import thaw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--rounds", type=int, default=20)
    args = parser.parse_args()
    if args.rounds < 1:
        parser.error("rounds must be positive")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    def save(name, value):
        (args.output_dir / f"{name}.json").write_text(
            json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )

    metadata = {
        "started_utc": datetime.now(UTC).isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "rounds_per_player": args.rounds,
        "poll_seconds": 0.01,
        "http_transport": "loopback; embedding adapter uses configured remote Ollama",
        "model_origin": "same SEMAPHORE_OLLAMA_BASE_URL for game and verifier",
        "hardware_limit": "remote CPU/GPU identity and utilization not independently measured",
        "acceptance_established": False,
        "source_sha256": {
            str(path.relative_to(ROOT)).replace("\\", "/"): digest(path.read_bytes())
            for directory in (
                "experiments/acceptance",
                "experiments/game_server",
                "packages/semaphore_core",
            )
            for path in sorted((ROOT / directory).rglob("*.py"))
        },
    }
    git = subprocess.run(
        ["git", "-c", f"safe.directory={ROOT.as_posix()}", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    metadata["baseline_commit"] = git.stdout.strip() if git.returncode == 0 else None
    save("metadata", metadata)
    service = server = thread = None
    try:
        provider = OllamaEmbedder(OllamaConfig.from_env())
        embedder = PinnedEmbedder(provider)
        metadata["fingerprint_sha256"] = fingerprint_hash(embedder.identity())
        print("Pinned model preflight passed", flush=True)
        game_raw = (ROOT / "fixtures/w3/calibration-authored.json").read_bytes()
        verification_raw = (ROOT / "fixtures/w3/held_out-authored.json").read_bytes()
        artifact, vectors = prepare_artifact(game_raw, embedder)
        metadata["artifact_identities"] = thaw(artifact.identities)
        metadata["verification_manifest_sha256"] = digest(verification_raw)
        for _ in range(3):
            embedder.embed_queries(["acceptance warmup association"])
        metadata["warmup"] = "entry preparation plus three excluded query calls; no model unload"
        resident = provider.running_model()
        metadata["model_residency"] = {
            key: resident.get(key)
            for key in ("name", "digest", "size", "size_vram", "context_length")
        }
        save("metadata", metadata)
        print("Running independent real-model parity", flush=True)
        parity_report = parity(verification_raw, backend="core", ollama_env=True)
        save("parity", parity_report)
        print(f"Parity passed={parity_report['passed']}; running 1/4/8-player load", flush=True)
        service = GameService({"default": (artifact, vectors)}, embedder)
        server = make_server(service, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        command = [
            sys.executable,
            "-m",
            "experiments.acceptance.verify_worker",
            "--backend",
            "core",
            "--manifest-path",
            str(ROOT / "fixtures/w3/held_out-authored.json"),
            "--ollama-env",
            "--pressure",
        ]
        report = load_probe(
            f"http://127.0.0.1:{server.server_port}", "default", command, rounds=args.rounds
        )
        save("load", report)
        metadata["probe_execution_passed"] = parity_report["passed"] and report["passed"]
        print(json.dumps(report, indent=2), flush=True)
    except Exception as exc:
        metadata["failure_type"] = type(exc).__name__
        metadata["probe_execution_passed"] = False
        print(f"Measurement failed: {type(exc).__name__}", flush=True)
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        if service is not None:
            service.close()
        if thread is not None:
            thread.join(1)
        metadata["finished_utc"] = datetime.now(UTC).isoformat()
        save("metadata", metadata)
    return 0 if metadata["probe_execution_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
