"""Deterministic, naive stub for Project 7's output -- unblocks Projects
8, 9.

Clustering policy: reuses `interfaces.ner.CorefChain` groupings 1:1 (one
chain becomes one cluster, exact surface-text match only); any entity
mention with no chain becomes its own singleton cluster. `posterior=1.0`
always. NOT a reference implementation: Project 7's real job (per
`.claude/agents/oupm-modeler.md`) is exactly what this stub skips --
name-variant merging, honorific stripping, and treating a bare surname
match as weak evidence rather than certainty.
"""

from __future__ import annotations

from vietnlp.interfaces.ner import CorefChain, NamedEntity
from vietnlp.interfaces.oupm import EntityCluster


def stub_cluster(entities: list[NamedEntity], chains: list[CorefChain]) -> list[EntityCluster]:
    by_mention = {e.mention_id: e for e in entities}
    chained_mentions = {m for c in chains for m in c.mention_ids}

    clusters = []
    for c in chains:
        first = by_mention.get(c.mention_ids[0])
        canonical_name = first.text if first else c.mention_ids[0]
        clusters.append(
            EntityCluster(
                cluster_id=f"stub-cluster:{c.chain_id}",
                canonical_name=canonical_name,
                ontology_class=None,
                mention_ids=c.mention_ids,
                posterior=1.0,
                source="stub",
            )
        )
    for e in entities:
        if e.mention_id not in chained_mentions:
            clusters.append(
                EntityCluster(
                    cluster_id=f"stub-cluster:{e.mention_id}",
                    canonical_name=e.text,
                    ontology_class=None,
                    mention_ids=(e.mention_id,),
                    posterior=1.0,
                    source="stub",
                )
            )
    return clusters
