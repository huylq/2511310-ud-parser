"""Web discovery + extraction, for tier=news_gov_wiki sources.

Calls web_search (the z.ai MCP client) to find candidate URLs under the
source's vetted domain, then web_read to extract clean text from each,
writing every extracted document to Bronze.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable
from urllib.parse import urlparse

from vietnlp.acquisition.mcp_client import MCPError, web_read, web_search
from vietnlp.acquisition.sources import SourceRecord

DeadLetterSink = Callable[[tuple[dict, str]], None]


def discover_and_extract(
    source: SourceRecord,
    query: str,
    bronze,
    max_results: int = 10,
    dead_letter_sink: DeadLetterSink | None = None,
) -> dict:
    """Search `query` scoped to `source.base_url`'s domain, extract each
    hit, write to Bronze. Returns {"loaded": int, "dead_lettered": int}."""
    if not source.base_url:
        raise ValueError(f"source {source.name!r} has no base_url; cannot scope discovery")
    domain = urlparse(source.base_url).netloc

    hits = web_search(f"{query} site:{domain}", count=max_results)

    loaded = 0
    dead_lettered = 0
    for hit in hits:
        url = hit.get("url")
        if not url or urlparse(url).netloc != domain:
            dead_lettered += 1
            if dead_letter_sink is not None:
                dead_letter_sink((hit, "search result outside source's vetted domain"))
            continue
        try:
            text = web_read(url)
        except MCPError as exc:
            dead_lettered += 1
            if dead_letter_sink is not None:
                dead_letter_sink((hit, str(exc)))
            continue
        if not text.strip():
            dead_lettered += 1
            if dead_letter_sink is not None:
                dead_letter_sink((hit, "web_read returned empty text"))
            continue

        record = {
            "source_id": source.name,
            "url": url,
            "fetched_at": datetime.now(timezone.utc),
            "http_status": 200,
            "robots_decision": "allowed",  # source is enabled: corpus-scout already vetted robots.txt
            "content_type": "text/plain; charset=utf-8",
            "raw_payload": text.encode("utf-8"),
            "license": source.license or "unknown",
        }
        bronze.put_record(record)
        loaded += 1
    return {"loaded": loaded, "dead_lettered": dead_lettered}
