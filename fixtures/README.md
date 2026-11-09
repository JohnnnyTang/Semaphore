# Stage 1 fixtures

Only public or synthetic examples belong here. Do not commit participant clues,
credentials, downloaded model weights, or private runtime data.

Wave 2 owns these future fixture directories independently:

- `semantic/`: calibration and held-out examples, source/provenance records.
- `game_traces/`: scripted events and expected state/score after each event.
- `manifests/`: draft valid and invalid pack examples.

Those directories are created by their owning sessions. Their formats remain
provisional until Wave 3; the handoff's illustrative manifest is not a passing
publication fixture.

For gameplay design without a model, `semaphore_core.FakeRanker` accepts a mapping
of exact clue strings to entry-ID/score mappings. It returns highest score first,
uses ascending entry IDs for exact ties, and fails on missing data. All scores
must be finite. It does not check clue legality, normalize text, or measure
semantic quality. Small synthetic examples live in `tests/test_ranking.py`.
