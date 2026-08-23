"""Migration ordering and discovery are pure logic -- tested without a database."""

from pathlib import Path

import pytest

from vietnlp.platform.db.migrate import Migration, list_migrations, pending


def _write(dir_, filename, sql="SELECT 1;"):
    (dir_ / filename).write_text(sql)


def test_list_migrations_sorts_by_version(tmp_path):
    _write(tmp_path, "0002_second.sql")
    _write(tmp_path, "0001_first.sql")
    migrations = list_migrations(tmp_path)
    assert [m.version for m in migrations] == ["0001", "0002"]
    assert [m.name for m in migrations] == ["first", "second"]


def test_list_migrations_rejects_misnamed_file(tmp_path):
    _write(tmp_path, "not-a-migration.sql")
    with pytest.raises(ValueError, match="does not match"):
        list_migrations(tmp_path)


def test_list_migrations_rejects_duplicate_version(tmp_path):
    _write(tmp_path, "0001_first.sql")
    _write(tmp_path, "0001_also_first.sql")
    with pytest.raises(ValueError, match="duplicate migration version"):
        list_migrations(tmp_path)


def test_list_migrations_rejects_missing_directory(tmp_path):
    with pytest.raises(FileNotFoundError):
        list_migrations(migrations_dir=tmp_path / "does-not-exist")


def test_pending_excludes_applied_versions():
    migrations = [
        Migration("0001", "core", Path("x"), "SQL"),
        Migration("0002", "more", Path("y"), "SQL"),
    ]
    assert [m.version for m in pending({"0001"}, migrations)] == ["0002"]


def test_pending_with_nothing_applied_returns_everything():
    migrations = [Migration("0001", "core", Path("x"), "SQL")]
    assert pending(set(), migrations) == migrations


import os

import psycopg
from urllib.parse import quote

from vietnlp.platform.db.migrate import DEFAULT_DATABASE_URL, apply, status


def _live_database_url() -> str | None:
    url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    try:
        with psycopg.connect(url, connect_timeout=2):
            return url
    except psycopg.OperationalError:
        return None


@pytest.fixture
def live_db():
    url = _live_database_url()
    if url is None:
        pytest.skip("no reachable Postgres (DATABASE_URL); run with the stack up to exercise this")
    # Isolate into a fresh schema so this test is safe to run repeatedly
    # against the real deployed database, not just a throwaway one.
    schema = f"migrate_test_{os.getpid()}"
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
        conn.execute(f"CREATE SCHEMA {schema}")
    scoped_url = f"{url}?options={quote(f'-c search_path={schema},public')}"
    yield scoped_url
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")


def test_apply_creates_every_table_from_0001(live_db):
    applied = apply(live_db)
    assert "0001" in applied

    with psycopg.connect(live_db) as conn:
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = current_schema()"
            ).fetchall()
        }
    expected = {
        "sources", "documents", "sentences", "tokens", "annotation_runs",
        "entities", "mentions", "logical_forms", "embeddings", "dead_letters",
        "schema_migrations",
    }
    assert expected <= tables


def test_apply_is_idempotent(live_db):
    first = apply(live_db)
    second = apply(live_db)
    assert first == ["0001"]
    assert second == [], "re-applying must be a no-op"


def test_status_reports_applied_migrations(live_db):
    apply(live_db)
    rows = status(live_db)
    assert ("0001", "core_schema", True) in rows


def test_apply_keeps_earlier_migrations_when_a_later_one_fails(tmp_path, live_db):
    # Each migration must commit independently: a failure in migration 0002
    # must not roll back the 0001 work that already succeeded in this same
    # apply() call.
    _write(tmp_path, "0001_ok.sql", "CREATE TABLE ok_table (id INT);")
    _write(tmp_path, "0002_bad.sql", "THIS IS NOT VALID SQL;")

    with pytest.raises(psycopg.Error):
        apply(live_db, migrations_dir=tmp_path)

    rows = status(live_db, migrations_dir=tmp_path)
    applied = {version: is_applied for version, _, is_applied in rows}
    assert applied["0001"] is True, "migration 0001 should have committed before 0002 failed"
    assert applied["0002"] is False, "migration 0002 must not be recorded as applied"

    with psycopg.connect(live_db) as conn:
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = current_schema()"
            ).fetchall()
        }
    assert "ok_table" in tables, "0001's DDL must have actually committed, not just its bookkeeping row"
