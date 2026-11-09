# Semantic fixture v1

This is an agent-authored synthetic experiment, released under the repository's
MIT license. No third-party dataset rows, human participant clues or model vectors
are included. The 150 entries and 450 candidate legal clues are not independently
human reviewed. Knowledge/style bias and clues resembling dictionary definitions
limit what high scores would establish.

`authored.tsv` is the source (pipe-separated despite its familiar tabular suffix).
`fixture.json` is the frozen expanded input. `fixture.sha256` identifies its exact
UTF-8 bytes. Regeneration uses `experiments/model_eval/build_fixture.py`; changes
after measurement require a new fixture version and invalidation of old results.
Generation uses no embedding model, random runtime seed or model results.

Each of five categories has 30 entries: concrete objects, geography, ambiguous
labels, multiword labels, and deliberately specialist biology. Within each category,
indices congruent to 0 or 1 modulo 5 are held out: 60 targets with 180 natural
clues; the other 90 targets/270 clues are calibration. Entries and candidate pools
can overlap across splits, but target-clue pairs cannot. This is a target-level
evaluation split, not a disjoint unseen-vocabulary test.

Every target has one exact-label illegal control in addition to its three authored
clues. These 150 controls test fixture hygiene and are excluded from embeddings
and quality denominators. W3 still owns production normalization, inflections,
aliases and forbidden-phrase semantics; the fixture validator's conservative
substring check is not a proposed game rule.

Every case records 20 IDs: target, two deterministic same-category decoys, then
17 hash-ordered alternatives. Prefixes give stack sizes 6, 12 and 20. Same-category
decoys are authored difficulty controls, not a claim that every pair is a measured
nearest neighbor. All three models receive identical candidates. Rank 1 is most
related (highest cosine); exact ties use ascending ID, matching the provisional
fake ranker. No game animation or production near-tie rule is implied.

Three fixture pack views are experiments, not publishable manifests: general
intended-good, difficult biology, and an intentionally weak generic clue `thing`
for every target. The weak view deliberately violates unique-clue expectations.
Five deterministic samples with up to 19 decoys yield a median per clue, then a
median per target; reachability is the fraction of target medians at rank <=3.
Expected separation is a hypothesis to measure, never a preset pass result.

Validate without downloading model packages:

```sh
python experiments/model_eval/run.py validate
python -m unittest discover -s experiments/model_eval -p 'test_*.py'
```
