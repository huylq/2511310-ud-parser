"""Deterministic, naive stub for Project 4's output -- unblocks Project 9.

Adjudication policy: wherever two candidate systems disagree on a token's
`upos`/`head`/`deprel`, always prefer system A, with a placeholder
rationale. This is NOT an adjudication in the sense
`.claude/agents/treebank-adjudicator.md` requires -- a real ruling states
the competing analyses, the deciding principle, and why it generalizes.
It exists only to produce a structurally valid `AdjudicatedSentence` so
Project 9 can build its export/benchmark pipeline before Project 4 ships
real rulings. NOT a reference implementation.
"""

from __future__ import annotations

from vietnlp.interfaces.treebank import AdjudicatedSentence, AdjudicationDecision
from vietnlp.interfaces.ud import UDToken

_STUB_RATIONALE = "stub adjudication: system A preferred by default, no linguistic judgment applied"


def stub_adjudicate(
    sent_id: str, system_a: tuple[UDToken, ...], system_b: tuple[UDToken, ...]
) -> AdjudicatedSentence:
    """`system_a`/`system_b` must be the same length and index the same
    tokens in order -- the shape two independent parses of one sentence
    share. Always picks `system_a`'s value at every field where the two
    disagree."""
    if len(system_a) != len(system_b):
        raise ValueError(f"{sent_id}: system_a has {len(system_a)} tokens, system_b has {len(system_b)}")
    decisions = []
    for a, b in zip(system_a, system_b):
        if a.upos != b.upos:
            decisions.append(
                AdjudicationDecision(
                    idx=a.idx, field="upos", candidate_a=a.upos, candidate_b=b.upos,
                    decision=a.upos, rationale=_STUB_RATIONALE,
                )
            )
        if a.head != b.head:
            decisions.append(
                AdjudicationDecision(
                    idx=a.idx, field="head", candidate_a=str(a.head), candidate_b=str(b.head),
                    decision=str(a.head), rationale=_STUB_RATIONALE,
                )
            )
        if a.deprel != b.deprel:
            decisions.append(
                AdjudicationDecision(
                    idx=a.idx, field="deprel", candidate_a=a.deprel, candidate_b=b.deprel,
                    decision=a.deprel, rationale=_STUB_RATIONALE,
                )
            )
    return AdjudicatedSentence(sent_id=sent_id, tokens=system_a, decisions=tuple(decisions), source="stub")
