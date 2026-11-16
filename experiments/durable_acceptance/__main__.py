"""Run probes against an explicitly supplied trusted local adapter module."""

import argparse
import json
from pathlib import Path

from .harness import ProcessAdapter, behavior_probe, crash_probe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter", required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()
    args.workspace.mkdir(parents=True, exist_ok=True)
    if any(args.workspace.iterdir()):
        parser.error("workspace must be empty; probes use disposable synthetic databases")
    results = []
    for phase in ("admission", "completion", "terminal"):
        for edge in ("before", "after"):
            adapter = ProcessAdapter(args.adapter, args.workspace / f"{phase}-{edge}")
            results.append(crash_probe(adapter, phase, edge))
    results.append(behavior_probe(ProcessAdapter(args.adapter, args.workspace / "behavior")))
    print(
        json.dumps(
            {"adapter": args.adapter, "probes": results, "real_model_acceptance": False}, indent=2
        )
    )


if __name__ == "__main__":
    main()
