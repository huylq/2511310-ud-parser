"""Contract for Project 1 (Word Segmentation & POS Tagging), consumed by
Projects 2 (UD parsing), 3 (NER/coref), 4 (treebank), 8 (serving) and 9
(export/benchmark).

Mirrors `tokens.form/syllables/upos` in
`platform/db/migrations/0001_core_schema.sql`; a `head`/`deprel`/`lemma`/
`xpos`/`feats` are deliberately absent here -- those are Project 2's and the
treebank's job to add, not this stage's.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd
import pandera as pa

from ._common import REGISTERS, SOURCE_VALUES, UPOS_TAGSET

SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class Token:
    idx: int                       # 0-based position within the sentence
    form: str                      # the segmented WORD -- may span several syllables
    syllables: tuple[str, ...]     # underlying syllable sequence, order-preserving, never collapsed
    upos: str | None = None        # UD v2 tag; None before POS tagging runs


@dataclass(frozen=True)
class SegmentedSentence:
    sent_id: str                    # f"{content_hash}:{sent_idx}", matches fixture_sentences.jsonl
    register: str                   # carried through from the fixture, never altered by this stage
    tokens: tuple[Token, ...]
    source: Literal["stub", "real"] = "stub"


SEGPOS_SCHEMA = pa.DataFrameSchema(
    {
        "sent_id": pa.Column(str, pa.Check.str_length(min_value=1)),
        "register": pa.Column(str, pa.Check.isin(REGISTERS)),
        "idx": pa.Column(int, pa.Check.ge(0)),
        "form": pa.Column(str, pa.Check.str_length(min_value=1)),
        "upos": pa.Column(str, pa.Check.isin(UPOS_TAGSET), nullable=True),
        "source": pa.Column(str, pa.Check.isin(SOURCE_VALUES)),
    },
    strict=False,
)


def to_rows(sentence: SegmentedSentence) -> list[dict]:
    """Flatten to one row per token -- the shape SEGPOS_SCHEMA validates."""
    return [
        {
            "sent_id": sentence.sent_id,
            "register": sentence.register,
            "idx": token.idx,
            "form": token.form,
            "upos": token.upos,
            "source": sentence.source,
        }
        for token in sentence.tokens
    ]


def validate_segmented_sentence(sentence: SegmentedSentence) -> SegmentedSentence:
    """Raises `pandera.errors.SchemaError` (or `ValueError` for structural
    defects pandera can't see, like zero tokens) on a nonconforming object;
    returns `sentence` unchanged otherwise."""
    rows = to_rows(sentence)
    if not rows:
        raise ValueError(f"SegmentedSentence {sentence.sent_id!r} has zero tokens")
    SEGPOS_SCHEMA.validate(pd.DataFrame(rows), lazy=False)
    return sentence
