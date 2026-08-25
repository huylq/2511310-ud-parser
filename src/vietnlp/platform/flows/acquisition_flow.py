"""Acquisition orchestration: dispatches to the loader matching a vetted
source's tier. The kill switch is structural, not conventional -- a
disabled source's `get_source` call raises before any loader runs, on
every invocation, so disabling a source mid-run stops the very next
retry.
"""

from __future__ import annotations

from pathlib import Path

from prefect import flow

from vietnlp.acquisition.loaders.crawler import crawl_source
from vietnlp.acquisition.loaders.public_corpus import load_jsonl_corpus
from vietnlp.acquisition.loaders.web_discovery import discover_and_extract
from vietnlp.acquisition.sources import SourceError, get_source


@flow(name="acquisition")
def acquisition_flow(
    source_name: str,
    database_url: str,
    bronze,
    *,
    jsonl_path: Path | None = None,
    query: str | None = None,
    seed_urls: list[str] | None = None,
) -> dict:
    source = get_source(database_url, source_name)
    if not source.enabled:
        raise SourceError(f"source {source_name!r} is not enabled; refusing to acquire")

    if source.tier == "public_corpus":
        if jsonl_path is None:
            raise ValueError("tier=public_corpus requires jsonl_path")
        return load_jsonl_corpus(jsonl_path, source, bronze)

    if source.tier == "news_gov_wiki":
        if query is None:
            raise ValueError("tier=news_gov_wiki requires query")
        return discover_and_extract(source, query, bronze)

    if source.tier == "forum_qa_blog":
        if seed_urls is None:
            raise ValueError("tier=forum_qa_blog requires seed_urls")
        return crawl_source(source, seed_urls, bronze)

    raise SourceError(f"tier {source.tier!r} has no acquisition path (social is P6, permanently off)")
