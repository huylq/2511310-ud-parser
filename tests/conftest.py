"""Shared pytest fixtures for tests that touch live Postgres or MinIO.

Both fixtures probe for a reachable live dependency and self-skip if it
isn't there, so `pytest -q` (no --no-deps override) stays green without any
service running. `make test-live` proves the same tests pass for real.
"""
import os
from urllib.parse import quote

import psycopg
import pytest

from vietnlp.platform.db.migrate import DEFAULT_DATABASE_URL
from vietnlp.platform.storage.bronze import BronzeError, BronzeStore


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


def _live_store() -> BronzeStore | None:
    try:
        store = BronzeStore.from_env()
    except BronzeError:
        return None
    try:
        store.client().list_buckets()
    except Exception:
        return None
    return store


@pytest.fixture
def live_store():
    store = _live_store()
    if store is None:
        pytest.skip("no reachable MinIO (MINIO_ENDPOINT/credentials); run with the stack up")
    store.bucket = f"vietnlp-bronze-test-{os.getpid()}"
    yield store
    try:
        client = store.client()
        for obj in client.list_objects(store.bucket, recursive=True):
            client.remove_object(store.bucket, obj.object_name)
        client.remove_bucket(store.bucket)
    except Exception:
        pass  # best-effort cleanup of a throwaway test bucket, not the real store
