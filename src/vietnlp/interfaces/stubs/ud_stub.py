"""Deterministic, naive stub for Project 2's output -- unblocks Projects
4, 6, 8, 9.

Produces a trivial star-shaped tree: token 0 is root, every other token
attaches directly to token 0 with the generic `"dep"` relation. This is
NOT a claim about Vietnamese syntax (a real UD tree is almost never a flat
star) -- it exists only to be a structurally valid tree (it passes
`interfaces.ud.is_single_rooted_tree`) so downstream students can build
and test against *some* `DependencyParse` before Project 2 ships a real
parser. NOT a reference implementation.
"""

from __future__ import annotations

from vietnlp.interfaces.linguistics import SegmentedSentence
from vietnlp.interfaces.ud import DependencyParse, UDToken


def stub_parse(sentence: SegmentedSentence) -> DependencyParse:
    tokens = tuple(
        UDToken(
            idx=t.idx,
            form=t.form,
            upos=t.upos or "X",
            head=0 if t.idx == 0 else 1,  # every non-root token attaches to token 0 (1-based head = 1)
            deprel="root" if t.idx == 0 else "dep",
        )
        for t in sentence.tokens
    )
    return DependencyParse(sent_id=sentence.sent_id, tokens=tokens, source="stub")
