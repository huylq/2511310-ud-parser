"""Shared constants and helpers for the `interfaces/` contracts.

Nothing here is a contract by itself -- it exists so the individual
interface modules (`linguistics.py`, `ud.py`, ...) don't each redefine the
same tagsets/label sets and drift apart. Values are re-exported from
`platform.agents.registry` where a matching one already exists there (the
same set DeepSeek output is validated against), so a student project and
the DeepSeek-refinement stage it may call into can never disagree about
what a valid tag looks like.
"""

from __future__ import annotations

from vietnlp.platform.agents.registry import NER_LABELS, REGISTERS, UPOS_TAGSET

__all__ = ["REGISTERS", "UPOS_TAGSET", "NER_LABELS", "UD_DEPREL", "SOURCE_VALUES", "mention_id"]

SOURCE_VALUES = frozenset({"stub", "real"})

# Universal Dependencies v2's relation inventory (https://universaldependencies.org/u/dep/index.html).
# Standard and public, not project-specific -- safe to hardcode once, here,
# rather than each of projects 2/4/6 defining its own copy.
UD_DEPREL = frozenset(
    """
    acl advcl advmod amod appos aux case cc ccomp clf compound conj cop csubj
    dep det discourse dislocated expl fixed flat goeswith iobj list mark nmod
    nsubj nummod obj obl orphan parataxis punct reparandum root vocative xcomp
    """.split()
)


def mention_id(sent_id: str, token_start: int, token_end: int) -> str:
    """Canonical key for a token span, shared by NER/coref/OUPM so a mention
    minted in one project can be referenced by id in another without either
    side inventing its own addressing scheme."""
    return f"{sent_id}:{token_start}:{token_end}"
