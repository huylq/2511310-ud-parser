"""Contract for Project 4 (Treebank Curation & Adjudication), consumed by
Project 9 (export/benchmark, as the gold evaluation set).

An `AdjudicatedSentence` is what comes out the far side of resolving a
disagreement between two candidate analyses (e.g. Project 2's real parser
vs. a DeepSeek proposal, or two annotator passes) against
`tests/fixtures/treebank/gold_treebank_seed.conllu`. Per
`.claude/agents/treebank-adjudicator.md`'s standard: every decision states
the competing analyses, the deciding principle, and why it generalizes --
not a bare pick. `AdjudicationDecision.rationale` is where that goes, and
`validate_adjudicated_sentence` requires it to be non-empty for exactly that
reason.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd
import pandera as pa

from ._common import SOURCE_VALUES, UD_DEPREL, UPOS_TAGSET
from .ud import UDToken

SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class AdjudicationDecision:
    idx: int                # token idx the decision concerns
    field: str               # "upos" | "head" | "deprel"
    candidate_a: str
    candidate_b: str
    decision: str             # the adjudicated final value -- must equal candidate_a or candidate_b
    rationale: str             # required prose: competing analyses + deciding principle + why it generalizes


@dataclass(frozen=True)
class AdjudicatedSentence:
    sent_id: str
    tokens: tuple[UDToken, ...]                  # the final, adjudicated analysis
    decisions: tuple[AdjudicationDecision, ...]   # empty when the two candidates agreed everywhere
    source: Literal["stub", "real"] = "stub"


@dataclass(frozen=True)
class IAAReport:
    """Inter-annotator-agreement summary over the gold seed set."""

    metric: str        # e.g. "cohen_kappa_upos", "las_agreement"
    value: float
    n_items: int


_FIELDS = frozenset({"upos", "deprel", "head"})

DECISION_SCHEMA = pa.DataFrameSchema(
    {
        "sent_id": pa.Column(str, pa.Check.str_length(min_value=1)),
        "idx": pa.Column(int, pa.Check.ge(0)),
        "field": pa.Column(str, pa.Check.isin(_FIELDS)),
        "decision": pa.Column(str, pa.Check.str_length(min_value=1)),
        "rationale": pa.Column(str, pa.Check.str_length(min_value=1)),
    },
    strict=False,
)


def to_rows(sentence: AdjudicatedSentence) -> list[dict]:
    return [
        {
            "sent_id": sentence.sent_id,
            "idx": d.idx,
            "field": d.field,
            "decision": d.decision,
            "rationale": d.rationale,
        }
        for d in sentence.decisions
    ]


def validate_adjudicated_sentence(sentence: AdjudicatedSentence) -> AdjudicatedSentence:
    """Raises `ValueError`/`pandera.errors.SchemaError` if: the final token
    sequence is empty; any token's `upos`/`deprel` falls outside the
    standard tagsets; or any decision has an empty rationale (a bare pick
    with no stated reasoning is not an adjudication, per
    `.claude/agents/treebank-adjudicator.md`)."""
    if not sentence.tokens:
        raise ValueError(f"AdjudicatedSentence {sentence.sent_id!r} has zero tokens")
    for t in sentence.tokens:
        if t.upos not in UPOS_TAGSET:
            raise ValueError(f"{sentence.sent_id}: token {t.idx} upos {t.upos!r} not a UD tag")
        if t.deprel not in UD_DEPREL:
            raise ValueError(f"{sentence.sent_id}: token {t.idx} deprel {t.deprel!r} not a UD relation")
    rows = to_rows(sentence)
    if rows:
        DECISION_SCHEMA.validate(pd.DataFrame(rows), lazy=False)
        for d in sentence.decisions:
            if d.decision not in (d.candidate_a, d.candidate_b):
                raise ValueError(
                    f"{sentence.sent_id}: decision {d.decision!r} at idx {d.idx} matches "
                    f"neither candidate ({d.candidate_a!r}, {d.candidate_b!r})"
                )
    return sentence
