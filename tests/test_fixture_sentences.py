"""Contract for `fixture_sentences.jsonl` -- the sentence-level fixture
Projects 1-3 build against. Purely mechanical (see
`tests/fixtures/generate_fixture_sentences.py`), so these tests exist to
catch drift between it and the 100-document `fixture_corpus.jsonl` it was
generated from, not to test `split_sentences` itself (see
`test_db_sentence_split.py` for that).
"""
import json
from pathlib import Path

CORPUS_PATH = Path(__file__).parent / "fixtures" / "corpus" / "fixture_corpus.jsonl"
SENTENCES_PATH = Path(__file__).parent / "fixtures" / "corpus" / "fixture_sentences.jsonl"


def _load(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def test_sentences_file_exists():
    assert SENTENCES_PATH.exists(), "run tests/fixtures/generate_fixture_sentences.py"


def test_every_sentence_has_a_parent_document():
    doc_hashes = {r["content_hash"] for r in _load(CORPUS_PATH)}
    for sentence in _load(SENTENCES_PATH):
        assert sentence["content_hash"] in doc_hashes


def test_sent_id_matches_the_linguistics_interface_convention():
    for sentence in _load(SENTENCES_PATH):
        assert sentence["sent_id"] == f"{sentence['content_hash']}:{sentence['idx']}"


def test_sent_ids_are_unique():
    ids = [s["sent_id"] for s in _load(SENTENCES_PATH)]
    assert len(ids) == len(set(ids))


def test_char_offsets_recover_the_sentence_text_from_its_document():
    docs_by_hash = {r["content_hash"]: r["text"] for r in _load(CORPUS_PATH)}
    for sentence in _load(SENTENCES_PATH):
        doc_text = docs_by_hash[sentence["content_hash"]]
        assert doc_text[sentence["char_start"]:sentence["char_end"]] == sentence["text"]


def test_sentence_idx_is_dense_and_zero_based_per_document():
    by_doc: dict[str, list[int]] = {}
    for sentence in _load(SENTENCES_PATH):
        by_doc.setdefault(sentence["content_hash"], []).append(sentence["idx"])
    for content_hash, idxs in by_doc.items():
        assert sorted(idxs) == list(range(len(idxs))), content_hash


def test_register_is_carried_through_unaltered_from_the_document():
    docs_by_hash = {r["content_hash"]: r["register"] for r in _load(CORPUS_PATH)}
    for sentence in _load(SENTENCES_PATH):
        assert sentence["register"] == docs_by_hash[sentence["content_hash"]]
