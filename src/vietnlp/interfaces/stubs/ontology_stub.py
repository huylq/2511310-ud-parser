"""Deterministic, naive stub for Project 5's output -- unblocks Projects
6, 7, 8, 9.

Maps `interfaces.ner.NamedEntity.label` to one ontology class through a
fixed lookup table -- no reasoning, no disambiguation among near-duplicate
names, `wikidata_qid` always `None`. NOT a reference implementation:
Project 5's real job (per `.claude/agents/ontology-engineer.md`) is
exactly the modelling decisions this stub skips -- e.g. kinship terms as
properties on one Person class, not sibling classes.
"""

from __future__ import annotations

from vietnlp.interfaces.ner import NamedEntity
from vietnlp.interfaces.ontology import OntologyIndividual

_LABEL_TO_CLASS = {
    "PER": "Person",
    "LOC": "Place",
    "ORG": "Organization",
    "MISC": "Thing",
}


def stub_individual(entity: NamedEntity) -> OntologyIndividual:
    return OntologyIndividual(
        entity_id=entity.mention_id,
        ontology_class=_LABEL_TO_CLASS.get(entity.label, "Thing"),
        wikidata_qid=None,
        source="stub",
    )
