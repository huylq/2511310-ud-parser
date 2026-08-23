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


def test_pending_excludes_applied_versions():
    migrations = [
        Migration("0001", "core", Path("x"), "SQL"),
        Migration("0002", "more", Path("y"), "SQL"),
    ]
    assert [m.version for m in pending({"0001"}, migrations)] == ["0002"]


def test_pending_with_nothing_applied_returns_everything():
    migrations = [Migration("0001", "core", Path("x"), "SQL")]
    assert pending(set(), migrations) == migrations
