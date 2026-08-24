"""Offline: fakes BronzeStore.put_record rather than requiring live MinIO --
end-to-end proof against the real store happens once, holistically, in
Task 10's deploy verification, not per-loader here."""
import json

from vietnlp.acquisition.loaders.public_corpus import load_jsonl_corpus
from vietnlp.acquisition.sources import SourceRecord


class _FakeBronzeStore:
    def __init__(self):
        self.records: list[dict] = []

    def put_record(self, record: dict) -> str:
        self.records.append(record)
        return f"bronze/fake/{len(self.records)}.parquet"


def _source(**overrides) -> SourceRecord:
    defaults = dict(
        id=1, name="test-corpus", tier="public_corpus", base_url=None,
        license="cc-by", robots_policy=None, enabled=True, rate_limit_seconds=5,
    )
    defaults.update(overrides)
    return SourceRecord(**defaults)


def _write_jsonl(tmp_path, lines: list[dict]):
    path = tmp_path / "corpus.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for line in lines:
            f.write(json.dumps(line) + "\n")
    return path


def test_loads_every_valid_line(tmp_path):
    path = _write_jsonl(tmp_path, [
        {"text": "Xin chao Viet Nam.", "url": "https://corpus.example/1", "license": "cc-by"},
        {"text": "Cau thu hai.", "url": "https://corpus.example/2", "license": "cc-by"},
    ])
    bronze = _FakeBronzeStore()
    result = load_jsonl_corpus(path, _source(), bronze)
    assert result == {"loaded": 2, "dead_lettered": 0}
    assert len(bronze.records) == 2
    assert bronze.records[0]["source_id"] == "test-corpus"
    assert bronze.records[0]["raw_payload"] == "Xin chao Viet Nam.".encode("utf-8")


def test_dead_letters_a_line_with_empty_text(tmp_path):
    path = _write_jsonl(tmp_path, [{"text": "", "url": "https://corpus.example/1"}])
    bronze = _FakeBronzeStore()
    caught = []
    result = load_jsonl_corpus(path, _source(), bronze, dead_letter_sink=caught.append)
    assert result == {"loaded": 0, "dead_lettered": 1}
    assert len(caught) == 1


def test_dead_letters_a_line_missing_text_key(tmp_path):
    path = _write_jsonl(tmp_path, [{"url": "https://corpus.example/1"}])
    bronze = _FakeBronzeStore()
    result = load_jsonl_corpus(path, _source(), bronze)
    assert result == {"loaded": 0, "dead_lettered": 1}


def test_falls_back_to_source_license_when_line_omits_it(tmp_path):
    path = _write_jsonl(tmp_path, [{"text": "Noi dung."}])
    bronze = _FakeBronzeStore()
    load_jsonl_corpus(path, _source(license="source-default-license"), bronze)
    assert bronze.records[0]["license"] == "source-default-license"


def test_skips_blank_lines(tmp_path):
    path = tmp_path / "corpus.jsonl"
    path.write_text('{"text": "Mot."}\n\n{"text": "Hai."}\n', encoding="utf-8")
    bronze = _FakeBronzeStore()
    result = load_jsonl_corpus(path, _source(), bronze)
    assert result == {"loaded": 2, "dead_lettered": 0}
