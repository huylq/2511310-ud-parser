"""The fixture corpus is the offline substrate for every later test (CLAUDE.md
Working Agreements: "A committed ~100-document fixture corpus keeps the full
pipeline testable without network or API spend"). These tests are its contract.
"""
import json
import unicodedata
from pathlib import Path

from vietnlp.acquisition.fixture_schema import validate_fixture_record

CORPUS_PATH = Path(__file__).parent / "fixtures" / "corpus" / "fixture_corpus.jsonl"


def _load():
    with CORPUS_PATH.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def test_corpus_file_exists():
    assert CORPUS_PATH.exists(), "run tests/fixtures/generate_fixture_corpus.py"


def test_corpus_has_exactly_100_documents():
    assert len(_load()) == 100


def test_every_document_is_fixture_schema_valid():
    for record in _load():
        validate_fixture_record(record)  # raises SchemaError on the first invalid row


def test_content_hashes_are_unique():
    hashes = [r["content_hash"] for r in _load()]
    assert len(hashes) == len(set(hashes))


def test_registers_are_balanced_across_four_categories():
    """CLAUDE.md flags informal/teencode/khong_dau as the registers the corpus
    is otherwise short of; the fixture exercises all four, evenly, so later
    register-balance tests (curation, P1) have a known-good baseline."""
    records = _load()
    counts: dict[str, int] = {}
    for r in records:
        counts[r["register"]] = counts.get(r["register"], 0) + 1
    assert set(counts) == {"formal", "informal", "teencode", "khong_dau"}
    assert all(count == 25 for count in counts.values()), counts


def test_text_is_nfc_normalized():
    for r in _load():
        assert r["text"] == unicodedata.normalize("NFC", r["text"])
