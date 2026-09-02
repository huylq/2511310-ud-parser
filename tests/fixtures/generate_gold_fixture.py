"""Generates `serving/gold_fixture.json` -- Project 8's static, offline
substrate.

Runs the real stub pipeline (`interfaces.stubs.linguistics_stub` ->
`ner_stub` -> `oupm_stub` -> `ontology_stub`) over the full 100-document /
151-sentence fixture corpus and materializes the result into the
`documents` / `sentences` / `entities` / `mentions` shape from
`platform/db/migrations/0001_core_schema.sql` -- JSON instead of a live
Postgres, since CLAUDE.md rule 3 makes Postgres a projection a student
never hand-edits, and Project 8's real handler is meant to query a live
projected DB, not this file. This fixture only stands in for that,
offline, so `TestClient`-based tests never need Docker.

Every field's provenance is "stub" throughout (see `interfaces/`'s
`source` field convention) -- this is real *shape*, not real annotation.

Run: python tests/fixtures/generate_gold_fixture.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from vietnlp.interfaces.stubs import linguistics_stub, ner_stub, ontology_stub, oupm_stub  # noqa: E402

CORPUS_PATH = Path(__file__).parent / "corpus" / "fixture_corpus.jsonl"
SENTENCES_PATH = Path(__file__).parent / "corpus" / "fixture_sentences.jsonl"
OUT_PATH = Path(__file__).parent / "serving" / "gold_fixture.json"


def _load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def build_gold_fixture() -> list[dict]:
    documents = _load_jsonl(CORPUS_PATH)
    sentences_by_doc: dict[str, list[dict]] = {}
    for s in _load_jsonl(SENTENCES_PATH):
        sentences_by_doc.setdefault(s["content_hash"], []).append(s)

    sentence_id = 0
    entity_id = 0
    out_docs = []
    for doc_id, doc in enumerate(documents, start=1):
        doc_sentences = sorted(sentences_by_doc.get(doc["content_hash"], []), key=lambda s: s["idx"])
        out_sentences = []
        doc_mentions = []  # NamedEntity objects, across this document's sentences
        for s in doc_sentences:
            sentence_id += 1
            out_sentences.append({"id": sentence_id, "document_id": doc_id, "idx": s["idx"], "text": s["text"]})
            segmented = linguistics_stub.stub_segment(s["sent_id"], s["register"], s["text"])
            doc_mentions.extend(ner_stub.stub_extract_entities(segmented))

        chains = ner_stub.stub_coref(doc_mentions)
        clusters = oupm_stub.stub_cluster(doc_mentions, chains)
        by_mention = {m.mention_id: m for m in doc_mentions}
        sentence_id_by_idx = {o["idx"]: o["id"] for o in out_sentences}

        out_entities = []
        out_mentions = []
        # Sort for determinism -- makes re-runs byte-identical even if a
        # future stub's internal iteration order changes.
        for cluster in sorted(clusters, key=lambda c: c.cluster_id):
            entity_id += 1
            first = by_mention[cluster.mention_ids[0]]
            ontology_class = ontology_stub.stub_individual(first).ontology_class
            out_entities.append({
                "id": entity_id,
                "canonical_name": cluster.canonical_name,
                "ontology_class": ontology_class,
                "wikidata_qid": None,
                "posterior": cluster.posterior,
            })
            for mid in cluster.mention_ids:
                m = by_mention[mid]
                sent_idx = int(m.sent_id.rsplit(":", 1)[-1])
                out_mentions.append({
                    "sentence_id": sentence_id_by_idx[sent_idx],
                    "token_start": m.token_start,
                    "token_end": m.token_end,
                    "entity_id": entity_id,
                    "confidence": 1.0,
                })

        out_docs.append({
            "id": doc_id,
            "content_hash": doc["content_hash"],
            "url": doc["url"],
            "lang": "vi",
            "register": doc["register"],
            "quality_score": None,
            "sentences": out_sentences,
            "entities": out_entities,
            "mentions": out_mentions,
        })
    return out_docs


def main() -> None:
    docs = build_gold_fixture()
    assert len(docs) == 100, f"expected 100 documents, got {len(docs)}"
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    n_sentences = sum(len(d["sentences"]) for d in docs)
    n_entities = sum(len(d["entities"]) for d in docs)
    n_mentions = sum(len(d["mentions"]) for d in docs)
    print(f"wrote {len(docs)} documents / {n_sentences} sentences / {n_entities} entities / "
          f"{n_mentions} mentions to {OUT_PATH}")


if __name__ == "__main__":
    main()
