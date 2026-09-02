"""Contract for `serving/gold_fixture.json` -- Project 8's static, offline
substrate (see `tests/fixtures/generate_gold_fixture.py`). Every document
row must construct into a valid `interfaces.serving.DocumentResponse`, and
every mention must reference a real sentence and a real entity within the
same document -- referential integrity a live Postgres would enforce with
foreign keys, checked here by hand since this is a flat JSON file.
"""
import json
from pathlib import Path

from vietnlp.interfaces.serving import DocumentResponse, EntityResponse, SentenceResponse, validate_document_response

GOLD_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "serving" / "gold_fixture.json"


def _load() -> list[dict]:
    with GOLD_FIXTURE_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def test_gold_fixture_file_exists():
    assert GOLD_FIXTURE_PATH.exists(), "run tests/fixtures/generate_gold_fixture.py"


def test_has_exactly_100_documents():
    assert len(_load()) == 100


def test_document_ids_are_unique_and_dense():
    docs = _load()
    ids = sorted(d["id"] for d in docs)
    assert ids == list(range(1, len(docs) + 1))


def test_every_document_round_trips_through_the_serving_contract():
    for doc in _load():
        response = DocumentResponse(
            id=doc["id"], content_hash=doc["content_hash"], url=doc["url"], lang=doc["lang"],
            register=doc["register"], quality_score=doc["quality_score"],
            sentences=tuple(SentenceResponse(**s) for s in doc["sentences"]),
            entities=tuple(
                EntityResponse(id=e["id"], canonical_name=e["canonical_name"], ontology_class=e["ontology_class"],
                                wikidata_qid=e["wikidata_qid"], posterior=e["posterior"])
                for e in doc["entities"]
            ),
        )
        validate_document_response(response)


def test_every_mention_references_a_sentence_and_entity_in_the_same_document():
    for doc in _load():
        sentence_ids = {s["id"] for s in doc["sentences"]}
        entity_ids = {e["id"] for e in doc["entities"]}
        for mention in doc["mentions"]:
            assert mention["sentence_id"] in sentence_ids
            assert mention["entity_id"] in entity_ids
            assert mention["token_end"] > mention["token_start"]


def test_entity_and_sentence_ids_are_globally_unique_across_documents():
    docs = _load()
    all_entity_ids = [e["id"] for d in docs for e in d["entities"]]
    all_sentence_ids = [s["id"] for d in docs for s in d["sentences"]]
    assert len(all_entity_ids) == len(set(all_entity_ids))
    assert len(all_sentence_ids) == len(set(all_sentence_ids))


def test_every_entity_ontology_class_is_a_known_stub_class():
    known = {"Person", "Place", "Organization", "Thing"}
    for doc in _load():
        for entity in doc["entities"]:
            assert entity["ontology_class"] in known
