# Default corpus source and scale feasibility

Date: November 8, 2026. This is a source-risk review and editorial estimate, not
a completed 3,000–5,000-entry corpus or a legal determination. The W2 fixture is
wholly authored; no source data below was copied into it.

| Source / role | Evidence and redistribution concern | Proposed use |
| --- | --- | --- |
| Princeton WordNet 3.0 / nouns and senses | The [official license](https://wordnet.princeton.edu/license-and-commercial-use) permits copying, modification and distribution subject to preserving its notices and disclaimers, with restrictions on promotional use of Princeton's name. | Candidate noun/sense inventory; preserve source identity and notices for any redistributed derivative. Avoid importing dictionary definitions as authored clues. |
| wordfreq / frequency screening | The [maintainer's license section](https://github.com/rspeer/wordfreq#license) distinguishes Apache-licensed software from CC BY-SA 4.0 data and additional source credits; it discourages detached CSV redistribution. | Local prioritization only initially. Do not label redistributed frequency tables or source-derived packs MIT; review attribution/share-alike scope before bundling. |
| Brysbaert, Warriner & Kuperman / concreteness | The [authors' university record](https://biblio.ugent.be/publication/5774089) describes 37,058 words and 2,896 two-word expressions. Access to a paper does not establish redistribution rights for its supplementary data; the original data/license endpoint was unavailable during this review. | Hold redistribution. Obtain and archive the exact data license or author permission; otherwise create independent editorial concreteness labels. |
| Authored entries and clues / launch fallback | All 150 current entries and clues are synthetic authoring, without dataset import. Human review, cultural bias and definition-style clues remain risks. | Keep provenance per source/version and use independent clue reviewers; authoring is feasible but not free. |

No joined noun/frequency/concreteness yield has been measured. Therefore a claim
that these sources already produce 5,000 playable words would be unsupported.
The practical next probe is a rights-cleared 500-candidate stratified sample:
record unique nouns after normalization, familiarity, concreteness, unwanted
proper names, ambiguity, duplicate senses, and legal-clue feasibility. Publish
counts for every filter, including rejected examples, before scaling.

For planning only, if 40–60% of a screened candidate pool survives editorial and
semantic checks, 3,000 usable entries need 5,000–7,500 candidates and 5,000 need
about 8,334–12,500. These are arithmetic scenarios, not observed retention rates.
At 3–5 clues per entry the corpus requires 9,000–25,000 unique legal clues.
Assuming 2 minutes per candidate for first review, 1 minute per clue for review,
and 20% rework, even 3,000 entries with three clues costs approximately 420–480
review hours at the above candidate yields. The assumptions need timed pilot
measurements; automated drafting does not remove independent review.

The 150-entry fixture proves that the file format and authoring workflow can
represent the required categories; it is intentionally balanced and is not a
random sample supporting an extrapolated survival percentage. Geography and
specialist biology should not dominate the default general pack merely because
their clues are easy for an agent to draft.

Recommended content gate: archive licenses and snapshots; run the 500-candidate
yield/timing probe; independently review 100 target/clue sets; then schedule
corpus production as explicit work. Keep full corpus, source data and private
play logs out of this W2 change. Record model-specific rejected pairs separately
so a later model migration can revisit exclusions without rewriting provenance.
