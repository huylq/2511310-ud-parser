"""Response cache keyed by (task, prompt_version, model, content hash).

The single largest cost saver in the pipeline. Re-running a flow over the same
Bronze content must not re-bill: Bronze is immutable and content-addressed, so an
identical input under an identical prompt version has an identical answer.

Bumping a prompt version deliberately invalidates that prompt's cache -- which is
the point. Never mutate a prompt without bumping its version, or you will serve
stale answers from the old prompt forever.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS responses (
    key         TEXT PRIMARY KEY,
    task        TEXT NOT NULL,
    model       TEXT NOT NULL,
    prompt_ver  TEXT NOT NULL,
    response    TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    hits        INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS responses_task ON responses(task, prompt_ver);
"""


def cache_key(task: str, prompt_version: str, model: str, payload: str) -> str:
    """Stable key. Payload is hashed, never stored -- it may contain scrubbed text."""
    h = hashlib.sha256()
    for part in (task, prompt_version, model, payload):
        h.update(part.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


class ResponseCache:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(
            db_path or os.getenv("VIETNLP_CACHE_DB", "/data/cache/responses.db")
        )
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            yield conn
            conn.commit()
        finally:
            conn.close()

    def get(self, key: str):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT response FROM responses WHERE key = ?", (key,)
            ).fetchone()
            if row is None:
                return None
            conn.execute("UPDATE responses SET hits = hits + 1 WHERE key = ?", (key,))
        return json.loads(row[0])

    def put(self, key: str, task: str, model: str, prompt_version: str, response) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO responses (key, task, model, prompt_ver, response) "
                "VALUES (?, ?, ?, ?, ?)",
                (key, task, model, prompt_version, json.dumps(response, ensure_ascii=False)),
            )

    def stats(self) -> list[tuple]:
        with self._connect() as conn:
            return conn.execute(
                "SELECT task, prompt_ver, COUNT(*), SUM(hits) FROM responses "
                "GROUP BY task, prompt_ver ORDER BY SUM(hits) DESC"
            ).fetchall()

    def invalidate(self, task: str, prompt_version: str | None = None) -> int:
        """Drop cached responses for a task, optionally one prompt version."""
        with self._connect() as conn:
            if prompt_version is None:
                cur = conn.execute("DELETE FROM responses WHERE task = ?", (task,))
            else:
                cur = conn.execute(
                    "DELETE FROM responses WHERE task = ? AND prompt_ver = ?",
                    (task, prompt_version),
                )
            return cur.rowcount
