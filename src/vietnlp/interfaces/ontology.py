"""Contract for Project 5 (Ontology Engineering), consumed by Project 6
(semantics, as predicate type signatures), Project 7 (OUPM, as entity
types), 8 (serving) and 9 (export/benchmark).

Mirrors `entities.ontology_class/wikidata_qid` in
`platform/db/migrations/0001_core_schema.sql`. Per
`.claude/agents/ontology-engineer.md`: kinship terms (anh/chi/em) are
properties on one Person class, not sibling classes, and administrative
units (xa/huyen/tinh) align to external KBs via `skos:closeMatch`, never
`owl:sameAs` -- `AlignmentRecord.relation`'s allowed value set encodes that
distinction structurally rather than leaving it to a docstring a student
might skip.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd
import pandera as pa

from ._common import SOURCE_VALUES

SCHEMA_VERSION = "1.0"

_ALIGNMENT_RELATIONS = frozenset({"owl:sameAs", "skos:closeMatch", "skos:exactMatch", "skos:broadMatch"})


@dataclass(frozen=True)
class OntologyIndividual:
    entity_id: str                  # a NamedEntity.mention_id or an EntityCluster.cluster_id
    ontology_class: str               # e.g. "Person", "Organization", "Place"
    wikidata_qid: str | None = None
    source: Literal["stub", "real"] = "stub"


@dataclass(frozen=True)
class AlignmentRecord:
    ontology_class: str
    external_uri: str                 # e.g. a Wikidata or DBpedia URI
    relation: str                      # owl:sameAs | skos:closeMatch | skos:exactMatch | skos:broadMatch
    source: Literal["stub", "real"] = "stub"


INDIVIDUAL_SCHEMA = pa.DataFrameSchema(
    {
        "entity_id": pa.Column(str, pa.Check.str_length(min_value=1)),
        "ontology_class": pa.Column(str, pa.Check.str_length(min_value=1)),
        "wikidata_qid": pa.Column(str, pa.Check.str_matches(r"^Q\d+$"), nullable=True),
        "source": pa.Column(str, pa.Check.isin(SOURCE_VALUES)),
    },
    strict=False,
)

ALIGNMENT_SCHEMA = pa.DataFrameSchema(
    {
        "ontology_class": pa.Column(str, pa.Check.str_length(min_value=1)),
        "external_uri": pa.Column(str, pa.Check.str_length(min_value=1)),
        "relation": pa.Column(str, pa.Check.isin(_ALIGNMENT_RELATIONS)),
        "source": pa.Column(str, pa.Check.isin(SOURCE_VALUES)),
    },
    strict=False,
)


def to_row(individual: OntologyIndividual) -> dict:
    return {
        "entity_id": individual.entity_id,
        "ontology_class": individual.ontology_class,
        "wikidata_qid": individual.wikidata_qid,
        "source": individual.source,
    }


def validate_ontology_individuals(individuals: list[OntologyIndividual]) -> list[OntologyIndividual]:
    if individuals:
        INDIVIDUAL_SCHEMA.validate(pd.DataFrame([to_row(i) for i in individuals]), lazy=False)
    return individuals


def validate_alignment_records(records: list[AlignmentRecord]) -> list[AlignmentRecord]:
    if records:
        rows = [
            {
                "ontology_class": r.ontology_class,
                "external_uri": r.external_uri,
                "relation": r.relation,
                "source": r.source,
            }
            for r in records
        ]
        ALIGNMENT_SCHEMA.validate(pd.DataFrame(rows), lazy=False)
    return records
