# W5 independent creator walkthrough

November 11, 2026. Baseline `64e3a90`, Windows 10, Python 3.12.10. I used the
[creator kit proposal](../design/creator-kit.md) as the journey and the installed
development dependencies with `PYTHONPATH=packages;.` to select this worktree's
shared core. The input is the existing [authored held-out manifest](../../fixtures/w3/held_out-authored.json)
with 60 synthetic entries and 180 synthetic clues. I simulated creation and
packaging in memory and used the deterministic text-hash embedder. The test made
no model or network calls. This is a contract walkthrough by an independent
agent. Acceptance of the future CLI, independent authoring, real local and hub
runtime parity, and publication still require separate evidence.

## What the walkthrough exercised

| Creator action | Observed outcome |
| --- | --- |
| Initialize and validate | Emptying the fixture's entries and test set produced `schema_invalid`, consistent with an intentionally incomplete scaffold. The complete fixture parsed and passed shared hygiene, coverage and legality checks. |
| Break, diagnose and repair | Replacing the first legal test clue with the target's exact label produced `illegal_clue`. Both failures returned an empty error path. Restoring the authored clue allowed verification. A creator with many entries needs the entry ID and clue index to act on this result. |
| Run a local playtest | `verify_pack` returned `measured` with 3/60 reachable and mean rank 9.6333 on text-hash vectors. These values test report shape only. Verification with `experiment-arcade-paced-v1`, the current default casual ID, produced `invalid_ruleset`. |
| Read the report and package | I projected reachability, mean rank, flagged IDs and metrics version into the allowed `test_report` fields. I serialized sorted keys as UTF-8 JSON with two-space indentation and one trailing LF for reproducible trial bytes. This is a walkthrough encoding choice. Local authority remained outside the upload manifest. |
| Recompute the packaged artifact | Original, repackaged and modified self-report manifests shared the semantic and vector hashes. The raw digest changed on packaging. Recomputing the package preserved all report fields except raw digest and elapsed time. Setting self-reported reachability to 1.0 still left recomputed metrics unchanged. |
| Compare independent paths | The [parity harness](probe-method.md#separate-verification-paths) ran fresh processes for the W3 reference and shared core on the same package bytes. All 900 clue/sample comparisons agreed in membership, order and target rank, with raw scores within `1e-5`. Report fields agreed apart from elapsed time. Both paths returned `measured`. |
| Submit, retry and inspect publication | [Platform draft](../contracts-drafts/platform.md#http-semantics) gives an owner-scoped async job, exact-byte/key retry after transport loss, a new key for changed rejected bytes subject to reservation policy, and a new version for changed published bytes. The experiment exposes no auth, upload, job or publication route to exercise these steps. |

| Hash | SHA-256 |
| --- | --- |
| Original bytes | `8ebf7369b1a1406e3ae3f2e2b553f77b97e451414fef7fa3e095c14552e9b76f` |
| Packaged bytes | `ecf45409c44746b7e3e6515fb4a84a6d07cba4533e9b33e0f4b5aa404871d830` |
| Semantic projection | `025c488ea3dc3d906c5e8082743bf16e499cee6b6957daa5da911419596b7c66` |
| Entry-vector projection | `d1f6a0dfaa6eabf8d1d9e99074fc2ff9ec6247539affea06147bda10fd4a7eb8` |

## Reproduce package and parity

Run in the repository's locked Python 3.12 environment. On Windows PowerShell,
set `$env:PYTHONPATH='packages;.'` before piping the Python snippet to
`python -`.

```python
import json
from pathlib import Path

from experiments.acceptance.parity import parity
from experiments.acceptance.verify_worker import SyntheticEmbedder
from semaphore_core.verification import manifest_hashes, parse_manifest, verify_pack

source = parse_manifest(Path("fixtures/w3/held_out-authored.json").read_bytes())
report = verify_pack(source, SyntheticEmbedder(), "experiment-arcade-v1")
artifact = dict(source.manifest)
artifact["test_report"] = {
    "reachability": report["metrics"]["reachability"],
    "mean_rank": report["metrics"]["mean_rank"],
    "flagged": report["flagged_entries"],
    "metrics_version": report["metrics_version"],
}
raw = (
    json.dumps(artifact, ensure_ascii=False, allow_nan=False, sort_keys=True, indent=2) + "\n"
).encode("utf-8")
print(manifest_hashes(parse_manifest(raw)))
result = parity(raw)
assert result["passed"], result
print(json.dumps(result))
```

## Decisions and later acceptance

- Give the creator a stable path for schema and semantic errors and a bounded
  per-entry diagnostic when explaining weak words. The current report supplies
  flagged IDs, aggregate mean rank and near-duplicate pairs. The proposed
  `report` command's per-entry typical ranks and hard-neighbor guidance need
  an explicit local diagnostic format or a specified recomputation step.
- Bind packaging to the report's semantic hash, model fingerprint, protocol and
  applicable ruleset. The current schema admits only aggregate self-report
  fields and optional metrics version. Keep the detailed comparison data in a
  local report with its own versioned authority and identity format. Compare
  the package's resulting exact-byte digest separately when the hub recomputes.
- Resolve how the independent creator runtime reproduces the model pin. Today
  the verifier requires equality with a LAN development fingerprint that
  includes a raw service filesystem path. Test portable model identity on an
  independent installation before promising the same model will pass there.
- In Stage 3, ask an independent creator to author and repair a pack from the
  shipped workflow, package it and compare their real-model decisions with
  hub recomputation. Exercise failed-job repair, exact retries and publication
  of a new version with the prior leaderboard intact. Offline kit installation
  and default content distribution also need their later release checks.
