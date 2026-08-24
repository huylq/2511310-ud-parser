"""Content-addressed Bronze storage. Pure helpers are tested offline; the
put/get round trip against a live MinIO is a self-skipping integration test
(see `live_store` below), mirroring the pattern in test_db_migrate.py."""

import hashlib
from datetime import datetime, timedelta, timezone

import pytest

from vietnlp.platform.storage.bronze import (
    BronzeError, BronzeStore, bronze_key, content_hash,
)


def test_content_hash_is_sha256_hex():
    assert content_hash(b"hello") == hashlib.sha256(b"hello").hexdigest()


def test_content_hash_is_stable_for_identical_payload():
    assert content_hash("Xin chào".encode()) == content_hash("Xin chào".encode())


def test_bronze_key_partitions_by_source_and_date():
    when = datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc)
    assert bronze_key("fixture-formal", when, "abc123") == "bronze/fixture-formal/2026-08-23/abc123.parquet"


def test_bronze_key_normalises_to_utc_date():
    """A fetch just before UTC midnight, recorded in a positive-offset local
    time, must not shift onto the wrong day's partition."""
    when = datetime(2026, 8, 24, 6, 0, tzinfo=timezone(timedelta(hours=7)))  # 23:00 UTC on the 23rd
    assert "2026-08-23" in bronze_key("fixture-formal", when, "abc123")


def test_from_env_refuses_to_default_a_secret(monkeypatch):
    monkeypatch.delenv("MINIO_ROOT_USER", raising=False)
    monkeypatch.delenv("MINIO_ROOT_PASSWORD", raising=False)
    with pytest.raises(BronzeError, match="not set"):
        BronzeStore.from_env()


def test_bronze_key_rejects_naive_datetime():
    with pytest.raises(BronzeError, match="naive"):
        bronze_key("fixture-formal", datetime(2026, 8, 23, 12, 0), "abc123")


def test_from_env_rejects_endpoint_without_recognized_scheme(monkeypatch):
    monkeypatch.setenv("MINIO_ROOT_USER", "u")
    monkeypatch.setenv("MINIO_ROOT_PASSWORD", "p")
    monkeypatch.setenv("MINIO_ENDPOINT", "ftp://minio:9000")
    with pytest.raises(BronzeError, match="http"):
        BronzeStore.from_env()


def test_put_then_get_round_trips_a_record(live_store):
    text = "Hà Nội là thủ đô của Việt Nam."
    record = {
        "source_id": "fixture-formal", "url": "https://fixture.local/x",
        "fetched_at": datetime.now(timezone.utc), "http_status": 200,
        "robots_decision": "allowed", "content_type": "text/plain; charset=utf-8",
        "raw_payload": text.encode("utf-8"), "license": "synthetic-fixture",
    }
    key = live_store.put_record(record)
    fetched = live_store.get_record(key)
    assert fetched["raw_payload"] == record["raw_payload"]
    assert fetched["content_hash"] == content_hash(record["raw_payload"])


def test_put_is_idempotent_for_identical_content(live_store):
    record = {
        "source_id": "fixture-formal", "url": "https://fixture.local/y",
        "fetched_at": datetime.now(timezone.utc), "http_status": 200,
        "robots_decision": "allowed", "content_type": "text/plain; charset=utf-8",
        "raw_payload": "Nội dung không đổi.".encode("utf-8"), "license": "synthetic-fixture",
    }
    key1 = live_store.put_record(record)
    key2 = live_store.put_record(record)
    assert key1 == key2, "identical content must resolve to the identical Bronze key"
