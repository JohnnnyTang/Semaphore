# Draft manifest and protocol fixtures

Original synthetic fixture text authored for Semaphore on November 8, 2026, under
the repository MIT license. The handoff illustration is copied from the repository
handoff as an explicitly failing example. No participant clues, third-party corpus,
model vectors or measured semantic results are included.

From a repository with the coordinator's locked development dependencies:

```sh
uv run --no-sync python fixtures/manifests/check_examples.py
uv run --no-sync ruff check fixtures/manifests
uv run --no-sync ruff format --check fixtures/manifests
```

W2-D worktree validation used
`D:/code/Semaphore/.venv/Scripts/python.exe fixtures/manifests/check_examples.py`
because root dependency changes are coordinator-owned. No network access is needed
for the checks; all JSON Schema references resolve through a preloaded registry.

`cases.json` identifies the draft schema and each expected outcome. The valid
example has 40 authored labels with 3 clues each and passes structural/hygiene
checks only. Invalid examples isolate unknown uploaded vectors, missing rights,
normalized duplicate labels/clues and foreign test IDs. The handoff illustration
fails several requirements deliberately (old spec, two entries, missing IDs and
test coverage); it is not a valid pack made invalid only by changing a version.

`protocol-examples.json` tests command/snapshot/rejection/job/account/fingerprint
shapes. Its all-zero digests, fabricated runtime and metrics are **synthetic schema
values**, not a model selection, hub report or benchmark evidence. The runner checks
four schema documents and 19 protocol examples, including cross-file references,
plus seven manifest examples. It also exercises strict parsing, fixed hash vectors,
metadata/report seed isolation, changed-clue/vector isolation, entry ordering and
the owner/version retry decision table. No HTTP server, authorization middleware,
database race, stemming policy or real model runs in this check.

`hash-vectors.json` fixes exact accepted-byte, semantic-projection and vector-
projection digests of `valid-structural.json`. The local `.gitattributes` forces LF
for JSON on every checkout because the full manifest digest is byte-sensitive.
Do not regenerate hash expectations merely to make a changed algorithm pass; W3
must review intentional changes and version the protocol. Entry order matters;
test-clue authoring order and metadata do not affect semantic seeds.

`generate_examples.py` reproduces the seven manifest cases and their index; it
does not invent semantic results or regenerate hash expectations. After intentional
fixture changes, compare differences and separately review/update fixed digests.
The fixture scripts are draft acceptance aids, not the production shared core.
