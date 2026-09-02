"""Contract for `oupm/oupm_coref_probe.jsonl` + its gold clustering.
Structural checks only -- this file is PROVISIONAL (see
`tests/fixtures/oupm/PROVISIONAL.md`), so these tests catch generator
regressions and referential-integrity breaks, not linguistic quality;
that judgment call is the professor's, per the sign-off checklist.
"""
import json
from pathlib import Path

from vietnlp.interfaces.oupm import EntityCluster, validate_entity_cluster

OUPM_DIR = Path(__file__).parent / "fixtures" / "oupm"


def _cluster_from_gold(cluster: dict) -> EntityCluster:
    return EntityCluster(
        cluster_id=cluster["cluster_id"],
        canonical_name=cluster["canonical_name"],
        ontology_class=None,
        mention_ids=tuple(cluster["mention_ids"]),
        source="stub",
    )


def _load(name: str) -> list[dict]:
    with (OUPM_DIR / name).open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def test_probe_and_gold_files_exist():
    assert (OUPM_DIR / "oupm_coref_probe.jsonl").exists()
    assert (OUPM_DIR / "oupm_coref_probe_gold_clusters.jsonl").exists()


def test_has_exactly_12_documents_in_both_files():
    assert len(_load("oupm_coref_probe.jsonl")) == 12
    assert len(_load("oupm_coref_probe_gold_clusters.jsonl")) == 12


def test_mention_text_matches_its_token_span():
    for doc in _load("oupm_coref_probe.jsonl"):
        tokens_by_sent = {s["sent_idx"]: s["tokens"] for s in doc["sentences"]}
        for m in doc["mentions"]:
            sent_idx = int(m["sent_id"].rsplit(":", 1)[-1])
            tokens = tokens_by_sent[sent_idx]
            span = " ".join(tokens[m["token_start"]:m["token_end"]])
            assert span == m["text"], (doc["doc_id"], m)


def test_mention_ids_are_globally_unique_and_well_formed():
    for doc in _load("oupm_coref_probe.jsonl"):
        ids = [m["mention_id"] for m in doc["mentions"]]
        assert len(ids) == len(set(ids))
        for m in doc["mentions"]:
            assert m["mention_id"] == f"{m['sent_id']}:{m['token_start']}:{m['token_end']}"


def test_every_gold_cluster_references_only_known_mentions_of_the_same_document():
    probes = {d["doc_id"]: d for d in _load("oupm_coref_probe.jsonl")}
    for gold_doc in _load("oupm_coref_probe_gold_clusters.jsonl"):
        known = {m["mention_id"] for m in probes[gold_doc["doc_id"]]["mentions"]}
        for cluster in gold_doc["clusters"]:
            validate_entity_cluster(_cluster_from_gold(cluster), known_mention_ids=known)


def test_every_mention_belongs_to_exactly_one_gold_cluster():
    probes = {d["doc_id"]: d for d in _load("oupm_coref_probe.jsonl")}
    for gold_doc in _load("oupm_coref_probe_gold_clusters.jsonl"):
        all_mentions = {m["mention_id"] for m in probes[gold_doc["doc_id"]]["mentions"]}
        clustered = [mid for c in gold_doc["clusters"] for mid in c["mention_ids"]]
        assert len(clustered) == len(set(clustered)), f"{gold_doc['doc_id']}: a mention appears in >1 cluster"
        assert set(clustered) == all_mentions, f"{gold_doc['doc_id']}: mention/cluster coverage mismatch"


def test_at_least_one_document_has_a_must_not_merge_pair():
    """Sanity check on fixture design intent: at least one document must
    contain two singleton (or otherwise separate) clusters whose canonical
    names share a name component -- the false-positive-avoidance trap."""
    gold_by_doc = {d["doc_id"]: d for d in _load("oupm_coref_probe_gold_clusters.jsonl")}
    doc = gold_by_doc["probe-05-same-name-different-people"]
    per_clusters = [c for c in doc["clusters"] if "Nguyễn Văn Hùng" in c["canonical_name"]]
    assert len(per_clusters) == 2
    assert all(len(c["mention_ids"]) == 1 for c in per_clusters)
