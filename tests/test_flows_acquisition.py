"""Offline via Prefect's official test harness (no server, no network) plus
fakes for the loaders -- consistent with every other flow test in this repo."""
import pytest
from prefect.testing.utilities import prefect_test_harness

from vietnlp.acquisition.sources import SourceError, SourceRecord
from vietnlp.platform.flows.acquisition_flow import acquisition_flow


@pytest.fixture(autouse=True, scope="module")
def _prefect_test_mode():
    with prefect_test_harness():
        yield


class _FakeBronzeStore:
    pass  # never actually touched; the fake loaders below don't call it


def _source(**overrides) -> SourceRecord:
    defaults = dict(
        id=1, name="test-source", tier="public_corpus", base_url=None,
        license="cc-by", robots_policy=None, enabled=True, rate_limit_seconds=5,
    )
    defaults.update(overrides)
    return SourceRecord(**defaults)


def test_dispatches_public_corpus_tier_to_the_jsonl_loader(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "vietnlp.platform.flows.acquisition_flow.get_source",
        lambda database_url, name: _source(tier="public_corpus"),
    )
    called = {}

    def fake_loader(path, source, bronze, dead_letter_sink=None):
        called["path"] = path
        called["source"] = source
        return {"loaded": 5, "dead_lettered": 0}

    monkeypatch.setattr("vietnlp.platform.flows.acquisition_flow.load_jsonl_corpus", fake_loader)

    jsonl = tmp_path / "corpus.jsonl"
    jsonl.write_text("", encoding="utf-8")
    result = acquisition_flow("test-source", "postgresql://fake", _FakeBronzeStore(), jsonl_path=jsonl)
    assert result == {"loaded": 5, "dead_lettered": 0}
    assert called["path"] == jsonl


def test_dispatches_news_gov_wiki_tier_to_web_discovery(monkeypatch):
    monkeypatch.setattr(
        "vietnlp.platform.flows.acquisition_flow.get_source",
        lambda database_url, name: _source(tier="news_gov_wiki", base_url="https://news.example.vn"),
    )
    called = {}

    def fake_discover(source, query, bronze, dead_letter_sink=None):
        called["query"] = query
        return {"loaded": 3, "dead_lettered": 1}

    monkeypatch.setattr("vietnlp.platform.flows.acquisition_flow.discover_and_extract", fake_discover)

    result = acquisition_flow("test-source", "postgresql://fake", _FakeBronzeStore(), query="tin tuc")
    assert result == {"loaded": 3, "dead_lettered": 1}
    assert called["query"] == "tin tuc"


def test_dispatches_forum_qa_blog_tier_to_the_crawler(monkeypatch):
    monkeypatch.setattr(
        "vietnlp.platform.flows.acquisition_flow.get_source",
        lambda database_url, name: _source(tier="forum_qa_blog", base_url="https://forum.example.vn"),
    )
    called = {}

    def fake_crawl(source, seed_urls, bronze, dead_letter_sink=None):
        called["seed_urls"] = seed_urls
        return {"loaded": 2, "dead_lettered": 0}

    monkeypatch.setattr("vietnlp.platform.flows.acquisition_flow.crawl_source", fake_crawl)

    urls = ["https://forum.example.vn/1"]
    result = acquisition_flow("test-source", "postgresql://fake", _FakeBronzeStore(), seed_urls=urls)
    assert result == {"loaded": 2, "dead_lettered": 0}
    assert called["seed_urls"] == urls


def test_refuses_a_disabled_source(monkeypatch):
    """A source flipped to enabled=False must never dispatch a loader --
    this is the structural kill-switch, not a convention."""
    monkeypatch.setattr(
        "vietnlp.platform.flows.acquisition_flow.get_source",
        lambda database_url, name: _source(enabled=False),
    )
    with pytest.raises(SourceError, match="not enabled"):
        acquisition_flow("test-source", "postgresql://fake", _FakeBronzeStore())


def test_refuses_a_source_with_mismatched_tier_arguments(monkeypatch):
    """news_gov_wiki tier with no query given is a caller error, not a
    silent no-op."""
    monkeypatch.setattr(
        "vietnlp.platform.flows.acquisition_flow.get_source",
        lambda database_url, name: _source(tier="news_gov_wiki", base_url="https://news.example.vn"),
    )
    with pytest.raises(ValueError, match="query"):
        acquisition_flow("test-source", "postgresql://fake", _FakeBronzeStore())
