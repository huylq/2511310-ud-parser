"""Deterministic, naive stub for Project 1's output -- unblocks Projects
2, 3, 4, 8, 9 from week 1.

Splits `text` on whitespace only, so it produces one `Token` per
whitespace-delimited syllable and never merges multiple syllables into one
word (`sinh viên` stays two tokens, not one) -- syllable-vs-word is
exactly the problem Project 1 exists to solve, so this stub does not
attempt it. Every token is tagged `upos="X"`, UD's catch-all "other" tag,
never a real guess. NOT a reference implementation: copying this into a
Project 1 submission fails the gate's provenance check, since nothing
here is a genuine segmentation or tagging decision.
"""

from __future__ import annotations

from vietnlp.interfaces.linguistics import SegmentedSentence, Token


def stub_segment(sent_id: str, register: str, text: str) -> SegmentedSentence:
    pieces = text.split()
    tokens = tuple(
        Token(idx=i, form=piece, syllables=(piece,), upos="X") for i, piece in enumerate(pieces)
    )
    return SegmentedSentence(sent_id=sent_id, register=register, tokens=tokens, source="stub")
