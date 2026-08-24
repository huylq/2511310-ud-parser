"""Offline: monkeypatches web_search/web_read (Task 5's module-level
functions) and fakes BronzeStore, so no live network or MinIO is needed."""
from vietnlp.acquisition.loaders.web_discovery import discover_and_extract
from vietnlp.acquisition.mcp_client import MCPError
from vietnlp.acquisition.sources import SourceRecord


class _FakeBronzeStore:
    def __init__(self):
        self.records: list[dict] = []

    def put_record(self, record: dict) -> str:
        self.records.append(record)
        return f"bronze/fake/{len(self.records)}.parquet"


def _source(**overrides) -> SourceRecord:
    defaults = dict(
        id=1, name="test-news", tier="news_gov_wiki", base_url="https://news.example.vn",
        license="cc-by", robots_policy="allowed", enabled=True, rate_limit_seconds=5,
    )
    defaults.update(overrides)
    return SourceRecord(**defaults)


def test_extracts_every_in_domain_hit(monkeypatch):
    hits = [
        {"url": "https://news.example.vn/a", "title": "A"},
        {"url": "https://news.example.vn/b", "title": "B"},
    ]
    monkeypatch.setattr("vietnlp.acquisition.loaders.web_discovery.web_search", lambda q, count=10: hits)
    monkeypatch.setattr("vietnlp.acquisition.loaders.web_discovery.web_read", lambda url: f"content of {url}")

    bronze = _FakeBronzeStore()
    result = discover_and_extract(_source(), "tin tuc hom nay", bronze)
    assert result == {"loaded": 2, "dead_lettered": 0}
    assert bronze.records[0]["url"] == "https://news.example.vn/a"
    assert bronze.records[0]["raw_payload"] == b"content of https://news.example.vn/a"


def test_dead_letters_hits_outside_the_source_domain(monkeypatch):
    hits = [{"url": "https://not-the-vetted-domain.example/a", "title": "A"}]
    monkeypatch.setattr("vietnlp.acquisition.loaders.web_discovery.web_search", lambda q, count=10: hits)
    monkeypatch.setattr(
        "vietnlp.acquisition.loaders.web_discovery.web_read",
        lambda url: (_ for _ in ()).throw(AssertionError("should not extract an out-of-domain hit")),
    )

    bronze = _FakeBronzeStore()
    caught = []
    result = discover_and_extract(_source(), "query", bronze, dead_letter_sink=caught.append)
    assert result == {"loaded": 0, "dead_lettered": 1}
    assert "outside" in caught[0][1]


def test_dead_letters_on_extraction_failure(monkeypatch):
    hits = [{"url": "https://news.example.vn/broken", "title": "Broken"}]
    monkeypatch.setattr("vietnlp.acquisition.loaders.web_discovery.web_search", lambda q, count=10: hits)

    def _raise(url):
        raise MCPError("extraction failed")

    monkeypatch.setattr("vietnlp.acquisition.loaders.web_discovery.web_read", _raise)

    bronze = _FakeBronzeStore()
    result = discover_and_extract(_source(), "query", bronze)
    assert result == {"loaded": 0, "dead_lettered": 1}


def test_dead_letters_empty_extracted_text(monkeypatch):
    hits = [{"url": "https://news.example.vn/empty", "title": "Empty"}]
    monkeypatch.setattr("vietnlp.acquisition.loaders.web_discovery.web_search", lambda q, count=10: hits)
    monkeypatch.setattr("vietnlp.acquisition.loaders.web_discovery.web_read", lambda url: "   ")

    bronze = _FakeBronzeStore()
    result = discover_and_extract(_source(), "query", bronze)
    assert result == {"loaded": 0, "dead_lettered": 1}


def test_raises_if_source_has_no_base_url(monkeypatch):
    import pytest
    monkeypatch.setattr("vietnlp.acquisition.loaders.web_discovery.web_search", lambda q, count=10: [])
    with pytest.raises(ValueError, match="base_url"):
        discover_and_extract(_source(base_url=None), "query", _FakeBronzeStore())
