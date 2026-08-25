"""Acquisition orchestration: dispatches to the loader matching a vetted
source's tier. The kill switch is structural, not conventional -- a
disabled source's `get_source` call raises before any loader runs, on
every invocation, so disabling a source mid-run stops the very next
retry.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from prefect import flow

from vietnlp.acquisition.loaders.crawler import crawl_source
from vietnlp.acquisition.loaders.public_corpus import load_jsonl_corpus
from vietnlp.acquisition.loaders.web_discovery import discover_and_extract
from vietnlp.acquisition.sources import SourceError, get_source

DeadLetterSink = Callable[[tuple[dict, str]], None]


@flow(name="acquisition")
def acquisition_flow(
    source_name: str,
    database_url: str,
    bronze,
    *,
    jsonl_path: Path | None = None,
    query: str | None = None,
    seed_urls: list[str] | None = None,
    dead_letter_sink: DeadLetterSink | None = None,
) -> dict:
    source = get_source(database_url, source_name)
    if not source.enabled:
        raise SourceError(f"source {source_name!r} is not enabled; refusing to acquire")

    if source.tier == "public_corpus":
        if jsonl_path is None:
            raise ValueError("tier=public_corpus requires jsonl_path")
        return load_jsonl_corpus(jsonl_path, source, bronze, dead_letter_sink=dead_letter_sink)

    if source.tier == "news_gov_wiki":
        if query is None:
            raise ValueError("tier=news_gov_wiki requires query")
        return discover_and_extract(source, query, bronze, dead_letter_sink=dead_letter_sink)

    if source.tier == "forum_qa_blog":
        if seed_urls is None:
            raise ValueError("tier=forum_qa_blog requires seed_urls")
        return crawl_source(source, seed_urls, bronze, dead_letter_sink=dead_letter_sink)

    raise SourceError(f"tier {source.tier!r} has no acquisition path (social is P6, permanently off)")


def main(argv: list[str] | None = None) -> int:
    import os
    import sys

    import psycopg

    from vietnlp.platform.db.migrate import DEFAULT_DATABASE_URL
    from vietnlp.platform.storage.bronze import BronzeStore

    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(
            "usage: python -m vietnlp.platform.flows.acquisition_flow SOURCE_NAME "
            "[--query TEXT] [--jsonl-path PATH]",
            file=sys.stderr,
        )
        return 2
    source_name = argv[0]
    query = argv[argv.index("--query") + 1] if "--query" in argv else None
    jsonl_path = Path(argv[argv.index("--jsonl-path") + 1]) if "--jsonl-path" in argv else None

    database_url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    bronze = BronzeStore.from_env()

    def _dead_letter_sink(item: tuple[dict, str]) -> None:
        record, reason = item
        with psycopg.connect(database_url) as conn:
            conn.execute(
                "INSERT INTO dead_letters (stage, error, payload_uri) VALUES (%s, %s, %s)",
                ("acquisition", reason, record.get("url")),
            )

    result = acquisition_flow(
        source_name,
        database_url,
        bronze,
        query=query,
        jsonl_path=jsonl_path,
        dead_letter_sink=_dead_letter_sink,
    )
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
