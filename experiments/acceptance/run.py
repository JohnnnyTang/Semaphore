"""Run bounded independent probes. See docs/evidence/probe-method.md for scope."""

import argparse
import json
import sys
from pathlib import Path

from experiments.acceptance.common import ROOT
from experiments.acceptance.load import load_probe
from experiments.acceptance.parity import invalid, parity
from experiments.acceptance.replay import import_factory, reordered_delivery, replay
from experiments.acceptance.robustness import robustness


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "probe",
        choices=["plumbing", "parity", "invalid", "replay", "load", "robustness", "reorder"],
    )
    parser.add_argument(
        "--manifest", type=Path, default=ROOT / "fixtures/w3/held_out-authored.json"
    )
    parser.add_argument("--backend", choices=["core", "reference"], default="core")
    model = parser.add_mutually_exclusive_group()
    model.add_argument("--ollama-url")
    model.add_argument("--ollama-env", action="store_true")
    parser.add_argument("--adapter")
    parser.add_argument("--base-url")
    parser.add_argument("--artifact-id", default="default")
    parser.add_argument("--verification-command-json", type=json.loads)
    parser.add_argument("--rounds", type=int, default=10)
    parser.add_argument("--poll-seconds", type=float, default=0.01)
    parser.add_argument(
        "--synthetic", action="store_true", help="suppress load timings for a fake model"
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.probe == "parity":
            report = parity(
                args.manifest.read_bytes(),
                backend=args.backend,
                ollama_url=args.ollama_url,
                ollama_env=args.ollama_env,
            )
        elif args.probe == "invalid":
            report = invalid(args.manifest.read_bytes(), backend=args.backend)
        elif args.probe == "replay":
            if not args.adapter:
                parser.error(
                    "replay requires --adapter module:factory; use plumbing for the oracle"
                )
            report = replay(import_factory(args.adapter), synthetic=False)
        elif args.probe == "reorder":
            report = reordered_delivery()
        elif args.probe in {"load", "robustness"}:
            if not args.base_url:
                parser.error("HTTP probes require --base-url")
            if args.probe == "load":
                report = load_probe(
                    args.base_url,
                    args.artifact_id,
                    args.verification_command_json,
                    rounds=args.rounds,
                    synthetic=args.synthetic,
                    poll_seconds=args.poll_seconds,
                )
            else:
                report = robustness(args.base_url, args.artifact_id)
        else:
            from experiments.acceptance.fake import fake_server

            server = fake_server()
            try:
                origin = f"http://127.0.0.1:{server.server_port}"
                reports = [
                    replay(),
                    reordered_delivery(),
                    robustness(origin, synthetic=True),
                    invalid(args.manifest.read_bytes(), backend="reference"),
                ]
                command = [
                    sys.executable,
                    "-m",
                    "experiments.acceptance.verify_worker",
                    "--backend",
                    "reference",
                    "--manifest-path",
                    str(args.manifest),
                ]
                reports.append(
                    load_probe(
                        origin,
                        "default",
                        command,
                        rounds=args.rounds,
                        synthetic=True,
                        poll_seconds=args.poll_seconds,
                    )
                )
                report = {
                    "evidence": "synthetic-plumbing",
                    "acceptance_established": False,
                    "passed": all(r["passed"] for r in reports),
                    "reports": reports,
                }
            finally:
                server.shutdown()
                server.server_close()
    except Exception as exc:
        # Keep raw clues, HTTP bodies and arbitrary worker errors out of aggregate artifacts.
        report = {
            "passed": False,
            "acceptance_established": False,
            "failure_type": type(exc).__name__,
        }
    raw = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(raw, encoding="utf-8")
    print(raw, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
