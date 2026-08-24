"""Source vetting record: the authorization gate for acquisition.

A source is not crawled, searched, or bulk-loaded unless it has a row here
with enabled = true. corpus-scout produces these records after checking
robots.txt, license, and register fit -- this module only reads and writes
them, it never decides whether a source should be trusted.

Reuses Postgres's existing `sources` table (P0 migration 0001) rather than
inventing a parallel one. `tier` is constrained by that table's own CHECK
to news_gov_wiki | forum_qa_blog | social | public_corpus -- `social` is
reserved for P6 and this module never registers or dispatches it.
"""

from __future__ import annotations

from dataclasses import dataclass

import psycopg

_TIERS = frozenset({"news_gov_wiki", "forum_qa_blog", "social", "public_corpus"})


class SourceError(RuntimeError):
    pass


@dataclass(frozen=True)
class SourceRecord:
    id: int
    name: str
    tier: str
    base_url: str | None
    license: str | None
    robots_policy: str | None
    enabled: bool
    rate_limit_seconds: int


def register_source(
    database_url: str,
    name: str,
    tier: str,
    *,
    base_url: str | None = None,
    license: str | None = None,
    robots_policy: str | None = None,
    rate_limit_seconds: int = 5,
    enabled: bool = True,
) -> int:
    """Insert or update one source's vetting record by name. Returns its id."""
    if tier not in _TIERS:
        raise SourceError(f"tier {tier!r} not in {sorted(_TIERS)}")
    with psycopg.connect(database_url) as conn:
        row = conn.execute(
            """
            INSERT INTO sources (name, tier, base_url, license, robots_policy, rate_limit_seconds, enabled)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (name) DO UPDATE SET
                tier = EXCLUDED.tier,
                base_url = EXCLUDED.base_url,
                license = EXCLUDED.license,
                robots_policy = EXCLUDED.robots_policy,
                rate_limit_seconds = EXCLUDED.rate_limit_seconds,
                enabled = EXCLUDED.enabled
            RETURNING id
            """,
            (name, tier, base_url, license, robots_policy, rate_limit_seconds, enabled),
        ).fetchone()
        conn.commit()
        return row[0]


def get_source(database_url: str, name: str) -> SourceRecord:
    with psycopg.connect(database_url) as conn:
        row = conn.execute(
            "SELECT id, name, tier, base_url, license, robots_policy, enabled, rate_limit_seconds "
            "FROM sources WHERE name = %s",
            (name,),
        ).fetchone()
    if row is None:
        raise SourceError(f"no source named {name!r}; register it first via register_source()")
    return SourceRecord(*row)


def list_enabled_sources(database_url: str, tier: str | None = None) -> list[SourceRecord]:
    query = (
        "SELECT id, name, tier, base_url, license, robots_policy, enabled, rate_limit_seconds "
        "FROM sources WHERE enabled = true"
    )
    params: tuple = ()
    if tier is not None:
        query += " AND tier = %s"
        params = (tier,)
    query += " ORDER BY name"
    with psycopg.connect(database_url) as conn:
        rows = conn.execute(query, params).fetchall()
    return [SourceRecord(*row) for row in rows]
