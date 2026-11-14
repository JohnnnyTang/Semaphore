# 0005 — Ruleset binding and durable game boundaries

Date: November 14, 2026. Status: adopted contract; persistence implementation pending.

The W5 contract review found paced casual artifacts rejected by the verifier,
conflicting pack ownership keys, and unresolved durable score and clue policies.

Adopt `arcade-verification-binding-v1` in
[ruleset-verification.json](../../contracts/ruleset-verification.json): both exact
playable rulesets use the unchanged bottom3 metric, with separately recomputed,
correctly pinned reports. This fixes the callable verifier while preserving the
frozen reference and historical hashes. It does not certify sweep/pacing balance.

Adopt [storage](../../contracts/storage.md) and
[durable games](../../contracts/durable-game.md): global pack reservation, immutable
versions, HTTP snapshot/receipt transport, transactional finalization, interrupted
restart/quit with no competitive score, exact cohort separation, one row per game,
and deterministic score ties. Raw participant clues expire after 30 days; clue-free
receipts and private payload digests support retries through 90 days after game
end. Account deletion removes private records and anonymizes retained public
results; backups expire within 30 days and replay deletions before restoration.

These contracts supersede conflicting W2 storage/transport proposals for these
boundaries. The experiment API remains explicitly process-local. Durable database,
authentication and HTTP implementations are subsequent work; account issuance,
portable model identity, supported verification work budgets, publication and
Stage 1 human/performance/offline evidence are not resolved by this decision.
Stage 1 remains Revise pending its independent acceptance evidence.
