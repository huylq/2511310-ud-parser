"""Politeness-rate-limited crawler for tier=forum_qa_blog sources.

Handed an explicit seed list (e.g. a thread index's URLs) rather than
discovering pages itself -- paginated forum/Q&A structure varies too much
per site for one generic discovery strategy to handle well.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable
from urllib.parse import urlparse

import httpx

from vietnlp.acquisition.rate_limiter import TokenBucket
from vietnlp.acquisition.sources import SourceRecord

DeadLetterSink = Callable[[tuple[dict, str]], None]
Fetcher = Callable[[str], httpx.Response]


def _default_fetch(url: str) -> httpx.Response:
    return httpx.get(url, timeout=15.0)


def crawl_source(
    source: SourceRecord,
    seed_urls: list[str],
    bronze,
    fetch: Fetcher | None = None,
    dead_letter_sink: DeadLetterSink | None = None,
) -> dict:
    """Fetch each URL in `seed_urls`, one token-bucket-paced request at a
    time, writing survivors to Bronze. Returns {"loaded": int,
    "dead_lettered": int}."""
    fetch = fetch or _default_fetch
    domain = urlparse(source.base_url).netloc if source.base_url else None
    bucket = TokenBucket(rate_limit_seconds=source.rate_limit_seconds)

    loaded = 0
    dead_lettered = 0
    for url in seed_urls:
        if domain is not None and urlparse(url).netloc != domain:
            dead_lettered += 1
            if dead_letter_sink is not None:
                dead_letter_sink(({"url": url}, "URL outside source's vetted domain"))
            continue

        bucket.acquire()
        response = fetch(url)
        if response.status_code != 200:
            dead_lettered += 1
            if dead_letter_sink is not None:
                dead_letter_sink(({"url": url}, f"HTTP {response.status_code}"))
            continue
        body = response.text
        if not body.strip():
            dead_lettered += 1
            if dead_letter_sink is not None:
                dead_letter_sink(({"url": url}, "empty response body"))
            continue

        record = {
            "source_id": source.name,
            "url": url,
            "fetched_at": datetime.now(timezone.utc),
            "http_status": response.status_code,
            "robots_decision": "allowed",  # source is enabled: corpus-scout already vetted robots.txt
            "content_type": response.headers.get("content-type", "text/html"),
            "raw_payload": body.encode("utf-8"),
            "license": source.license or "unknown",
        }
        bronze.put_record(record)
        loaded += 1
    return {"loaded": loaded, "dead_lettered": dead_lettered}
