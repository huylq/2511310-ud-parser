"""Content-addressed Bronze storage on MinIO.

Bronze is immutable (CLAUDE.md rule 1): every object key is derived from the
SHA-256 of its payload, so writing identical content twice is a no-op, not a
second copy -- there is no update path, only put and get.
"""

from __future__ import annotations

import hashlib
import io
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone

import pyarrow as pa
import pyarrow.parquet as pq
from minio import Minio
from minio.error import S3Error

DEFAULT_BUCKET = "vietnlp-bronze"

_BRONZE_FIELDS = [
    "content_hash", "source_id", "url", "fetched_at", "http_status",
    "robots_decision", "content_type", "raw_payload", "license",
]


def content_hash(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def bronze_key(source_id: str, fetched_at: datetime, hash_hex: str) -> str:
    """`bronze/{source_id}/{YYYY-MM-DD}/{hash_hex}.parquet` -- partitioned the
    way the data contract (spec S4.1) partitions Bronze: source, then date."""
    if fetched_at.tzinfo is None:
        raise BronzeError("fetched_at must be timezone-aware, got a naive datetime")
    date = fetched_at.astimezone(timezone.utc).date().isoformat()
    return f"bronze/{source_id}/{date}/{hash_hex}.parquet"


class BronzeError(RuntimeError):
    pass


@dataclass
class BronzeStore:
    endpoint: str
    access_key: str
    secret_key: str
    bucket: str = DEFAULT_BUCKET
    secure: bool = False
    _client: Minio | None = field(default=None, repr=False)

    @classmethod
    def from_env(cls) -> "BronzeStore":
        endpoint = os.getenv("MINIO_ENDPOINT", "http://localhost:6043")
        access_key = os.getenv("MINIO_ROOT_USER")
        secret_key = os.getenv("MINIO_ROOT_PASSWORD")
        if not access_key or not secret_key:
            raise BronzeError(
                "MINIO_ROOT_USER / MINIO_ROOT_PASSWORD not set. (Values are never logged.)"
            )
        if endpoint.startswith("https://"):
            secure = True
        elif endpoint.startswith("http://"):
            secure = False
        else:
            raise BronzeError(
                f"MINIO_ENDPOINT must start with http:// or https://, got: {endpoint!r}"
            )
        host = endpoint.split("://", 1)[-1]  # Minio() wants a bare host:port
        return cls(endpoint=host, access_key=access_key, secret_key=secret_key, secure=secure)

    def client(self) -> Minio:
        if self._client is None:
            self._client = Minio(
                self.endpoint, access_key=self.access_key, secret_key=self.secret_key,
                secure=self.secure,
            )
        return self._client

    def ensure_bucket(self) -> None:
        c = self.client()
        if not c.bucket_exists(self.bucket):
            c.make_bucket(self.bucket)

    def put_record(self, record: dict) -> str:
        """Write one Bronze record as a single-row Parquet object.

        `record` must carry `raw_payload` (bytes), `source_id`, `fetched_at`
        (datetime) and the rest of the S4.1 fields except `content_hash`,
        which is computed here -- derived, never caller-supplied, so it
        cannot drift from what was actually written.
        """
        payload: bytes = record["raw_payload"]
        hash_hex = content_hash(payload)
        key = bronze_key(record["source_id"], record["fetched_at"], hash_hex)

        row = {f: record.get(f) for f in _BRONZE_FIELDS}
        row["content_hash"] = hash_hex
        row["fetched_at"] = record["fetched_at"].isoformat()
        table = pa.table({k: [v] for k, v in row.items()})
        buf = io.BytesIO()
        pq.write_table(table, buf)
        data = buf.getvalue()

        self.ensure_bucket()
        self.client().put_object(self.bucket, key, io.BytesIO(data), length=len(data))
        return key

    def get_record(self, key: str) -> dict:
        try:
            response = self.client().get_object(self.bucket, key)
            try:
                data = response.read()
            finally:
                response.close()
                response.release_conn()
        except S3Error as exc:
            raise BronzeError(f"no Bronze object at {key}: {exc}") from exc
        table = pq.read_table(io.BytesIO(data))
        return {k: v[0] for k, v in table.to_pydict().items()}
