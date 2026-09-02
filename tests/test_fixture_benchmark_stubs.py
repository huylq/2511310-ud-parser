"""Contract for `tests/fixtures/benchmark/*_stub.jsonl` -- see
`tests/fixtures/benchmark/README.md` for what these are and are not.
"""
import json
from pathlib import Path

BENCHMARK_DIR = Path(__file__).parent / "fixtures" / "benchmark"

_NER_LABELS = {"O", "B-PER", "I-PER", "B-LOC", "I-LOC", "B-ORG", "I-ORG", "B-MISC", "I-MISC"}
_SENTIMENTS = {"positive", "negative", "neutral"}


def _load(name: str) -> list[dict]:
    path = BENCHMARK_DIR / f"{name}_stub.jsonl"
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def test_all_three_stub_files_exist():
    for name in ("vlsp_ner", "uit_vsfc", "viquad"):
        assert (BENCHMARK_DIR / f"{name}_stub.jsonl").exists()


def test_every_row_carries_a_nonempty_stub_note():
    for name in ("vlsp_ner", "uit_vsfc", "viquad"):
        for row in _load(name):
            assert row.get("stub_note", "").strip(), f"{name}: row missing stub_note"


def test_vlsp_ner_between_10_and_20_rows_with_matching_tag_lengths():
    rows = _load("vlsp_ner")
    assert 10 <= len(rows) <= 20
    for row in rows:
        assert len(row["tokens"]) == len(row["ner_tags"])
        assert all(tag in _NER_LABELS for tag in row["ner_tags"])
    # required input classes: at least one row with no entities, one with a single-token entity
    assert any(all(tag == "O" for tag in row["ner_tags"]) for row in rows)
    assert any(len(row["tokens"]) == 2 for row in rows)


def test_uit_vsfc_between_10_and_20_rows_with_valid_sentiment():
    rows = _load("uit_vsfc")
    assert 10 <= len(rows) <= 20
    for row in rows:
        assert row["sentiment"] in _SENTIMENTS
        assert "text" in row
    # required input classes: at least one degenerate (empty text), one non-diacritic register
    assert any(row["text"] == "" for row in rows)
    assert any(row["text"] and row["text"].isascii() for row in rows)


def test_viquad_between_10_and_20_rows_with_correct_answer_offsets():
    rows = _load("viquad")
    assert 10 <= len(rows) <= 20
    for row in rows:
        start = row["answer_start"]
        end = start + len(row["answer_text"])
        assert row["context"][start:end] == row["answer_text"], row["question"]
