# Everyday word pool

`everyday.json` is the default server pack: 235 familiar English words with
three original clue examples each. Content covers food, animals, nature, home,
clothing, transport, places, music and occupations. Definitions in `embed_text`
anchor the intended meaning of ambiguous words.

Original text is MIT licensed. Forty entries reuse the repository's authored
manifest examples; the remainder were authored for this playable pool. These
are content examples, not measured semantic quality results.

Casual rounds draw without replacement from the whole pool. The default round
has six opening words and up to 119 arrivals; each new game draws independently.
To add words, provide unique IDs and labels, contextual embedding text, and
three to five legal clues per entry. Run `pytest tests/game/test_word_pool.py`
to validate the pack and sampling behavior.
