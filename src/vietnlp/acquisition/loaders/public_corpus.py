"""Loads a local, pre-downloaded public-corpus JSONL dump into Bronze.

Public corpora (OSCAR/CC-100 Vietnamese, Wikipedia dumps, VLSP/UIT
datasets) are downloaded out-of-band -- they are large, licensed bulk
files, not something this loader fetches itself.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from vietnlp.acquisition.sources import SourceRecord

DeadLetterSink = Callable[[tuple[dict, str]], None]


def load_jsonl_corpus(
    path: Path,
    source: SourceRecord,
    bronze,
    dead_letter_sink: DeadLetterSink | None = None,
) -> dict:
    """Read `path`'s JSONL lines and write each as a Bronze record.

    Returns {"loaded": int, "dead_lettered": int}.
    """
    loaded = 0
    dead_lettered = 0
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            text = raw.get("text")
            if not text:
                dead_lettered += 1
                if dead_letter_sink is not None:
                    dead_letter_sink((raw, "missing or empty 'text' field"))
                continue

            record = {
                "source_id": source.name,
                "url": raw.get("url") or f"corpus://{source.name}",
                "fetched_at": datetime.now(timezone.utc),
                "http_status": 200,
                "robots_decision": "no_robots",
                "content_type": "text/plain; charset=utf-8",
                "raw_payload": text.encode("utf-8"),
                "license": raw.get("license") or source.license or "unknown",
            }
            bronze.put_record(record)
            loaded += 1
    return {"loaded": loaded, "dead_lettered": dead_lettered}
