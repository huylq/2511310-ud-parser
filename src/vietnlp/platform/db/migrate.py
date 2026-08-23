"""Postgres schema migrations: numbered SQL files applied once, in order.

Migrations are forward-only and idempotent by construction -- each file is
plain SQL guarded with IF NOT EXISTS where it matters. Postgres is a
projection of Gold (CLAUDE.md rule 3): these migrations shape the projection,
they never carry data-fixing UPDATE or DELETE statements.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

import psycopg

DEFAULT_MIGRATIONS_DIR = Path(__file__).parent / "migrations"
# Local-dev convenience only, reachable via `make tunnel`. Never a secret default.
DEFAULT_DATABASE_URL = "postgresql://vietnlp:vietnlp@localhost:6042/vietnlp"

_FILENAME = re.compile(r"^(?P<version>\d{4})_(?P<name>[a-z0-9_]+)\.sql$")


@dataclass(frozen=True)
class Migration:
    version: str
    name: str
    path: Path
    sql: str


def list_migrations(migrations_dir: Path = DEFAULT_MIGRATIONS_DIR) -> list[Migration]:
    """All migrations in the directory, sorted by version.

    A filename outside the NNNN_name.sql pattern is rejected rather than
    silently skipped -- a typo'd filename that never runs is worse than one
    that fails loudly at discovery time.
    """
    if not migrations_dir.is_dir():
        raise FileNotFoundError(f"migrations directory not found: {migrations_dir}")
    migrations = []
    for path in sorted(migrations_dir.glob("*.sql")):
        m = _FILENAME.match(path.name)
        if not m:
            raise ValueError(f"migration filename {path.name!r} does not match NNNN_name.sql")
        migrations.append(
            Migration(version=m["version"], name=m["name"], path=path, sql=path.read_text())
        )
    versions = [m.version for m in migrations]
    if len(versions) != len(set(versions)):
        raise ValueError(f"duplicate migration version among {versions}")
    return sorted(migrations, key=lambda m: m.version)


def pending(applied: set[str], migrations: list[Migration]) -> list[Migration]:
    """Migrations not yet recorded as applied, in the order they must run."""
    return [m for m in migrations if m.version not in applied]


def _ensure_bookkeeping(conn: psycopg.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version    TEXT PRIMARY KEY,
            name       TEXT NOT NULL,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )


def _applied_versions(conn: psycopg.Connection) -> set[str]:
    rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
    return {r[0] for r in rows}


def apply(database_url: str, migrations_dir: Path = DEFAULT_MIGRATIONS_DIR) -> list[str]:
    """Apply every pending migration, each in its own transaction.

    Returns the versions applied, in order. Migrations already recorded in
    schema_migrations are left untouched -- this is what makes re-running
    `up` after a partial failure safe.
    """
    migrations = list_migrations(migrations_dir)
    applied_now: list[str] = []
    with psycopg.connect(database_url, autocommit=False) as conn:
        _ensure_bookkeeping(conn)
        conn.commit()
        already = _applied_versions(conn)
        conn.commit()
        for m in pending(already, migrations):
            with conn.transaction():
                conn.execute(m.sql)
                conn.execute(
                    "INSERT INTO schema_migrations (version, name) VALUES (%s, %s)",
                    (m.version, m.name),
                )
            applied_now.append(m.version)
    return applied_now


def status(database_url: str, migrations_dir: Path = DEFAULT_MIGRATIONS_DIR) -> list[tuple[str, str, bool]]:
    migrations = list_migrations(migrations_dir)
    with psycopg.connect(database_url) as conn:
        _ensure_bookkeeping(conn)
        conn.commit()
        already = _applied_versions(conn)
    return [(m.version, m.name, m.version in already) for m in migrations]


def main(argv=None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="vietnlp-migrate")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("up", help="apply pending migrations")
    sub.add_parser("status", help="show which migrations are applied")
    args = parser.parse_args(argv)

    database_url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    if args.cmd == "up":
        applied = apply(database_url)
        print(f"applied: {', '.join(applied)}" if applied else "up to date")
        return 0
    if args.cmd == "status":
        for version, name, is_applied in status(database_url):
            print(f"[{'x' if is_applied else ' '}] {version} {name}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
