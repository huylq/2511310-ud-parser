"""Source vetting record: corpus-scout's authorization gate for acquisition.
Live-Postgres tests, self-skipping under --no-deps (see conftest.py).

Each test calls apply(live_db) first, exactly like test_db_migrate.py's live
tests: that creates the `sources` table inside this test's own isolated
schema (unqualified CREATE TABLE resolves to the first entry on
search_path), so every unqualified INSERT/SELECT ... FROM sources this
module's functions issue resolve there too, instead of falling through to
the real public.sources table."""
import pytest

from vietnlp.acquisition.sources import SourceError, get_source, list_enabled_sources, register_source
from vietnlp.platform.db.migrate import apply


def test_register_then_get_round_trips(live_db):
    apply(live_db)
    register_source(live_db, "test-news", "news_gov_wiki", base_url="https://news.example.vn", license="cc-by")
    record = get_source(live_db, "test-news")
    assert record.name == "test-news"
    assert record.tier == "news_gov_wiki"
    assert record.base_url == "https://news.example.vn"
    assert record.enabled is True
    assert record.rate_limit_seconds == 5  # default


def test_register_rejects_unknown_tier(live_db):
    apply(live_db)
    with pytest.raises(SourceError, match="tier"):
        register_source(live_db, "test-bad-tier", "not_a_real_tier")


def test_get_source_raises_for_unregistered_name(live_db):
    apply(live_db)
    with pytest.raises(SourceError, match="no source named"):
        get_source(live_db, "never-registered")


def test_register_is_idempotent_by_name(live_db):
    apply(live_db)
    register_source(live_db, "test-idempotent", "public_corpus", rate_limit_seconds=5)
    register_source(live_db, "test-idempotent", "public_corpus", rate_limit_seconds=10)
    record = get_source(live_db, "test-idempotent")
    assert record.rate_limit_seconds == 10  # second registration updates, doesn't duplicate


def test_list_enabled_sources_excludes_disabled(live_db):
    apply(live_db)
    register_source(live_db, "test-enabled", "forum_qa_blog", enabled=True)
    register_source(live_db, "test-disabled", "forum_qa_blog", enabled=False)
    names = {s.name for s in list_enabled_sources(live_db, tier="forum_qa_blog")}
    assert "test-enabled" in names
    assert "test-disabled" not in names


def test_list_enabled_sources_filters_by_tier(live_db):
    apply(live_db)
    register_source(live_db, "test-tier-a", "news_gov_wiki")
    register_source(live_db, "test-tier-b", "public_corpus")
    names = {s.name for s in list_enabled_sources(live_db, tier="news_gov_wiki")}
    assert "test-tier-a" in names
    assert "test-tier-b" not in names
