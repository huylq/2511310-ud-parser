"""Contract for Project 7 (OUPM Entity Resolution), consumed by Project 8
(serving) and Project 9 (export/benchmark).

Mirrors `entities.canonical_name/ontology_class/posterior` in
`platform/db/migrations/0001_core_schema.sql`. `mention_ids` links back to
`interfaces.ner.NamedEntity.mention_id` values -- an `EntityCluster` is a
claim that a set of mentions, possibly from different documents, refer to
the same real-world entity, which is exactly what P4's open-universe model
(unknown entity count, MCMC) is inferring. Per
`.claude/agents/oupm-modeler.md`: a bare surname match (`Nguyen` collides on
~40% of Vietnamese names) is near-worthless evidence on its own --
`validate_entity_cluster` cannot check for that kind of reasoning quality,
only structural well-formedness; the golden-file test against
`tests/fixtures/corpus/oupm_coref_probe.jsonl`'s gold clustering is what
actually measures clustering quality (B3/CEAF/MUC).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ._common import SOURCE_VALUES

SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class EntityCluster:
    cluster_id: str
    canonical_name: str
    ontology_class: str | None
    mention_ids: tuple[str, ...]       # interfaces.ner.NamedEntity.mention_id values
    posterior: float = 1.0              # mirrors entities.posterior; P(cluster is a genuine entity)
    source: Literal["stub", "real"] = "stub"


def validate_entity_cluster(cluster: EntityCluster, known_mention_ids: set[str] | None = None) -> EntityCluster:
    """Raises `ValueError` if: the cluster has no mentions; `posterior` is
    outside [0, 1]; or (when `known_mention_ids` is supplied by the caller)
    a referenced mention was never produced by NER -- the same
    reference-integrity check `interfaces.ner.validate_coref_chain` applies,
    reused here because OUPM clusters and coref chains are both consumers of
    the same `NamedEntity.mention_id` addressing scheme."""
    if cluster.source not in SOURCE_VALUES:
        raise ValueError(f"EntityCluster {cluster.cluster_id!r}: source {cluster.source!r} invalid")
    if not cluster.mention_ids:
        raise ValueError(f"EntityCluster {cluster.cluster_id!r} has zero mentions")
    if not 0.0 <= cluster.posterior <= 1.0:
        raise ValueError(f"EntityCluster {cluster.cluster_id!r}: posterior {cluster.posterior} outside [0,1]")
    if known_mention_ids is not None:
        missing = [m for m in cluster.mention_ids if m not in known_mention_ids]
        if missing:
            raise ValueError(f"EntityCluster {cluster.cluster_id!r} references unknown mention(s): {missing}")
    return cluster
