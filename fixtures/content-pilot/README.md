# Bounded authored content pilot

November 14, 2026. Original agent-authored material under the repository MIT
license; no WordNet, wordfreq, concreteness dataset, or private player rows were
copied. `authored.psv` records five deliberately balanced everyday categories,
eight targets each, context strings and three clues per target. The 10 entries
in `rejections.json` are deliberately selected editorial controls, not random
source rejections. Labels such as bank/seal require a selected sense; specialist
familiarity decisions are editorial judgments, not measured reader responses.

This is a 50-candidate workflow pilot, not the planned 500-candidate source-yield
study. Its 40/50 retention must not be extrapolated to a 3,000–5,000-word corpus.
The drafting agent also performed editorial screening; independent human review
is pending. Definition-like clues, cultural familiarity, dialect (ruler, sieve,
colander), and neighboring-tool confusion require human review.

The measured drafting/build interval was 16:19:01–16:22:12 Asia/Shanghai (191 s),
including tool overhead. It is agent wall time, not human labor or a production
review-cost estimate. Human review time is unknown, not zero.

Rebuild into a new output directory:

```powershell
$env:PYTHONPATH = 'packages;.'
.venv/Scripts/python.exe -m experiments.acceptance.content_pilot --output-dir data/content-pilot-new
```

The command checks actual core manifest/clue rules, keeps per-filter counts and
source hashes, and rejects accidental overwrite. The [measurement report](../../docs/evidence/feasibility-2026-11-14.md)
links the frozen manifest, raw semantic metrics, local resource results and limits.
