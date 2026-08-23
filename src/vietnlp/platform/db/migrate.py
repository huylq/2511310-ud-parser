"""Postgres schema migrations: numbered SQL files applied once, in order.

Migrations are forward-only and idempotent by construction -- each file is
plain SQL guarded with IF NOT EXISTS where it matters. Postgres is a
projection of Gold (CLAUDE.md rule 3): these migrations shape the projection,
they never carry data-fixing UPDATE or DELETE statements.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

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
