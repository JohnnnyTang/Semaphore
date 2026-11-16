# W2 trusted local installation

November 16, 2026 (Asia/Shanghai). A real installation and explicitly accepted
casual artifact completed against the previously owner-selected Ollama endpoint.
The owner's request to finish W2 authorizes this bounded local installation; it
is not independent human approval or authorization to expose a public service.

## Provenance and scope

Reviewed `packs/README.md`, `packs/everyday.json`, the repository MIT license and
`fixtures/content-pilot/README.md`. The 235-entry everyday pool contains original
MIT-licensed authored material; no third-party corpus was imported. Forty entries
reuse repository-authored examples. Its 705 example clues are authored content,
not participant capture. Acceptance records this rights reference separately from
the immutable measured report. Independent content review remains open.

The installer used the actual `PackService`, `AuthService.bootstrap`, real SQLite
transactions, atomic asset staging, `PinnedEmbedder` and the frozen core verifier.
No synthetic reports or vectors were substituted. A generated local operator
password was used only in memory and discarded; no credentials, account IDs,
private database, vectors, or model endpoint are committed in this evidence.

## Reproduction and results

With the previously configured operator endpoint in `SEMAPHORE_OLLAMA_BASE_URL`:

```powershell
uv run --no-sync python -m experiments.durable_acceptance_w2.install --output data/s2-w2-installation-20261116-b
```

Use a new output directory when repeating. The helper refuses overwrite, pins the
full frozen model identity, limits network operations to 30 seconds, and consumes
one installer slot with the existing 600-second publication deadline. No model
pressure job ran concurrently. First bootstrap used a rejected hyphenated login;
that attempt failed before model work. The corrected underscore login succeeded.

- Verification elapsed: 51,074 ms, including the bounded corpus inference work.
- Entries: 235; legal authored clues: 705; reachable entries: 233 (99.1489%).
- Mean rank: 1.174468; flagged entries: `cherry`, `turtle`; flagged pairs: none.
- Report authority remains `experiment-recomputed`; status remains `measured`.
- Published exact manifest bytes and 235 ordered 2,560-dimensional entry vectors.
- Accepted one bounded casual artifact: six initial entries, twelve arrivals at
  five-second intervals, deadline 65,000 ms; explicit null seed/generator policy.
- Exact installation retry returned the original publication without re-inference.
- A newly constructed service and database connections read the accepted artifact.

| Pin | Value |
| --- | --- |
| Manifest SHA-256 | `f947edeac031f3181d116941393202cd68ef5865809d6f97be25f45256baefc0` |
| Fingerprint | `657120305f464d0fb6a6006b9dbc8152af04ba30317dadcef1b41af0aa2941a4` |
| Protocol | `910038622a203fbd9ed010d7d0d7169d35ea3a79d76e879a38e8d77de4d97132` |
| Ruleset | `experiment-arcade-paced-v1` |
| Report ID | `1095bf66cc1d4229a7297add0045af3b` |
| Artifact ID | `f321eb5386b446acba1e9a7996d47bf1` |
| Config digest | `d79ed416d19fb4c254c8481a6f31aea58c3148bc810aac902eab58153bb8db3a` |
| Artifact digest | `c0ca759b70f0c54cdf025dbfb419f468b13b22cad03c6a2bdfba59b7336fe98f` |

Local runtime assets, database, full measured report and summary remain under
ignored `data/s2-w2-installation-20261116-b/`. The helper passes Ruff lint and
format checks. This installation satisfies the actual trusted-installation part
of W2; coordinator integration must close the remaining host wiring checks.

## Retained gates

The provisional reachability threshold is not a calibrated human quality gate.
The reported 51-second batch is not gameplay latency evidence. Independent human
review, real signed-in game acceptance, 100 ms gameplay target, remote-host
network/resource isolation and population source-yield study remain open. The
helper opens no listener and makes no production-readiness claim. The generated
operator password is discarded, so this is an acceptance database, not an
operator-ready persistent deployment; bootstrap/reset through the host CLI is
required for an operational deployment.
