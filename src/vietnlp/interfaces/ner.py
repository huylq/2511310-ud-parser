"""Contract for Project 3 (NER & Coreference Resolution), consumed by
Project 4 (treebank), Project 5 (ontology), Project 7 (OUPM), 8 (serving)
and 9 (export/benchmark).

Mirrors `mentions.token_start/token_end/confidence` and `entities.*` in
`platform/db/migrations/0001_core_schema.sql`. `token_start`/`token_end` are
0-based, end-exclusive, and index into the SAME sentence's
`interfaces.linguistics.SegmentedSentence.tokens` -- a span is a Python
slice `tokens[token_start:token_end]`, not a character offset (this project
does NOT ask a model for character offsets, following the anti-hallucination
pattern in `platform/agents/registry.py::_validate_ner`: locate spans
against the source yourself, never trust an offset the model reports).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd
import pandera as pa

from ._common import NER_LABELS, SOURCE_VALUES, mention_id

SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class NamedEntity:
    sent_id: str
    token_start: int      # 0-based, inclusive
    token_end: int        # 0-based, exclusive
    label: str             # PER | LOC | ORG | MISC
    text: str               # the verbatim surface form the span covers, NFC-normalized
    source: Literal["stub", "real"] = "stub"

    @property
    def mention_id(self) -> str:
        return mention_id(self.sent_id, self.token_start, self.token_end)


@dataclass(frozen=True)
class CorefChain:
    chain_id: str
    mention_ids: tuple[str, ...]   # NamedEntity.mention_id values, same document
    source: Literal["stub", "real"] = "stub"


NER_SCHEMA = pa.DataFrameSchema(
    {
        "sent_id": pa.Column(str, pa.Check.str_length(min_value=1)),
        "token_start": pa.Column(int, pa.Check.ge(0)),
        "token_end": pa.Column(int, pa.Check.gt(0)),
        "label": pa.Column(str, pa.Check.isin(NER_LABELS)),
        "text": pa.Column(str, pa.Check.str_length(min_value=1)),
        "source": pa.Column(str, pa.Check.isin(SOURCE_VALUES)),
    },
    strict=False,
    checks=pa.Check(
        lambda df: df["token_end"] > df["token_start"],
        error="token_end must be strictly greater than token_start -- span cannot be empty or reversed",
    ),
)


def to_row(entity: NamedEntity) -> dict:
    return {
        "sent_id": entity.sent_id,
        "token_start": entity.token_start,
        "token_end": entity.token_end,
        "label": entity.label,
        "text": entity.text,
        "source": entity.source,
    }


def validate_named_entities(entities: list[NamedEntity]) -> list[NamedEntity]:
    """Validates a batch (NER naturally produces zero-or-more spans per
    sentence, unlike the one-object-per-sentence shape of Projects 1/2).
    An empty list is valid -- not every sentence contains an entity."""
    if entities:
        NER_SCHEMA.validate(pd.DataFrame([to_row(e) for e in entities]), lazy=False)
    return entities


def validate_coref_chain(chain: CorefChain, known_mention_ids: set[str]) -> CorefChain:
    """`known_mention_ids` is the caller's own `NamedEntity.mention_id` set
    for the document this chain belongs to -- a chain referencing a mention
    that was never produced by NER is exactly the kind of hallucination
    `platform/agents/registry.py`'s validators exist to catch, applied here
    at the interface-contract level instead of an LLM-output level."""
    if len(chain.mention_ids) < 2:
        raise ValueError(f"CorefChain {chain.chain_id!r} has fewer than 2 mentions -- not a chain")
    missing = [m for m in chain.mention_ids if m not in known_mention_ids]
    if missing:
        raise ValueError(f"CorefChain {chain.chain_id!r} references unknown mention(s): {missing}")
    return chain
