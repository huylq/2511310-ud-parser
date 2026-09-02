"""Deterministic, naive stub for Project 3's output -- unblocks Projects
4, 5, 7, 8, 9.

Entity detection: any token whose form starts with an uppercase letter
becomes a single-token span labeled `"MISC"` -- this stub cannot tell
PER from LOC from ORG, which is exactly Project 3's job. Coreference:
exact surface-text match only, no pronoun resolution, no honorific
stripping -- two spans with identical `text` in the same document become
one `CorefChain`. NOT a reference implementation.
"""

from __future__ import annotations

from collections import defaultdict

from vietnlp.interfaces.linguistics import SegmentedSentence
from vietnlp.interfaces.ner import CorefChain, NamedEntity


def stub_extract_entities(sentence: SegmentedSentence) -> list[NamedEntity]:
    return [
        NamedEntity(
            sent_id=sentence.sent_id,
            token_start=t.idx,
            token_end=t.idx + 1,
            label="MISC",
            text=t.form,
            source="stub",
        )
        for t in sentence.tokens
        if t.form and t.form[0].isupper()
    ]


def stub_coref(entities: list[NamedEntity]) -> list[CorefChain]:
    """Groups spans with identical `text` (exact match only) among the
    supplied entities -- pass all entities for one document. A singleton
    group produces no chain (a chain needs >= 2 mentions, per
    `interfaces.ner.validate_coref_chain`)."""
    by_text: dict[str, list[str]] = defaultdict(list)
    for e in entities:
        by_text[e.text].append(e.mention_id)
    return [
        CorefChain(chain_id=f"stub-chain-{i}:{text}", mention_ids=tuple(mention_ids), source="stub")
        for i, (text, mention_ids) in enumerate(sorted(by_text.items()))
        if len(mention_ids) >= 2
    ]
