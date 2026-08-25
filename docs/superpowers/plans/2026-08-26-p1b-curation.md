# P1b: Curation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the curation half of P1 — a 7-stage Bronze-to-Silver pipeline
(boilerplate strip, cross-source MinHash dedup, fastText language ID, DeepSeek
register classification, heuristic quality score, PII scrub, Silver write)
plus the Postgres projector that turns Silver into queryable
`documents`/`sentences` rows.

**Architecture:** `curation_flow` reads Bronze records not yet processed
(tracked in a new `curation_processed` bookkeeping table), runs each through
the 7 stages as chained Prefect tasks — a rejection at any stage raises a
typed exception and dead-letters the record, never a silent drop — and
promotes survivors to the new `SilverStore`. A separate, small
`silver_projector` is the only code path allowed to write to Postgres's
`documents`/`sentences` tables, reading un-projected Silver objects and
sentence-splitting them with a light rule-based splitter (not the real
UD-parse pipeline — that is P2).

**Tech Stack:** Python 3.11, `datasketch` (MinHash/LSH dedup), `fasttext-wheel`
+ Facebook AI's `lid.176.ftz` model (language ID), the existing
`platform/agents` DeepSeek client/budget/cache/registry (register
classification, quality-score borderline band, PII fallback), Prefect 3,
pyarrow/MinIO (Silver storage, mirroring Bronze), psycopg3 (the projector).

**Spec:** `docs/superpowers/specs/2026-08-24-p1-acquisition-curation-design.md`
(the Curation, Silver Storage & Postgres Projector, Testing, Budget Sizing,
and Open Risks sections specifically — the Acquisition sections were already
implemented as P1a, merged to `main` at commit `2506812`).

## Global Constraints

- Python 3.11 only.
- CLAUDE.md rule 1 (Bronze is immutable): nothing in this plan edits or
  deletes a Bronze object. Curation only ever reads Bronze and writes Silver.
- CLAUDE.md rule 2 (DeepSeek output never enters Gold unvalidated): the
  register-classification and quality-score borderline stages reuse the
  existing, already-validated `register-classifier` / `quality-scorer`
  agents in `platform/agents/registry.py` unchanged. The new PII fallback
  (Task 7) gets its own anti-hallucination validator before this plan is
  done — same "locate the model's claimed text in the source ourselves"
  pattern `_validate_ner` already uses, so a hallucinated span cannot be
  redacted.
- CLAUDE.md rule 3 (Postgres/Fuseki are projections, never hand-edited): the
  **only** code path in this plan permitted to write to `documents` or
  `sentences` is `platform/db/silver_projector.py` (Task 9). Two new tables
  this plan adds — `curation_processed` (Task 8) and `silver_projections`
  (Task 9) — are operational bookkeeping (which Bronze/Silver objects have
  already been looked at), not corpus content, the same carve-out the P1a
  plan already established for `sources` and for `dead_letters`.
- CLAUDE.md rule 4 (no silent drops): every stage that rejects a document
  raises one of four typed exceptions (`DuplicateError`, `LanguageIDError`,
  `LowQuality`, `ValidationFailed`). `curation_flow`'s per-record loop
  catches exactly those four, never a bare `Exception`, and always calls
  `dead_letter_sink` with the record and the exception text.
- CLAUDE.md rule 5 (budget caps hard-stop, they do not warn):
  `BudgetExceeded` is deliberately **not** one of the four exceptions
  `curation_flow` catches per-record. It must propagate out of the flow and
  abort the whole run — catching it per-record would silently turn a hard
  stop into a per-document warning while still spending on every later
  record. This is a load-bearing design point in Task 8, not an oversight.
- Vietnamese-specific: word segmentation does not exist yet (P2's job;
  CLAUDE.md — Vietnamese orthography is syllable-segmented, not
  word-segmented), so MinHash dedup (Task 5) shingles on characters, not
  words. Non-diacritic Vietnamese is a register CLAUDE.md requires tracking,
  not noise to discard — Task 4 includes an empirical test against the
  fixture corpus's `non_diacritic` texts and a documented fallback in case
  fastText's raw accuracy on romanized Vietnamese is not good enough,
  because off-the-shelf lang-id is known to confuse it with
  Indonesian/Malay (this is `curation-analyst`'s own documented top risk).
- Server `_59` is a shared 8-vCPU/15-GB host with ~3-4 GB actually free and
  a dozen unrelated containers (unchanged since P1a). The fastText model is
  the compressed `.ftz` variant (~1 MB, not the ~126 MB `.bin`) specifically
  because of this. No new Docker service is added for dedup — the LSH index
  lives in-process, seeded at the start of each curation run from one small
  Parquet manifest object stored in Silver's own MinIO bucket, not a
  persistent index service (Redis, etc.) the pilot's ~100K-document scale
  does not need.
- `rsync` is not installed on `_59`; sync is tar-over-SSH via
  `deploy/deploy.sh`, same mechanism P1a used. Whenever a task changes
  `pyproject.toml` or `deploy/Dockerfile` (Task 1 only), the image must be
  rebuilt (`docker compose build agents`) before the next test run picks up
  the change — a `docker compose run` against a stale image silently tests
  old dependencies.
- `platform/agents/` (client, budget, cache, policy) is untouched except for
  one addition: a new `pii-scrubber` `Agent` registered in `registry.py`
  (Task 7). The routing/budget/cache machinery itself is not modified.
- Testing: the default offline gate (`docker compose run --rm --no-deps
  --entrypoint pytest agents /app/tests -q`) must stay green without
  Postgres or MinIO running. Every curation stage's tests are pure-logic or
  mock DeepSeek via `httpx.MockTransport` (same pattern as
  `tests/test_client_flow.py`) — genuine live Postgres/MinIO/DeepSeek
  integration is exercised once, holistically, in Task 11, mirroring how
  P1a's Task 10 proved the whole acquisition path for real.
- New third-party dependencies, both MIT-licensed libraries:
  `datasketch>=1.6` (MinHash/LSH) and `fasttext-wheel>=0.9.2` (prebuilt
  wheels for the `fasttext` language-ID library, since the official
  `fasttext` PyPI package lacks wheels for many platforms). The bundled
  `lid.176.ftz` **model** itself is separately licensed CC-BY-SA 3.0 by
  Facebook AI Research — attributed in `deploy/THIRD_PARTY_NOTICES.md`
  (Task 1). Before baking the model into the image, confirm
  `https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz`
  still resolves (`curl -fsSL -I <url>` from `_59`); if fastText has moved
  the canonical URL, use whatever `https://fasttext.cc/docs/en/language-identification.html`
  currently documents and update this plan's note accordingly.

---

### Task 1: Curation dependencies + fastText language-ID model

**Files:**
- Modify: `pyproject.toml`
- Modify: `deploy/Dockerfile`
- Create: `deploy/THIRD_PARTY_NOTICES.md`
- Create: `tests/test_curation_environment.py`

**Interfaces:**
- Consumes: nothing from later tasks.
- Produces: `datasketch` and `fasttext` importable inside the built image;
  a Vietnamese-language-ID model available at the path named by
  `VIETNLP_FASTTEXT_MODEL` (baked in as a Dockerfile `ENV`, defaulting to
  `/app/models/lid.176.ftz`). Tasks 4 and 5 depend on both.

- [ ] **Step 1: Add the two new dependencies**

In `pyproject.toml`, add to `dependencies`:

```toml
    "datasketch>=1.6",
    "fasttext-wheel>=0.9.2",
```

- [ ] **Step 2: Bake the dependencies and the language-ID model into the image**

In `deploy/Dockerfile`, extend the existing pip-install line and add the
model download right after it:

```dockerfile
COPY pyproject.toml /app/
RUN pip install --no-cache-dir \
    httpx>=0.27 pytest>=8.0 respx>=0.21 "mcp>=2.0,<3" \
    "psycopg[binary]>=3.1" pyarrow>=15 minio>=7.2 prefect>=3.0 pandera>=0.20 pandas>=2.0 \
    "datasketch>=1.6" "fasttext-wheel>=0.9.2"

# fastText Vietnamese-capable language-ID model. Baked in at build time so
# curation never needs network access at runtime. The compressed .ftz
# variant (~1 MB) is used deliberately -- _59 has ~3-4 GB free, not enough
# headroom to justify the ~126 MB uncompressed .bin for a marginal accuracy
# gain. Model license: CC-BY-SA 3.0, Facebook AI Research -- see
# deploy/THIRD_PARTY_NOTICES.md.
RUN mkdir -p /app/models && python -c "\
import urllib.request; \
urllib.request.urlretrieve( \
    'https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz', \
    '/app/models/lid.176.ftz')"
ENV VIETNLP_FASTTEXT_MODEL=/app/models/lid.176.ftz
```

Place this block after the existing `pip install` line and before
`COPY src/ /app/src/`.

- [ ] **Step 3: Add the third-party notice**

Create `deploy/THIRD_PARTY_NOTICES.md`:

```markdown
# Third-Party Notices

## lid.176.ftz (fastText language identification model)

Source: https://fasttext.cc/docs/en/language-identification.html
Publisher: Facebook AI Research
License: CC-BY-SA 3.0 (https://creativecommons.org/licenses/by-sa/3.0/)

Used unmodified by `vietnlp.curation.lang_id` to confirm acquired text is
Vietnamese before any further curation stage runs.
```

- [ ] **Step 4: Write the smoke test**

Create `tests/test_curation_environment.py`:

```python
"""Smoke test for curation's non-Python dependencies -- confirms the image
built in Task 1 actually has a working fastText model and datasketch
installed before Tasks 4/5 build real logic on top of them."""

import os


def test_fasttext_language_model_predicts_vietnamese():
    import fasttext

    model = fasttext.load_model(os.environ["VIETNLP_FASTTEXT_MODEL"])
    labels, probs = model.predict("Xin chào các bạn, hôm nay trời đẹp quá.")
    assert labels[0] == "__label__vi"
    assert probs[0] > 0.5


def test_datasketch_minhash_round_trips_a_signature():
    from datasketch import MinHash

    a = MinHash(num_perm=128)
    a.update(b"hello world")
    b = MinHash(num_perm=128)
    b.update(b"hello world")
    assert a.jaccard(b) == 1.0
```

- [ ] **Step 5: Sync, rebuild, and run**

```bash
tar czf - --exclude '.git' --exclude '__pycache__' --exclude '*.pyc' \
  --exclude '.env' --exclude 'deepseek.key' --exclude 'data' \
  src pyproject.toml tests deploy CLAUDE.md Makefile \
  | ssh _59 'tar xzf - -C vietnlp'
ssh _59 'cd vietnlp/deploy && docker compose build agents'
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_curation_environment.py -v'
```

Expected: PASS, 2 tests. If the model URL 404s, follow this plan's Global
Constraints note on re-checking fastText's current documented URL.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml deploy/Dockerfile deploy/THIRD_PARTY_NOTICES.md tests/test_curation_environment.py
git commit -m "feat: add datasketch + fastText language-ID model for curation"
```

---

### Task 2: Shared content-addressing module + SilverStore

**Files:**
- Create: `src/vietnlp/platform/storage/_content_addressed.py`
- Modify: `src/vietnlp/platform/storage/bronze.py`
- Create: `src/vietnlp/platform/storage/silver.py`
- Modify: `tests/conftest.py`
- Create: `tests/test_storage_silver.py`
- Test: `tests/test_storage_bronze.py` (must stay green, unchanged)

**Interfaces:**
- Consumes: nothing from later tasks.
- Produces: `SilverStore` (`platform/storage/silver.py`) with
  `put_record(record: dict) -> str`, `get_record(key: str) -> dict`,
  `list_keys(prefix: str = "silver/") -> list[str]`, `.from_env()`,
  `.client()`, `.ensure_bucket()`, `.bucket`. A Silver record's fields are
  `content_hash, bronze_uri, source_id, url, fetched_at, curated_at, text,
  lang, register, quality_score, dedup_cluster_id, pii_scrubbed,
  minhash_signature`. `BronzeStore` additionally gets
  `list_keys(prefix: str = "bronze/") -> list[str]`. Tasks 5, 8, 9, 11 all
  depend on this.

- [ ] **Step 1: Extract the shared content-addressing helpers**

Create `src/vietnlp/platform/storage/_content_addressed.py`:

```python
"""Shared content-addressing helpers for Bronze and Silver storage.

Both stores derive their object key from the SHA-256 of a payload plus a
date partition (spec S4.1's `source/date` partitioning) -- this is the one
implementation both `BronzeStore` and `SilverStore` use, so the derivation
logic cannot drift between the two layers.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone


class ContentAddressError(RuntimeError):
    pass


def content_hash(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def partitioned_key(layer: str, source_id: str, at: datetime, hash_hex: str) -> str:
    """`{layer}/{source_id}/{YYYY-MM-DD}/{hash_hex}.parquet`."""
    if at.tzinfo is None:
        raise ContentAddressError("timestamp must be timezone-aware, got a naive datetime")
    date = at.astimezone(timezone.utc).date().isoformat()
    return f"{layer}/{source_id}/{date}/{hash_hex}.parquet"
```

- [ ] **Step 2: Point `bronze.py` at the shared module, add `list_keys`**

In `src/vietnlp/platform/storage/bronze.py`, replace the local
`content_hash`/`bronze_key` definitions (lines 29-39) with:

```python
from ._content_addressed import ContentAddressError, content_hash, partitioned_key


def bronze_key(source_id: str, fetched_at: datetime, hash_hex: str) -> str:
    """`bronze/{source_id}/{YYYY-MM-DD}/{hash_hex}.parquet` -- partitioned the
    way the data contract (spec S4.1) partitions Bronze: source, then date."""
    try:
        return partitioned_key("bronze", source_id, fetched_at, hash_hex)
    except ContentAddressError as exc:
        raise BronzeError(str(exc)) from exc
```

Remove the now-unused `import hashlib` if nothing else in the file uses it
(check: `content_hash` itself moved out, and nothing else calls `hashlib`
directly). Add one new method to `BronzeStore`, right after `get_record`:

```python
    def list_keys(self, prefix: str = "bronze/") -> list[str]:
        """All Bronze object keys under a prefix -- curation_flow (P1b) uses
        this to enumerate documents not yet processed."""
        self.ensure_bucket()
        return [
            obj.object_name
            for obj in self.client().list_objects(self.bucket, prefix=prefix, recursive=True)
        ]
```

- [ ] **Step 3: Run the existing Bronze tests to confirm the refactor changed no behavior**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_storage_bronze.py -v'
```

Expected: PASS, all existing tests unchanged (`test_bronze_key_rejects_naive_datetime`
must still see `BronzeError` with `"naive"` in the message — the try/except
re-raise in Step 2 exists specifically to preserve this).

- [ ] **Step 4: Write `SilverStore`**

Create `src/vietnlp/platform/storage/silver.py`:

```python
"""Content-addressed Silver storage on MinIO.

Mirrors BronzeStore's shape (spec S4.1's source/date partitioning, shared
via _content_addressed.py) but carries curation's output fields instead of
Bronze's raw-fetch fields. Silver documents are immutable in the same sense
Bronze is: a corrected document is a new content_hash, promoted again, never
an in-place edit -- CLAUDE.md rule 3 makes Postgres a projection of Silver
(via silver_projector.py), so Silver itself must be the thing worth
projecting from, not a scratch pad.
"""

from __future__ import annotations

import io
import os
from dataclasses import dataclass, field
from datetime import datetime

import pyarrow as pa
import pyarrow.parquet as pq
from minio import Minio
from minio.error import S3Error

from ._content_addressed import ContentAddressError, content_hash, partitioned_key

DEFAULT_BUCKET = "vietnlp-silver"

_SILVER_FIELDS = [
    "content_hash", "bronze_uri", "source_id", "url", "fetched_at", "curated_at",
    "text", "lang", "register", "quality_score", "dedup_cluster_id",
    "pii_scrubbed", "minhash_signature",
]


class SilverError(RuntimeError):
    pass


def silver_key(source_id: str, curated_at: datetime, hash_hex: str) -> str:
    """`silver/{source_id}/{YYYY-MM-DD}/{hash_hex}.parquet` -- partitioned by
    curation date, mirroring Bronze's fetch-date partitioning (spec S4.1)."""
    try:
        return partitioned_key("silver", source_id, curated_at, hash_hex)
    except ContentAddressError as exc:
        raise SilverError(str(exc)) from exc


@dataclass
class SilverStore:
    endpoint: str
    access_key: str
    secret_key: str
    bucket: str = DEFAULT_BUCKET
    secure: bool = False
    _client: Minio | None = field(default=None, repr=False)

    @classmethod
    def from_env(cls) -> "SilverStore":
        endpoint = os.getenv("MINIO_ENDPOINT", "http://localhost:6043")
        access_key = os.getenv("MINIO_ROOT_USER")
        secret_key = os.getenv("MINIO_ROOT_PASSWORD")
        if not access_key or not secret_key:
            raise SilverError(
                "MINIO_ROOT_USER / MINIO_ROOT_PASSWORD not set. (Values are never logged.)"
            )
        if endpoint.startswith("https://"):
            secure = True
        elif endpoint.startswith("http://"):
            secure = False
        else:
            raise SilverError(
                f"MINIO_ENDPOINT must start with http:// or https://, got: {endpoint!r}"
            )
        host = endpoint.split("://", 1)[-1]
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
        """Write one Silver record as a single-row Parquet object.

        `record` must carry `text` (str) and `curated_at` (a fresh,
        timezone-aware datetime this stage creates). `fetched_at` is
        forwarded as-is -- it arrives as the ISO string already read back
        from Bronze, not a fresh datetime, so unlike `curated_at` it is
        never re-serialized here. `content_hash` is computed here from the
        cleaned text -- derived, never caller-supplied.
        """
        text: str = record["text"]
        hash_hex = content_hash(text.encode("utf-8"))
        key = silver_key(record["source_id"], record["curated_at"], hash_hex)

        row = {f: record.get(f) for f in _SILVER_FIELDS}
        row["content_hash"] = hash_hex
        row["curated_at"] = record["curated_at"].isoformat()
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
            raise SilverError(f"no Silver object at {key}: {exc}") from exc
        table = pq.read_table(io.BytesIO(data))
        return {k: v[0] for k, v in table.to_pydict().items()}

    def list_keys(self, prefix: str = "silver/") -> list[str]:
        """All Silver object keys under a prefix -- used by the projector
        (Task 9) and by curation_flow's dedup-manifest bootstrap (Task 5)."""
        self.ensure_bucket()
        return [
            obj.object_name
            for obj in self.client().list_objects(self.bucket, prefix=prefix, recursive=True)
        ]
```

- [ ] **Step 5: Add a `live_silver_store` fixture**

In `tests/conftest.py`, add (mirroring `live_store` exactly, just for the
new store):

```python
from vietnlp.platform.storage.silver import SilverError, SilverStore


def _live_silver_store() -> SilverStore | None:
    try:
        store = SilverStore.from_env()
    except SilverError:
        return None
    try:
        store.client().list_buckets()
    except Exception:
        return None
    return store


@pytest.fixture
def live_silver_store():
    store = _live_silver_store()
    if store is None:
        pytest.skip("no reachable MinIO (MINIO_ENDPOINT/credentials); run with the stack up")
    store.bucket = f"vietnlp-silver-test-{os.getpid()}"
    yield store
    try:
        client = store.client()
        for obj in client.list_objects(store.bucket, recursive=True):
            client.remove_object(store.bucket, obj.object_name)
        client.remove_bucket(store.bucket)
    except Exception:
        pass  # best-effort cleanup of a throwaway test bucket, not the real store
```

- [ ] **Step 6: Write `SilverStore`'s tests**

Create `tests/test_storage_silver.py`:

```python
"""Content-addressed Silver storage. Pure helpers are tested offline; the
put/get round trip against a live MinIO is a self-skipping integration test,
mirroring tests/test_storage_bronze.py exactly."""

from datetime import datetime, timedelta, timezone

import pytest

from vietnlp.platform.storage.silver import SilverError, SilverStore, silver_key


def test_silver_key_partitions_by_source_and_date():
    when = datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc)
    assert silver_key("fixture-formal", when, "abc123") == "silver/fixture-formal/2026-08-23/abc123.parquet"


def test_silver_key_normalises_to_utc_date():
    when = datetime(2026, 8, 24, 6, 0, tzinfo=timezone(timedelta(hours=7)))
    assert "2026-08-23" in silver_key("fixture-formal", when, "abc123")


def test_silver_key_rejects_naive_datetime():
    with pytest.raises(SilverError, match="naive"):
        silver_key("fixture-formal", datetime(2026, 8, 23, 12, 0), "abc123")


def test_from_env_refuses_to_default_a_secret(monkeypatch):
    monkeypatch.delenv("MINIO_ROOT_USER", raising=False)
    monkeypatch.delenv("MINIO_ROOT_PASSWORD", raising=False)
    with pytest.raises(SilverError, match="not set"):
        SilverStore.from_env()


def test_put_then_get_round_trips_a_record(live_silver_store):
    record = {
        "bronze_uri": "bronze/fixture-formal/2026-08-23/deadbeef.parquet",
        "source_id": "fixture-formal", "url": "https://fixture.local/x",
        "fetched_at": "2026-08-23T00:00:00+00:00",
        "curated_at": datetime.now(timezone.utc),
        "text": "Hà Nội là thủ đô của Việt Nam.", "lang": "vi", "register": "formal",
        "quality_score": 4.5, "dedup_cluster_id": "cluster-1", "pii_scrubbed": False,
        "minhash_signature": [1, 2, 3],
    }
    key = live_silver_store.put_record(record)
    fetched = live_silver_store.get_record(key)
    assert fetched["text"] == record["text"]
    assert fetched["bronze_uri"] == record["bronze_uri"]
    assert fetched["fetched_at"] == record["fetched_at"]
    assert list(fetched["minhash_signature"]) == [1, 2, 3]


def test_put_is_idempotent_for_identical_text(live_silver_store):
    record = {
        "bronze_uri": "bronze/fixture-formal/2026-08-23/deadbeef.parquet",
        "source_id": "fixture-formal", "url": "https://fixture.local/y",
        "fetched_at": "2026-08-23T00:00:00+00:00",
        "curated_at": datetime.now(timezone.utc),
        "text": "Nội dung không đổi.", "lang": "vi", "register": "formal",
        "quality_score": 4.0, "dedup_cluster_id": "cluster-2", "pii_scrubbed": False,
        "minhash_signature": [4, 5, 6],
    }
    key1 = live_silver_store.put_record(record)
    key2 = live_silver_store.put_record(record)
    assert key1 == key2, "identical text must resolve to the identical Silver key"
```

- [ ] **Step 7: Run**

```bash
tar czf - --exclude '.git' --exclude '__pycache__' --exclude '*.pyc' --exclude '.env' --exclude 'deepseek.key' --exclude 'data' src pyproject.toml tests deploy CLAUDE.md Makefile | ssh _59 'tar xzf - -C vietnlp'
ssh _59 'cd vietnlp/deploy && docker compose run --rm --entrypoint pytest agents /app/tests/test_storage_bronze.py /app/tests/test_storage_silver.py -v'
```

Expected: PASS. The two live tests self-skip if MinIO is unreachable;
run `make test-live` against `_59` (which has MinIO up) to exercise them.

- [ ] **Step 8: Commit**

```bash
git add src/vietnlp/platform/storage/_content_addressed.py \
        src/vietnlp/platform/storage/bronze.py \
        src/vietnlp/platform/storage/silver.py \
        tests/conftest.py tests/test_storage_silver.py
git commit -m "feat: add SilverStore, share content-addressing with BronzeStore"
```

---

### Task 3: Boilerplate-strip safety net

**Files:**
- Create: `src/vietnlp/curation/boilerplate.py`
- Create: `tests/test_curation_boilerplate.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `strip_boilerplate(text: str) -> str`. Task 8 calls this as
  curation's first stage.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_curation_boilerplate.py`:

```python
"""Boilerplate-strip is a safety net, not the primary extraction step (that
is web-reader's job at acquisition time) -- it must be conservative: it is
allowed to miss boilerplate (the quality-score stage catches that later) but
must never damage real content."""

import json
from pathlib import Path

from vietnlp.curation.boilerplate import strip_boilerplate

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "corpus" / "fixture_corpus.jsonl"


def test_strips_a_copyright_line():
    text = "Nội dung chính.\n© 2026 Some Site. All rights reserved.\n"
    assert "©" not in strip_boilerplate(text)
    assert "Nội dung chính." in strip_boilerplate(text)


def test_strips_a_cookie_notice_line():
    text = "Bài viết thật.\nCookie Policy: chúng tôi sử dụng cookie.\n"
    assert "Cookie Policy" not in strip_boilerplate(text)


def test_removes_control_characters():
    text = "Vẫn ổn\x0bnhưng có ký tự lạ."
    assert "\x0b" not in strip_boilerplate(text)


def test_collapses_excess_blank_lines():
    text = "Đoạn một.\n\n\n\n\nĐoạn hai."
    assert "\n\n\n" not in strip_boilerplate(text)


def test_never_raises_on_empty_text():
    assert strip_boilerplate("") == ""


def test_fixture_corpus_passes_through_unchanged():
    """Golden-file check: none of the 100 hand-authored fixture sentences
    contain boilerplate or control characters, so the safety net must leave
    every one byte-identical (after whitespace-strip)."""
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)
            assert strip_boilerplate(record["text"]) == record["text"].strip()
```

- [ ] **Step 2: Run to verify failure**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_curation_boilerplate.py -v'
```

Expected: FAIL — `ModuleNotFoundError: No module named 'vietnlp.curation.boilerplate'`.

- [ ] **Step 3: Implement**

Create `src/vietnlp/curation/boilerplate.py`:

```python
"""Boilerplate-strip safety net for Bronze records already extracted
upstream.

web-reader's extraction (news_gov_wiki / forum_qa_blog acquisition paths)
already strips navigation/boilerplate at fetch time. This module exists only
as a safety net for the public_corpus loader, which writes external-dataset
text straight through with no such extraction step (spec: "safety net for
public-loader imports that skip web-reader's extraction-time stripping"). It
is intentionally conservative -- a wrongly-stripped sentence is worse than a
boilerplate line that slips through, since the latter is caught by the
quality-score stage.
"""

from __future__ import annotations

import re

_BOILERPLATE_LINE = re.compile(
    r"^\s*("
    r"(©|copyright)\s.*|"
    r"(all rights reserved).*|"
    r"(cookie|cookies)\s+(policy|notice|consent).*|"
    r"(bản quyền)\s.*|"
    r"(chia sẻ|share)\s*:?\s*(facebook|twitter|zalo)\s*$"
    r")\s*$",
    re.IGNORECASE,
)

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def strip_boilerplate(text: str) -> str:
    """Drop boilerplate lines and control characters; collapse blank runs.

    Never raises -- worst case, nothing matches and `text` passes through
    with only whitespace normalized.
    """
    text = _CONTROL_CHARS.sub("", text)
    lines = [line for line in text.split("\n") if not _BOILERPLATE_LINE.match(line)]
    collapsed = "\n".join(lines)
    collapsed = re.sub(r"\n{3,}", "\n\n", collapsed)
    collapsed = re.sub(r"[ \t]{2,}", " ", collapsed)
    return collapsed.strip()
```

- [ ] **Step 4: Run to verify pass**

```bash
tar czf - --exclude '.git' --exclude '__pycache__' --exclude '*.pyc' --exclude '.env' --exclude 'deepseek.key' --exclude 'data' src pyproject.toml tests deploy CLAUDE.md Makefile | ssh _59 'tar xzf - -C vietnlp'
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_curation_boilerplate.py -v'
```

Expected: PASS, 6 tests.

- [ ] **Step 5: Commit**

```bash
git add src/vietnlp/curation/boilerplate.py tests/test_curation_boilerplate.py
git commit -m "feat: add boilerplate-strip safety net for curation"
```

---

### Task 4: Language identification (fastText)

**Files:**
- Create: `src/vietnlp/curation/lang_id.py`
- Create: `tests/test_curation_lang_id.py`

**Interfaces:**
- Consumes: Task 1's baked-in model at `VIETNLP_FASTTEXT_MODEL`.
- Produces: `identify(text: str) -> tuple[str, float]`, `LanguageIDError`.
  Task 8 calls this as curation's third stage (after dedup, before register
  classification).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_curation_lang_id.py`:

```python
"""fastText language ID. The non_diacritic test is the empirical check the
design spec deferred to implementation: curation-analyst's own agent doc
names 'lang-id false negatives on non-diacritic Vietnamese' as its most
common failure mode (confused with Indonesian/Malay). If this test fails,
tune MIN_CONFIDENCE and/or flip ENABLE_ROMANIZATION_FALLBACK in lang_id.py
against what is actually observed here -- do not weaken the test to route
around a real accuracy problem."""

import json
from pathlib import Path

import pytest

from vietnlp.curation.lang_id import LanguageIDError, identify

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "corpus" / "fixture_corpus.jsonl"


def _fixture_texts_by_register(register: str) -> list[str]:
    texts = []
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)
            if record["register"] == register:
                texts.append(record["text"])
    return texts


def test_identifies_formal_vietnamese():
    lang, confidence = identify("Bộ Giáo dục và Đào tạo công bố lịch thi tốt nghiệp.")
    assert lang == "vi"
    assert confidence > 0.5


def test_rejects_english():
    with pytest.raises(LanguageIDError):
        identify("The Ministry of Education announced the exam schedule today.")


def test_rejects_empty_text():
    with pytest.raises(LanguageIDError, match="empty"):
        identify("   ")


def test_identifies_non_diacritic_fixture_texts_as_vietnamese():
    non_diacritic = _fixture_texts_by_register("non_diacritic")
    assert len(non_diacritic) == 25
    accepted = 0
    for text in non_diacritic:
        try:
            lang, _ = identify(text)
            accepted += lang == "vi"
        except LanguageIDError:
            pass
    # These are short (one-clause) fixture sentences -- the hardest case for
    # any lang-id on romanized text. Below 80%, the pipeline would be
    # silently discarding most of a register CLAUDE.md requires tracking.
    assert accepted / len(non_diacritic) >= 0.8, (
        f"only {accepted}/{len(non_diacritic)} non_diacritic fixture texts identified as "
        "Vietnamese -- tune MIN_CONFIDENCE / enable the romanization fallback in lang_id.py"
    )
```

- [ ] **Step 2: Run to verify failure**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_curation_lang_id.py -v'
```

Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

Create `src/vietnlp/curation/lang_id.py`:

```python
"""fastText language identification -- confirms Bronze text is Vietnamese
before it costs anything further downstream (spec: "confirms Vietnamese-
family text, including non-diacritic input"). Character-n-gram based, so it
stays reasonably robust when diacritics are missing -- word-based lang-id
would need Vietnamese word segmentation, which does not exist yet (P2's job;
CLAUDE.md: Vietnamese orthography is syllable-segmented, not
word-segmented).
"""

from __future__ import annotations

import os
import threading

DEFAULT_MODEL_PATH = "/app/models/lid.176.ftz"
# Below this, fastText's own confidence is unreliable on short strings; a
# genuinely-short Vietnamese fragment is better dead-lettered than trusted
# on a low-confidence guess either way.
MIN_CONFIDENCE = 0.5
_VI_LABEL = "__label__vi"

# Vietnamese's native syllable inventory never uses these four Latin
# letters -- they occur only in loanwords/foreign proper nouns. Indonesian
# and Malay (fastText's most common false-positive labels for non-diacritic
# Vietnamese) use them far more freely, especially "w" and "j". This is a
# documented fallback, OFF by default -- flip on only if
# test_identifies_non_diacritic_fixture_texts_as_vietnamese shows fastText's
# raw accuracy is not enough, and record the observed rate in this comment.
ENABLE_ROMANIZATION_FALLBACK = False
_NON_VIETNAMESE_LETTERS = set("fjwz")
_FALLBACK_CONFUSABLE_LABELS = {"__label__id", "__label__ms"}

_model = None
_lock = threading.Lock()


class LanguageIDError(RuntimeError):
    """Raised when text is confidently not Vietnamese, or confidence is too
    low to trust either way. Both are dead-letter conditions (CLAUDE.md
    rule 4), never a silent pass-through."""


def _load_model():
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                import fasttext

                path = os.getenv("VIETNLP_FASTTEXT_MODEL", DEFAULT_MODEL_PATH)
                _model = fasttext.load_model(path)
    return _model


def _looks_like_romanized_vietnamese(text: str) -> bool:
    words = text.lower().split()
    if not words:
        return False
    avg_len = sum(len(w) for w in words) / len(words)
    has_excluded_letters = any(set(w) & _NON_VIETNAMESE_LETTERS for w in words)
    return not has_excluded_letters and avg_len <= 6.0


def identify(text: str) -> tuple[str, float]:
    """Returns (lang_code, confidence). Raises LanguageIDError if the text is
    not confidently Vietnamese-family."""
    model = _load_model()
    # fastText treats embedded newlines as multiple inputs; a document is
    # one label decision, not one per line.
    flat = " ".join(text.split())
    if not flat:
        raise LanguageIDError("empty text after normalization")
    labels, probs = model.predict(flat, k=1)
    label, confidence = labels[0], float(probs[0])
    lang = label.removeprefix("__label__")

    if label != _VI_LABEL:
        if (
            ENABLE_ROMANIZATION_FALLBACK
            and label in _FALLBACK_CONFUSABLE_LABELS
            and _looks_like_romanized_vietnamese(flat)
        ):
            return "vi", confidence
        raise LanguageIDError(f"detected language {lang!r} (confidence {confidence:.2f}), not Vietnamese")
    if confidence < MIN_CONFIDENCE:
        raise LanguageIDError(f"Vietnamese confidence {confidence:.2f} below {MIN_CONFIDENCE}")
    return lang, confidence
```

- [ ] **Step 4: Run to verify pass**

```bash
tar czf - --exclude '.git' --exclude '__pycache__' --exclude '*.pyc' --exclude '.env' --exclude 'deepseek.key' --exclude 'data' src pyproject.toml tests deploy CLAUDE.md Makefile | ssh _59 'tar xzf - -C vietnlp'
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_curation_lang_id.py -v'
```

Expected: PASS, 4 tests. If
`test_identifies_non_diacritic_fixture_texts_as_vietnamese` fails, set
`ENABLE_ROMANIZATION_FALLBACK = True` in `lang_id.py`, re-run, and update the
comment above it with the observed before/after acceptance rate — do not
proceed to Task 5 with this test red.

- [ ] **Step 5: Commit**

```bash
git add src/vietnlp/curation/lang_id.py tests/test_curation_lang_id.py
git commit -m "feat: add fastText Vietnamese language identification"
```

---

### Task 5: Cross-source MinHash dedup

**Files:**
- Create: `src/vietnlp/curation/dedup.py`
- Create: `tests/test_curation_dedup.py`

**Interfaces:**
- Consumes: Task 2's `SilverStore` (`.client()`, `.bucket`, `.ensure_bucket()`).
- Produces: `DedupIndex` (classmethods `empty()`, `from_manifest_rows(rows)`;
  methods `manifest_rows()`, `check_and_add(content_hash: str, m: MinHash) ->
  str`; attributes `lsh`, `signatures`, `cluster_of`), `DuplicateError`,
  `compute_signature(text: str) -> MinHash`, `signature_to_digest(m) ->
  list[int]`, `signature_from_digest(digest) -> MinHash`, `load_manifest(silver)
  -> DedupIndex`, `save_manifest(silver, index) -> None`. Task 8 uses all of
  these as curation's second stage and for run-to-run persistence.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_curation_dedup.py`:

```python
"""MinHash dedup. Character-shingled (no word segmentation exists yet -- P2's
job). The manifest round-trip needs live MinIO and self-skips without it,
mirroring test_storage_bronze.py's pattern."""

import json
from pathlib import Path

import pytest

from vietnlp.curation.dedup import (
    DedupIndex, DuplicateError, compute_signature, load_manifest,
    save_manifest, shingles, signature_from_digest, signature_to_digest,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "corpus" / "fixture_corpus.jsonl"


def test_shingles_of_short_text_is_the_whole_text():
    assert shingles("hi", k=5) == {"hi"}


def test_shingles_covers_every_window():
    assert shingles("abcdef", k=5) == {"abcde", "bcdef"}


def test_identical_text_has_jaccard_similarity_one():
    a = compute_signature("Hà Nội là thủ đô của Việt Nam.")
    b = compute_signature("Hà Nội là thủ đô của Việt Nam.")
    assert a.jaccard(b) == 1.0


def test_signature_digest_round_trips():
    m = compute_signature("Một câu tiếng Việt bất kỳ.")
    reconstructed = signature_from_digest(signature_to_digest(m))
    assert m.jaccard(reconstructed) == 1.0


def test_check_and_add_flags_a_near_duplicate():
    index = DedupIndex.empty()
    text_a = "Ngân hàng Nhà nước giữ nguyên lãi suất điều hành trong quý này."
    text_b = "Ngân hàng Nhà nước giữ nguyên lãi suất điều hành trong quý này!"
    index.check_and_add("hash-a", compute_signature(text_a))
    with pytest.raises(DuplicateError) as excinfo:
        index.check_and_add("hash-b", compute_signature(text_b))
    assert excinfo.value.duplicate_of == "hash-a"


def test_check_and_add_does_not_flag_distinct_text():
    index = DedupIndex.empty()
    index.check_and_add("hash-a", compute_signature("Đội tuyển bóng đá giành chiến thắng."))
    index.check_and_add("hash-b", compute_signature("Thành phố triển khai thêm tuyến xe buýt."))
    assert set(index.signatures) == {"hash-a", "hash-b"}


def test_fixture_corpus_has_zero_internal_near_duplicates():
    """Golden-file check: the 100 fixture sentences are all genuinely
    distinct, so none should collide."""
    index = DedupIndex.empty()
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)
            index.check_and_add(record["content_hash"], compute_signature(record["text"]))
    assert len(index.signatures) == 100


def test_manifest_round_trips_through_live_minio(live_silver_store):
    index = DedupIndex.empty()
    index.check_and_add("hash-a", compute_signature("Nội dung mẫu để kiểm tra."))
    save_manifest(live_silver_store, index)

    loaded = load_manifest(live_silver_store)
    assert set(loaded.signatures) == {"hash-a"}
    assert loaded.cluster_of["hash-a"] == "hash-a"


def test_load_manifest_returns_empty_index_when_none_exists_yet(live_silver_store):
    index = load_manifest(live_silver_store)
    assert index.signatures == {}
```

- [ ] **Step 2: Run to verify failure**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_curation_dedup.py -v'
```

Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

Create `src/vietnlp/curation/dedup.py`:

```python
"""Cross-source near-duplicate detection via MinHash + LSH.

Character-shingled (not word-shingled): Vietnamese has no word segmentation
yet (P2's job; CLAUDE.md -- orthography is syllable-segmented, not
word-segmented), so word n-grams are not available at this stage. Character
5-grams are a standard, language-agnostic substitute for near-duplicate
detection that needs no upstream tokenizer.

The LSH index lives in-process, seeded at the start of each curation run
from a small manifest object in Silver's own bucket
(`silver/_dedup_manifest.parquet`) -- not rebuilt by re-fetching every
promoted Silver document's full record, and not a persistent external index
(Redis, etc.), which would be new infrastructure this pilot's ~100K-document
scale does not need (spec: "design for more, do not build for more").
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from datasketch import MinHash, MinHashLSH
from minio.error import S3Error

SHINGLE_SIZE = 5
NUM_PERM = 128
# Fraction of shared shingles above which two documents are the "same"
# article for corpus purposes -- e.g. a wire-service lede copied verbatim
# across outlets. Tuned against the fixture corpus (100 distinct synthetic
# sentences: zero should collide, per this task's golden-file test) plus
# hand-built near-duplicate pairs in this module's tests; revisit against a
# real sample once one exists (spec's own open risk).
JACCARD_THRESHOLD = 0.8

MANIFEST_KEY = "silver/_dedup_manifest.parquet"


class DuplicateError(RuntimeError):
    """Raised when a document collides with an already-indexed document
    above JACCARD_THRESHOLD."""

    def __init__(self, duplicate_of: str):
        self.duplicate_of = duplicate_of
        super().__init__(f"near-duplicate of already-promoted document {duplicate_of}")


def shingles(text: str, k: int = SHINGLE_SIZE) -> set[str]:
    normalized = " ".join(text.split())
    if len(normalized) < k:
        return {normalized} if normalized else set()
    return {normalized[i : i + k] for i in range(len(normalized) - k + 1)}


def compute_signature(text: str) -> MinHash:
    m = MinHash(num_perm=NUM_PERM)
    for shingle in shingles(text):
        m.update(shingle.encode("utf-8"))
    return m


def signature_to_digest(m: MinHash) -> list[int]:
    return [int(v) for v in m.digest()]


def signature_from_digest(digest: list[int]) -> MinHash:
    m = MinHash(num_perm=NUM_PERM)
    m.hashvalues = np.array(digest, dtype=m.hashvalues.dtype)
    return m


@dataclass
class DedupIndex:
    """In-process LSH index, seeded from a manifest and updated as new
    documents are promoted within the same curation run."""

    lsh: MinHashLSH
    signatures: dict = field(default_factory=dict)   # content_hash -> MinHash
    cluster_of: dict = field(default_factory=dict)    # content_hash -> canonical cluster content_hash

    @classmethod
    def empty(cls) -> "DedupIndex":
        return cls(lsh=MinHashLSH(threshold=JACCARD_THRESHOLD, num_perm=NUM_PERM))

    @classmethod
    def from_manifest_rows(cls, rows: list[dict]) -> "DedupIndex":
        index = cls.empty()
        for row in rows:
            m = signature_from_digest(list(row["minhash_signature"]))
            index.lsh.insert(row["content_hash"], m)
            index.signatures[row["content_hash"]] = m
            index.cluster_of[row["content_hash"]] = row["cluster_id"]
        return index

    def manifest_rows(self) -> list[dict]:
        return [
            {
                "content_hash": h,
                "cluster_id": self.cluster_of[h],
                "minhash_signature": signature_to_digest(self.signatures[h]),
            }
            for h in self.signatures
        ]

    def check_and_add(self, content_hash: str, m: MinHash) -> str:
        """Returns this document's cluster id. Raises DuplicateError if it
        collides with an already-indexed document above JACCARD_THRESHOLD."""
        matches = self.lsh.query(m)
        if matches:
            raise DuplicateError(duplicate_of=matches[0])
        self.lsh.insert(content_hash, m)
        self.signatures[content_hash] = m
        self.cluster_of[content_hash] = content_hash  # first-seen member is its own cluster id
        return content_hash


def load_manifest(silver) -> DedupIndex:
    """Load the persisted dedup index, or start empty if none exists yet
    (first curation run ever)."""
    silver.ensure_bucket()
    try:
        response = silver.client().get_object(silver.bucket, MANIFEST_KEY)
        try:
            data = response.read()
        finally:
            response.close()
            response.release_conn()
    except S3Error:
        return DedupIndex.empty()
    table = pq.read_table(io.BytesIO(data))
    return DedupIndex.from_manifest_rows(table.to_pylist())


def save_manifest(silver, index: DedupIndex) -> None:
    rows = index.manifest_rows()
    if not rows:
        return
    table = pa.table(
        {
            "content_hash": [r["content_hash"] for r in rows],
            "cluster_id": [r["cluster_id"] for r in rows],
            "minhash_signature": [r["minhash_signature"] for r in rows],
        }
    )
    buf = io.BytesIO()
    pq.write_table(table, buf)
    data = buf.getvalue()
    silver.ensure_bucket()
    silver.client().put_object(silver.bucket, MANIFEST_KEY, io.BytesIO(data), length=len(data))
```

- [ ] **Step 4: Run to verify pass**

```bash
tar czf - --exclude '.git' --exclude '__pycache__' --exclude '*.pyc' --exclude '.env' --exclude 'deepseek.key' --exclude 'data' src pyproject.toml tests deploy CLAUDE.md Makefile | ssh _59 'tar xzf - -C vietnlp'
ssh _59 'cd vietnlp/deploy && docker compose run --rm --entrypoint pytest agents /app/tests/test_curation_dedup.py -v'
```

Expected: PASS, 9 tests (the two live-manifest tests run for real against
`_59`'s MinIO; they self-skip on a machine without it).

- [ ] **Step 5: Commit**

```bash
git add src/vietnlp/curation/dedup.py tests/test_curation_dedup.py
git commit -m "feat: add MinHash cross-source dedup with a persisted manifest"
```

---

### Task 6: Heuristic quality score

**Files:**
- Create: `src/vietnlp/curation/quality.py`
- Create: `tests/test_curation_quality.py`

**Interfaces:**
- Consumes: existing `platform/agents/registry.py`'s `"quality-scorer"` agent
  (unchanged — used by Task 8, not by this module directly).
- Produces: `heuristic_score(text: str, stripped_text: str, lang_confidence:
  float) -> float`, `LowQuality`, `THRESHOLD_LOW = 2.0`, `THRESHOLD_HIGH =
  3.5`. Task 8 uses the thresholds to decide whether to dead-letter, accept
  the heuristic score, or ask the existing `quality-scorer` DeepSeek agent.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_curation_quality.py`:

```python
"""Heuristic quality score, 0-5 to match the DeepSeek quality-scorer agent's
own scale. The fixture corpus's sentences are short single-clause synthetic
records (median 77 chars) -- shorter than a typical real document -- so most
land in the borderline band by design; that is expected pipeline behavior,
not a miscalibration (see quality.py's module docstring)."""

import json
from pathlib import Path

from vietnlp.curation.boilerplate import strip_boilerplate
from vietnlp.curation.quality import THRESHOLD_LOW, heuristic_score

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "corpus" / "fixture_corpus.jsonl"


def test_short_low_script_ratio_text_scores_low():
    score = heuristic_score("12345 !!!", "12345 !!!", lang_confidence=0.1)
    assert score < THRESHOLD_LOW


def test_clean_full_length_vietnamese_text_scores_high():
    text = "Bộ Giáo dục và Đào tạo công bố lịch thi tốt nghiệp trung học phổ thông năm nay. " * 4
    score = heuristic_score(text, text, lang_confidence=0.95)
    assert score >= 4.0


def test_heavy_boilerplate_residue_lowers_the_score():
    original = "Nội dung.\n" + "© 2026 site.\n" * 20
    stripped = strip_boilerplate(original)
    with_residue = heuristic_score(original, stripped, lang_confidence=0.9)
    no_residue = heuristic_score(stripped, stripped, lang_confidence=0.9)
    assert with_residue < no_residue


def test_no_fixture_document_is_rejected_pre_deepseek():
    """None of the 100 hand-authored fixture sentences are spam or gibberish
    -- none should fall below THRESHOLD_LOW even though they are short."""
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)
            stripped = strip_boilerplate(record["text"])
            score = heuristic_score(record["text"], stripped, lang_confidence=0.9)
            assert score >= THRESHOLD_LOW, (record["text"], score)
```

- [ ] **Step 2: Run to verify failure**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_curation_quality.py -v'
```

Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

Create `src/vietnlp/curation/quality.py`:

```python
"""Heuristic quality score -- a 0-5 scale matching the DeepSeek
quality-scorer agent's own scale (registry.py's "quality-scorer"), so the
two are directly comparable and a borderline document's DeepSeek verdict
simply replaces the heuristic one rather than needing a separate scale.

Below THRESHOLD_LOW: dead-lettered without spending on DeepSeek -- a
heuristically bad document is not worth a paid opinion (spec: "below-
threshold documents are dead-lettered as low_quality"). Between the
thresholds: DeepSeek's verdict is authoritative (spec: "invoked only for the
borderline band"). At or above THRESHOLD_HIGH: the heuristic score stands.

Note: the committed fixture corpus's sentences are short, single-clause
synthetic records (median ~77 characters) -- shorter than a typical real
acquired document. Most therefore land in the borderline band under these
thresholds by construction, which correctly exercises both the heuristic and
the DeepSeek-borderline code paths in the same golden-file run (Task 11);
it is not evidence the thresholds are wrong for real, full-length documents.
"""

from __future__ import annotations

import re

THRESHOLD_LOW = 2.0
THRESHOLD_HIGH = 3.5

_MIN_FULL_CREDIT_CHARS = 200
_MAX_FULL_CREDIT_CHARS = 5000
_MIN_CHARS = 50

_VIETNAMESE_LETTER = re.compile(r"[A-Za-zÀ-ỹĐđ]")


class LowQuality(RuntimeError):
    """Raised when the heuristic score is below THRESHOLD_LOW -- a
    dead-letter condition, no DeepSeek call spent on it."""


def _length_score(text: str) -> float:
    n = len(text)
    if n < _MIN_CHARS:
        return 0.0
    if n < _MIN_FULL_CREDIT_CHARS:
        return 5.0 * (n - _MIN_CHARS) / (_MIN_FULL_CREDIT_CHARS - _MIN_CHARS)
    if n <= _MAX_FULL_CREDIT_CHARS:
        return 5.0
    return 4.0  # very long dumped multi-article scrapes lose a little credit, not rejected outright


def _script_ratio_score(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    vietnamese = sum(1 for c in letters if _VIETNAMESE_LETTER.match(c))
    return 5.0 * (vietnamese / len(letters))


def _boilerplate_residue_score(text: str, stripped_text: str) -> float:
    if not text:
        return 0.0
    removed_fraction = 1.0 - (len(stripped_text) / len(text))
    return max(0.0, 5.0 * (1.0 - removed_fraction * 4))  # >12.5% removed -> 0


def heuristic_score(text: str, stripped_text: str, lang_confidence: float) -> float:
    """Weighted average of four 0-5 sub-scores. Length and script ratio
    dominate because they are the two hardest signals to fake."""
    components = [
        (_length_score(stripped_text), 0.35),
        (_script_ratio_score(stripped_text), 0.35),
        (_boilerplate_residue_score(text, stripped_text), 0.15),
        (5.0 * lang_confidence, 0.15),
    ]
    return sum(score * weight for score, weight in components)
```

- [ ] **Step 4: Run to verify pass**

```bash
tar czf - --exclude '.git' --exclude '__pycache__' --exclude '*.pyc' --exclude '.env' --exclude 'deepseek.key' --exclude 'data' src pyproject.toml tests deploy CLAUDE.md Makefile | ssh _59 'tar xzf - -C vietnlp'
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_curation_quality.py -v'
```

Expected: PASS, 4 tests.

- [ ] **Step 5: Commit**

```bash
git add src/vietnlp/curation/quality.py tests/test_curation_quality.py
git commit -m "feat: add heuristic quality score for curation's borderline gate"
```

---

### Task 7: PII scrub (regex + DeepSeek fallback)

**Files:**
- Create: `src/vietnlp/curation/pii.py`
- Modify: `src/vietnlp/platform/agents/registry.py`
- Create: `tests/test_curation_pii.py`
- Modify: `tests/test_registry.py`

**Interfaces:**
- Consumes: `platform/agents/client.py`'s `AgentClient`,
  `platform/agents/registry.py`'s `get()`/`ValidationFailed` (existing).
- Produces: `regex_scrub(text: str) -> tuple[str, bool]`,
  `has_ambiguous_span(text: str) -> bool`, `scrub(text: str, client:
  AgentClient) -> tuple[str, bool]`; a new `"pii-scrubber"` agent in
  `registry.AGENTS`. Task 8 calls `scrub` as curation's sixth stage.

- [ ] **Step 1: Write the failing regex/orchestration tests**

Create `tests/test_curation_pii.py`:

```python
"""PII scrub: regex first, DeepSeek fallback only when a regex-ambiguous
digit span survives (spec's stated cost model -- not on every document).
The DeepSeek call is mocked via httpx.MockTransport, same pattern as
tests/test_client_flow.py."""

import json
from pathlib import Path

import httpx
import pytest

from vietnlp.curation.pii import has_ambiguous_span, regex_scrub, scrub
from vietnlp.platform.agents.budget import BudgetLedger
from vietnlp.platform.agents.cache import ResponseCache
from vietnlp.platform.agents.client import AgentClient

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "corpus" / "fixture_corpus.jsonl"


def test_scrubs_a_vietnamese_mobile_number():
    text, changed = regex_scrub("Gọi tôi qua số 0912345678 nhé.")
    assert "[PHONE]" in text and "0912345678" not in text
    assert changed


def test_scrubs_a_national_id():
    text, changed = regex_scrub("CCCD của tôi là 012345678912.")
    assert "[ID]" in text
    assert changed


def test_scrubs_an_email():
    text, _ = regex_scrub("Liên hệ qua nguyen.van.a@example.com để biết thêm.")
    assert "[EMAIL]" in text and "@example.com" not in text


def test_scrubs_an_address():
    text, _ = regex_scrub("Tôi ở số 12 đường Lê Lợi, quận 1.")
    assert "[ADDRESS]" in text


def test_scrubs_a_handle():
    text, _ = regex_scrub("Theo dõi mình tại @nguyenvana nhé.")
    assert "[HANDLE]" in text and "@nguyenvana" not in text


def test_clean_text_is_unchanged():
    text, changed = regex_scrub("Hôm nay trời đẹp quá.")
    assert text == "Hôm nay trời đẹp quá."
    assert not changed


def test_has_ambiguous_span_true_for_unclassified_digit_run():
    assert has_ambiguous_span("Mã đơn hàng của bạn là 987654321.")


def test_has_ambiguous_span_false_for_clean_text():
    assert not has_ambiguous_span("Không có gì đặc biệt ở đây.")


def test_fixture_corpus_has_no_regex_pii_and_no_ambiguous_spans():
    """Golden-file check: the synthetic fixture corpus has no real personal
    data, so scrub() must never need to call DeepSeek on it."""
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)
            text = record["text"]
            scrubbed, changed = regex_scrub(text)
            assert scrubbed == text and not changed
            assert not has_ambiguous_span(text)


def _client_with_handler(tmp_path, monkeypatch, handler):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-not-real")
    c = AgentClient(
        flow_run_id="pii-test",
        ledger=BudgetLedger(tmp_path / "b.db", flow_cap_usd=1.0, daily_cap_usd=1.0, total_cap_usd=1.0),
        cache=ResponseCache(tmp_path / "c.db"),
    )
    c._client = httpx.Client(
        base_url="https://api.deepseek.test",
        transport=httpx.MockTransport(handler),
        headers={"Authorization": "Bearer test-key-not-real"},
    )
    return c


def test_scrub_does_not_call_deepseek_without_an_ambiguous_span(tmp_path, monkeypatch):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"spans": []}'}}],
                                          "usage": {"prompt_tokens": 1, "completion_tokens": 1}})

    client = _client_with_handler(tmp_path, monkeypatch, handler)
    scrubbed, changed = scrub("Trời hôm nay thật đẹp.", client)
    assert calls == []
    assert not changed


def test_scrub_calls_deepseek_and_redacts_a_found_person_name(tmp_path, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        content = '{"spans": [{"text": "Nguyễn Văn A", "label": "PERSON"}]}'
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}],
                                          "usage": {"prompt_tokens": 1, "completion_tokens": 1}})

    client = _client_with_handler(tmp_path, monkeypatch, handler)
    scrubbed, changed = scrub("Đơn hàng 987654321 của Nguyễn Văn A đã được giao.", client)
    assert "[PERSON]" in scrubbed
    assert "Nguyễn Văn A" not in scrubbed
    assert changed
```

- [ ] **Step 2: Run to verify failure**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_curation_pii.py -v'
```

Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implement `pii.py`**

Create `src/vietnlp/curation/pii.py`:

```python
"""Regex-first PII scrub with a DeepSeek fallback for ambiguous spans and
person names (spec: "regex first ... DeepSeek fallback only on regex-
ambiguous spans"). Scrubbed spans become typed placeholders, never bare
deletions, so sentence structure survives for later tokenization (P2).
"""

from __future__ import annotations

import re

_PHONE = re.compile(r"(?<!\d)(?:\+84|0)(?:3|5|7|8|9)\d{8}(?!\d)")
_CCCD = re.compile(r"(?<!\d)\d{12}(?!\d)")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_ADDRESS = re.compile(r"\bsố\s+\d+[,\s]+(?:đường|phố|ngõ|ngách)\s+[^\n,.;]+", re.IGNORECASE)
_HANDLE = re.compile(r"(?<!\w)@[A-Za-z0-9_.]{2,30}")
# A 9-12 digit run that is neither a matched phone nor a matched CCCD is not
# confidently anything -- regex cannot tell a stray ID number from an order
# code. DeepSeek adjudicates these (and, in the same call, catches person
# names regex cannot detect at all).
_AMBIGUOUS_DIGITS = re.compile(r"(?<!\d)\d{9,12}(?!\d)")

_REGEX_PASSES = [
    (_PHONE, "[PHONE]"),
    (_CCCD, "[ID]"),
    (_EMAIL, "[EMAIL]"),
    (_ADDRESS, "[ADDRESS]"),
    (_HANDLE, "[HANDLE]"),
]


def regex_scrub(text: str) -> tuple[str, bool]:
    """Applies every regex pass in order. Returns (scrubbed_text, changed)."""
    changed = False
    for pattern, placeholder in _REGEX_PASSES:
        text, n = pattern.subn(placeholder, text)
        changed = changed or n > 0
    return text, changed


def has_ambiguous_span(text: str) -> bool:
    """True if a digit run survived regex_scrub that regex could not
    confidently classify -- this, and only this, triggers the DeepSeek
    fallback (spec's stated cost model: not every document)."""
    return bool(_AMBIGUOUS_DIGITS.search(text))


def scrub(text: str, client) -> tuple[str, bool]:
    """Full PII scrub: regex passes, then a DeepSeek fallback call only when
    an ambiguous digit span survives. Returns (scrubbed_text, was_scrubbed).
    """
    from vietnlp.platform.agents.registry import get

    scrubbed, changed = regex_scrub(text)
    if has_ambiguous_span(scrubbed):
        spans, _result = get("pii-scrubber").run(client, scrubbed)
        for span in sorted(spans, key=lambda s: -s["start"]):  # right-to-left keeps earlier offsets valid
            scrubbed = scrubbed[: span["start"]] + f"[{span['label']}]" + scrubbed[span["end"] :]
            changed = True
    return scrubbed, changed
```

- [ ] **Step 4: Register the `pii-scrubber` agent**

In `src/vietnlp/platform/agents/registry.py`, add a new validator right
after `_validate_ner` (reuses the exact same anti-hallucination pattern:
locate the model's claimed text in the source, reject anything that does not
occur verbatim):

```python
_PII_LABELS = frozenset({"PERSON", "PHONE", "ID", "EMAIL", "ADDRESS", "HANDLE"})


def _validate_pii(parsed: Any, source: str) -> list[dict]:
    """Anti-hallucination pattern identical to _validate_ner: the model names
    text, we locate it ourselves. A span that does not occur verbatim in the
    source cannot be redacted -- it is rejected, not guessed at."""
    spans = parsed.get("spans") if isinstance(parsed, dict) else None
    if not isinstance(spans, list):
        raise ValidationFailed("expected 'spans' list")

    normalized = unicodedata.normalize("NFC", source)
    out: list[dict] = []
    cursors: dict[str, int] = {}
    for i, span in enumerate(spans):
        if not isinstance(span, dict):
            raise ValidationFailed(f"span {i} is not an object")
        text, label = span.get("text"), span.get("label")
        if not isinstance(text, str) or not text.strip():
            raise ValidationFailed(f"span {i} has no text")
        if label not in _PII_LABELS:
            raise ValidationFailed(f"span {i} label {label!r} not in {sorted(_PII_LABELS)}")
        needle = unicodedata.normalize("NFC", text)
        start = normalized.find(needle, cursors.get(needle, 0))
        if start < 0:
            raise ValidationFailed(f"span {i} text {text!r} does not occur in the source -- hallucinated")
        end = start + len(needle)
        cursors[needle] = end
        out.append({"start": start, "end": end, "label": label, "text": needle})
    return out
```

Then, in the `AGENTS` list (right after the `ner-bootstrapper` entry), add:

```python
        Agent(
            name="pii-scrubber",
            task="pii_flag",
            prompt_version="v1",
            description="Adjudicates ambiguous digit spans and finds person names regex cannot.",
            system_prompt=(
                f"{_VI}\n\nFind personally-identifying spans: person names, and any phone "
                "number, national ID, email, address, or social-handle NOT already replaced "
                "by a [PLACEHOLDER] token. Copy each span's text EXACTLY as it appears. "
                'Reply {"spans": [{"text": "...", "label": "PERSON|PHONE|ID|EMAIL|ADDRESS|HANDLE"}]}.'
            ),
            validate=_validate_pii,
        ),
```

- [ ] **Step 5: Add the registry unit test**

In `tests/test_registry.py`, add (mirroring the file's existing style for
`ner-bootstrapper`):

```python
def test_pii_scrubber_rejects_a_hallucinated_span():
    with pytest.raises(ValidationFailed, match="hallucinated"):
        get("pii-scrubber").validate({"spans": [{"text": "not in source", "label": "PERSON"}]}, "Xin chào.")


def test_pii_scrubber_locates_a_real_span():
    result = get("pii-scrubber").validate({"spans": [{"text": "Nam", "label": "PERSON"}]}, "Nam đi học.")
    assert result == [{"start": 0, "end": 3, "label": "PERSON", "text": "Nam"}]
```

- [ ] **Step 6: Run to verify pass**

```bash
tar czf - --exclude '.git' --exclude '__pycache__' --exclude '*.pyc' --exclude '.env' --exclude 'deepseek.key' --exclude 'data' src pyproject.toml tests deploy CLAUDE.md Makefile | ssh _59 'tar xzf - -C vietnlp'
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_curation_pii.py /app/tests/test_registry.py -v'
```

Expected: PASS, all tests in both files (10 new in `test_curation_pii.py`, 2
new in `test_registry.py`, plus the full pre-existing `test_registry.py`
suite unchanged).

- [ ] **Step 7: Commit**

```bash
git add src/vietnlp/curation/pii.py src/vietnlp/platform/agents/registry.py \
        tests/test_curation_pii.py tests/test_registry.py
git commit -m "feat: add regex+DeepSeek PII scrub for curation"
```

---

### Task 8: `curation_flow` orchestration

**Files:**
- Create: `src/vietnlp/platform/flows/curation_flow.py`
- Create: `src/vietnlp/platform/db/migrations/0003_curation_processed.sql`
- Create: `tests/test_flows_curation.py` (unit-level tests only — the
  golden-file end-to-end test is Task 11)
- Test: `tests/test_db_migrate.py` (must stay green, unchanged)

**Interfaces:**
- Consumes: Task 2 (`SilverStore.put_record`), Task 3 (`strip_boilerplate`),
  Task 4 (`identify`, `LanguageIDError`), Task 5 (`DedupIndex`,
  `DuplicateError`, `compute_signature`, `signature_to_digest`,
  `load_manifest`, `save_manifest`), Task 6 (`heuristic_score`, `LowQuality`,
  `THRESHOLD_LOW`, `THRESHOLD_HIGH`), Task 7 (`pii.scrub`), existing
  `registry.get("register-classifier")` / `get("quality-scorer")`, existing
  `AgentClient`, `BudgetExceeded`, `ValidationFailed`.
- Produces: `curation_flow(records, silver, client, *, dedup_index=None,
  dead_letter_sink=None, promoted_sink=None) -> dict` (keys: `processed`,
  `dead_lettered`, `promoted`, `dedup_index`), `DeadLetterSink`,
  `PromotedSink`, `main()`. A new `curation_processed` Postgres table. Task
  10's Makefile target and Task 11's live verification depend on `main()`.

- [ ] **Step 1: Add the migration**

Create `src/vietnlp/platform/db/migrations/0003_curation_processed.sql`:

```sql
-- 0003_curation_processed.sql
-- Tracks which Bronze objects curation has already looked at, successfully
-- promoted or not -- so re-running curation_flow does not re-spend DeepSeek
-- calls on documents it has already adjudicated. Operational bookkeeping,
-- not corpus content (CLAUDE.md rule 3's projection rule governs
-- documents/sentences, not this table) -- the same carve-out already used
-- for `sources` and `dead_letters`.

CREATE TABLE IF NOT EXISTS curation_processed (
    bronze_uri   TEXT PRIMARY KEY,
    outcome      TEXT NOT NULL CHECK (outcome IN ('promoted', 'dead_lettered')),
    silver_uri   TEXT,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

- [ ] **Step 2: Run the migration test suite to confirm it applies cleanly**

```bash
tar czf - --exclude '.git' --exclude '__pycache__' --exclude '*.pyc' --exclude '.env' --exclude 'deepseek.key' --exclude 'data' src pyproject.toml tests deploy CLAUDE.md Makefile | ssh _59 'tar xzf - -C vietnlp'
ssh _59 'cd vietnlp/deploy && docker compose run --rm --entrypoint pytest agents /app/tests/test_db_migrate.py -v'
```

Expected: PASS, same test count as before this task — `test_db_migrate.py`
discovers migrations generically by scanning the directory, so a new,
syntactically valid file needs no test changes to be picked up.

- [ ] **Step 3: Write the failing unit tests for `curation_flow`**

Create `tests/test_flows_curation.py`:

```python
"""Unit-level curation_flow tests: dead-letter routing, the budget-exceeded
hard-stop, and promoted-record shape. The full golden-file run against all
100 fixture documents is tests/test_flows_curation_e2e.py (Task 11) -- kept
separate so this file's failures are fast to localize to one stage."""

import httpx
import pytest

from vietnlp.curation.dedup import DuplicateError
from vietnlp.curation.lang_id import LanguageIDError
from vietnlp.platform.agents.budget import BudgetExceeded, BudgetLedger
from vietnlp.platform.agents.cache import ResponseCache
from vietnlp.platform.agents.client import AgentClient
from vietnlp.platform.flows.curation_flow import curation_flow


class _FakeSilver:
    def __init__(self):
        self.records: list[dict] = []

    def put_record(self, record: dict) -> str:
        key = f"silver/{record['source_id']}/fake/{len(self.records)}.parquet"
        self.records.append(record)
        return key


def _bronze_record(text: str, bronze_uri: str = "bronze/fixture-formal/2026-08-23/x.parquet") -> dict:
    return {
        "bronze_uri": bronze_uri,
        "content_hash": "deadbeef",
        "source_id": "fixture-formal",
        "url": "https://fixture.local/x",
        "fetched_at": "2026-08-23T00:00:00+00:00",
        "raw_payload": text.encode("utf-8"),
    }


def _deepseek_handler(request: httpx.Request) -> httpx.Response:
    import json as _json

    body = _json.loads(request.content)
    system = body["messages"][0]["content"]
    if "Classify the register" in system:
        content = '{"register": "formal"}'
    elif "Rate the document" in system:
        content = '{"score": 4.5, "reason": "ok"}'
    else:
        content = '{"spans": []}'
    return httpx.Response(
        200,
        json={
            "choices": [{"message": {"content": content}}],
            "usage": {"prompt_tokens": 50, "completion_tokens": 10, "prompt_cache_hit_tokens": 0},
        },
    )


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-not-real")
    c = AgentClient(
        flow_run_id="curation-unit-test",
        ledger=BudgetLedger(tmp_path / "b.db", flow_cap_usd=5.0, daily_cap_usd=5.0, total_cap_usd=5.0),
        cache=ResponseCache(tmp_path / "c.db"),
    )
    c._client = httpx.Client(
        base_url="https://api.deepseek.test",
        transport=httpx.MockTransport(_deepseek_handler),
        headers={"Authorization": "Bearer test-key-not-real"},
    )
    return c


def test_promotes_a_clean_document(client):
    silver = _FakeSilver()
    result = curation_flow(
        iter([_bronze_record("Bộ Giáo dục và Đào tạo công bố lịch thi tốt nghiệp trung học phổ thông năm nay.")]),
        silver, client,
    )
    assert result == {"processed": 1, "dead_lettered": 0, "promoted": 1, "dedup_index": result["dedup_index"]}
    assert len(silver.records) == 1
    assert silver.records[0]["register"] == "formal"


def test_dead_letters_a_duplicate_without_calling_deepseek_twice(client):
    silver = _FakeSilver()
    dead = []
    text = "Ngân hàng Nhà nước giữ nguyên lãi suất điều hành trong quý này."
    records = [_bronze_record(text, "bronze/a.parquet"), _bronze_record(text, "bronze/b.parquet")]

    result = curation_flow(iter(records), silver, client, dead_letter_sink=lambda item: dead.append(item))

    assert result["promoted"] == 1
    assert result["dead_lettered"] == 1
    assert len(dead) == 1
    assert "near-duplicate" in dead[0][1]


def test_dead_letters_non_vietnamese_text(client):
    silver = _FakeSilver()
    dead = []
    records = [_bronze_record("The Ministry of Education announced the exam schedule today for everyone.")]

    result = curation_flow(iter(records), silver, client, dead_letter_sink=lambda item: dead.append(item))

    assert result["dead_lettered"] == 1
    assert result["promoted"] == 0
    assert len(dead) == 1


def test_budget_exceeded_propagates_and_aborts_the_flow(client, tmp_path):
    """CLAUDE.md rule 5: caps hard-stop, they do not warn. This is the
    load-bearing assertion for that rule at curation's layer -- a budget
    breach on record 2 of 3 must abort the whole flow, not just skip record 2."""
    from vietnlp.platform.agents.policy import Model

    silver = _FakeSilver()
    client.ledger.record(
        flow_run_id="curation-unit-test", task="language_register", model=Model.CHAT,
        input_tokens=10_000_000, cached_tokens=0, output_tokens=0,
    )
    records = [_bronze_record("Một câu tiếng Việt hợp lệ để kiểm tra ngân sách.")]

    with pytest.raises(BudgetExceeded):
        curation_flow(iter(records), silver, client)
    assert silver.records == [], "budget must be checked before any record is promoted"
```

- [ ] **Step 4: Run to verify failure**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_flows_curation.py -v'
```

Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 5: Implement `curation_flow.py`**

Create `src/vietnlp/platform/flows/curation_flow.py`:

```python
"""Curation orchestration: Bronze -> Silver, one Prefect task per stage,
following bootstrap_flow.py's validate-then-dead-letter shape exactly.

Budget caps are a hard stop, not a per-record condition (CLAUDE.md rule 5):
BudgetExceeded is deliberately NOT in `_REJECTIONS` below -- it must
propagate out of the flow and abort the whole run. Catching it per-record
would turn a hard stop into a per-document warning while still spending on
every later record.
"""

from __future__ import annotations

import datetime as _dt
import os
from typing import Callable, Iterable

from prefect import flow, task

from vietnlp.curation.boilerplate import strip_boilerplate
from vietnlp.curation.dedup import (
    DedupIndex, DuplicateError, compute_signature, signature_to_digest,
)
from vietnlp.curation.lang_id import LanguageIDError, identify
from vietnlp.curation.pii import scrub as pii_scrub
from vietnlp.curation.quality import THRESHOLD_HIGH, THRESHOLD_LOW, LowQuality, heuristic_score
from vietnlp.platform.agents.client import AgentClient
from vietnlp.platform.agents.registry import ValidationFailed, get as get_agent
from vietnlp.platform.storage.bronze import content_hash

DeadLetterSink = Callable[[tuple[dict, str]], None]
PromotedSink = Callable[[dict, str], None]

_REJECTIONS = (DuplicateError, LanguageIDError, LowQuality, ValidationFailed)


@task
def _boilerplate_strip_task(record: dict) -> tuple[str, str]:
    text = record["raw_payload"]
    text = text.decode("utf-8") if isinstance(text, bytes) else text
    return text, strip_boilerplate(text)


@task
def _dedup_task(stripped: str, index: DedupIndex) -> str:
    h = content_hash(stripped.encode("utf-8"))
    return index.check_and_add(h, compute_signature(stripped))  # raises DuplicateError


@task
def _lang_id_task(stripped: str) -> tuple[str, float]:
    return identify(stripped)  # raises LanguageIDError


@task(retries=2, retry_delay_seconds=2)
def _register_classify_task(stripped: str, client: AgentClient) -> str:
    validated, _result = get_agent("register-classifier").run(client, stripped)
    return validated["register"]


@task(retries=2, retry_delay_seconds=2)
def _quality_score_task(text: str, stripped: str, lang_confidence: float, client: AgentClient) -> float:
    score = heuristic_score(text, stripped, lang_confidence)
    if score < THRESHOLD_LOW:
        raise LowQuality(f"heuristic score {score:.2f} below {THRESHOLD_LOW}")
    if score < THRESHOLD_HIGH:
        validated, _result = get_agent("quality-scorer").run(client, stripped)
        return validated["score"]
    return score


@task(retries=2, retry_delay_seconds=2)
def _pii_scrub_task(stripped: str, client: AgentClient) -> tuple[str, bool]:
    return pii_scrub(stripped, client)


@flow(name="curation")
def curation_flow(
    records: Iterable[dict],
    silver,
    client: AgentClient,
    *,
    dedup_index: DedupIndex | None = None,
    dead_letter_sink: DeadLetterSink | None = None,
    promoted_sink: PromotedSink | None = None,
) -> dict:
    """`records` are raw Bronze record dicts (as returned by
    `BronzeStore.get_record`), each with `record["bronze_uri"]` additionally
    set by the caller to the key it was read from -- Bronze's own stored
    fields do not include the object's own key."""
    index = dedup_index if dedup_index is not None else DedupIndex.empty()
    processed = 0
    dead_lettered = 0
    promoted = 0

    for record in records:
        try:
            text, stripped = _boilerplate_strip_task(record)
            content_hash_hex = _dedup_task(stripped, index)
            lang, confidence = _lang_id_task(stripped)
            register = _register_classify_task(stripped, client)
            score = _quality_score_task(text, stripped, confidence, client)
            scrubbed, was_scrubbed = _pii_scrub_task(stripped, client)

            silver_uri = silver.put_record(
                {
                    "bronze_uri": record["bronze_uri"],
                    "source_id": record["source_id"],
                    "url": record["url"],
                    "fetched_at": record["fetched_at"],
                    "curated_at": _dt.datetime.now(_dt.timezone.utc),
                    "text": scrubbed,
                    "lang": lang,
                    "register": register,
                    "quality_score": score,
                    "dedup_cluster_id": index.cluster_of[content_hash_hex],
                    "pii_scrubbed": was_scrubbed,
                    "minhash_signature": signature_to_digest(index.signatures[content_hash_hex]),
                }
            )
            if promoted_sink is not None:
                promoted_sink(record, silver_uri)
            promoted += 1
            processed += 1
        except _REJECTIONS as exc:
            dead_lettered += 1
            processed += 1
            if dead_letter_sink is not None:
                dead_letter_sink((record, str(exc)))
        # BudgetExceeded is NOT in _REJECTIONS -- it propagates and aborts
        # the flow (CLAUDE.md rule 5: caps hard-stop, they do not warn).

    return {"processed": processed, "dead_lettered": dead_lettered, "promoted": promoted, "dedup_index": index}


def main(argv: list[str] | None = None) -> int:
    import sys
    import uuid

    import psycopg

    from vietnlp.curation.dedup import load_manifest, save_manifest
    from vietnlp.platform.db.migrate import DEFAULT_DATABASE_URL
    from vietnlp.platform.storage.bronze import BronzeStore
    from vietnlp.platform.storage.silver import SilverStore

    argv = sys.argv[1:] if argv is None else argv
    limit = int(argv[argv.index("--limit") + 1]) if "--limit" in argv else None

    database_url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    bronze = BronzeStore.from_env()
    silver = SilverStore.from_env()
    flow_run_id = os.getenv("VIETNLP_FLOW_RUN_ID") or f"curation-{uuid.uuid4().hex[:8]}"

    with psycopg.connect(database_url) as conn:
        already = {r[0] for r in conn.execute("SELECT bronze_uri FROM curation_processed").fetchall()}
    pending = [k for k in bronze.list_keys() if k not in already]
    if limit is not None:
        pending = pending[:limit]

    def _load(key: str) -> dict:
        record = bronze.get_record(key)
        record["bronze_uri"] = key
        return record

    def _dead_letter_sink(item: tuple[dict, str]) -> None:
        record, reason = item
        with psycopg.connect(database_url) as conn:
            conn.execute(
                "INSERT INTO dead_letters (stage, content_hash, error, payload_uri) VALUES (%s, %s, %s, %s)",
                ("curation", record.get("content_hash"), reason, record.get("bronze_uri")),
            )
            conn.execute(
                "INSERT INTO curation_processed (bronze_uri, outcome) VALUES (%s, 'dead_lettered') "
                "ON CONFLICT (bronze_uri) DO NOTHING",
                (record.get("bronze_uri"),),
            )

    def _promoted_sink(record: dict, silver_uri: str) -> None:
        with psycopg.connect(database_url) as conn:
            conn.execute(
                "INSERT INTO curation_processed (bronze_uri, outcome, silver_uri) VALUES (%s, 'promoted', %s) "
                "ON CONFLICT (bronze_uri) DO NOTHING",
                (record.get("bronze_uri"), silver_uri),
            )

    index = load_manifest(silver)
    with AgentClient(flow_run_id=flow_run_id) as client:
        result = curation_flow(
            (_load(k) for k in pending), silver, client,
            dedup_index=index, dead_letter_sink=_dead_letter_sink, promoted_sink=_promoted_sink,
        )
    save_manifest(silver, result["dedup_index"])
    print({k: v for k, v in result.items() if k != "dedup_index"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Run to verify pass**

```bash
tar czf - --exclude '.git' --exclude '__pycache__' --exclude '*.pyc' --exclude '.env' --exclude 'deepseek.key' --exclude 'data' src pyproject.toml tests deploy CLAUDE.md Makefile | ssh _59 'tar xzf - -C vietnlp'
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_flows_curation.py -v'
```

Expected: PASS, 4 tests.

- [ ] **Step 7: Commit**

```bash
git add src/vietnlp/platform/flows/curation_flow.py \
        src/vietnlp/platform/db/migrations/0003_curation_processed.sql \
        tests/test_flows_curation.py
git commit -m "feat: wire curation_flow (Bronze -> Silver, 7 stages, dead-letter + budget hard-stop)"
```

---

### Task 9: Sentence splitter + Postgres projector

**Files:**
- Create: `src/vietnlp/platform/db/sentence_split.py`
- Create: `src/vietnlp/platform/db/silver_projector.py`
- Create: `src/vietnlp/platform/db/migrations/0004_silver_projection_marker.sql`
- Create: `tests/test_db_sentence_split.py`
- Create: `tests/test_db_silver_projector.py`

**Interfaces:**
- Consumes: Task 2's `SilverStore.get_record`/`list_keys`, Task 8's Silver
  record shape (`content_hash, bronze_uri, source_id, url, fetched_at, lang,
  register, quality_score, text`), the existing `sources`/`documents`/
  `sentences` tables (P0 migration `0001`).
- Produces: `split_sentences(text: str) -> list[tuple[str, int, int]]`,
  `project_pending(database_url: str, silver) -> dict`, `main()`. Task 10's
  Makefile target and Task 11's live verification depend on `main()`.

- [ ] **Step 1: Write the failing sentence-splitter tests**

Create `tests/test_db_sentence_split.py`:

```python
"""Light rule-based Vietnamese sentence segmentation -- good enough to
populate sentences.idx/text/char_start/char_end for P2 to annotate later,
not the real UD-parse pipeline."""

from vietnlp.platform.db.sentence_split import split_sentences


def test_single_sentence_spans_the_whole_trimmed_text():
    text = "Trời hôm nay thật đẹp."
    result = split_sentences(text)
    assert result == [("Trời hôm nay thật đẹp.", 0, len(text))]


def test_splits_two_sentences_with_correct_offsets():
    text = "Trời đẹp. Đi chơi không?"
    result = split_sentences(text)
    assert [s[0] for s in result] == ["Trời đẹp.", "Đi chơi không?"]
    for sentence, start, end in result:
        assert text[start:end] == sentence


def test_does_not_split_on_a_known_abbreviation():
    text = "TP. Hồ Chí Minh có nhiều công viên."
    result = split_sentences(text)
    assert len(result) == 1
    assert result[0][0] == text


def test_handles_leading_and_trailing_whitespace():
    text = "  Câu có khoảng trắng thừa.  "
    result = split_sentences(text)
    assert result == [("Câu có khoảng trắng thừa.", 2, 2 + len("Câu có khoảng trắng thừa."))]


def test_empty_text_yields_no_sentences():
    assert split_sentences("") == []
    assert split_sentences("   ") == []
```

- [ ] **Step 2: Run to verify failure**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_db_sentence_split.py -v'
```

Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implement the splitter**

Create `src/vietnlp/platform/db/sentence_split.py`:

```python
"""Light rule-based Vietnamese sentence segmentation for the Silver ->
Postgres projector. Not the real UD-parse pipeline (P2's job) -- this only
needs to be good enough to populate `sentences.idx/text/char_start/char_end`
so P2 has something to annotate. Sentence-final punctuation is the same as
English (. ! ?); the abbreviation guard list exists so common abbreviations
do not split a sentence in the middle.
"""

from __future__ import annotations

import re

# Not exhaustive -- P2's real tokenizer replaces this. Only covers the most
# common false-split cases.
_ABBREVIATIONS = {
    "tp", "ts", "ths", "pgs", "gs", "tskh", "vnd", "no", "km", "cm", "mm",
    "kg", "ông", "bà", "stt", "vd", "vv",
}

_SENTENCE_END = re.compile(r"([.!?]+)(\s+|$)")


def split_sentences(text: str) -> list[tuple[str, int, int]]:
    """Returns [(sentence_text, char_start, char_end), ...] over `text`."""
    sentences: list[tuple[str, int, int]] = []
    start = 0
    for match in _SENTENCE_END.finditer(text):
        end = match.end(1)
        raw = text[start:end]
        candidate = raw.strip()
        if not candidate:
            start = match.end()
            continue
        last_word = re.split(r"[\s.]+", candidate.rstrip("."))[-1].lower()
        if last_word in _ABBREVIATIONS and match.end() < len(text):
            continue  # false split (abbreviation) -- keep accumulating past it
        stripped_start = start + (len(raw) - len(raw.lstrip()))
        sentences.append((candidate, stripped_start, stripped_start + len(candidate)))
        start = match.end()
    raw = text[start:]
    candidate = raw.strip()
    if candidate:
        stripped_start = start + (len(raw) - len(raw.lstrip()))
        sentences.append((candidate, stripped_start, stripped_start + len(candidate)))
    return sentences
```

- [ ] **Step 4: Run to verify pass**

```bash
tar czf - --exclude '.git' --exclude '__pycache__' --exclude '*.pyc' --exclude '.env' --exclude 'deepseek.key' --exclude 'data' src pyproject.toml tests deploy CLAUDE.md Makefile | ssh _59 'tar xzf - -C vietnlp'
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_db_sentence_split.py -v'
```

Expected: PASS, 5 tests.

- [ ] **Step 5: Add the projector's migration**

Create `src/vietnlp/platform/db/migrations/0004_silver_projection_marker.sql`:

```sql
-- 0004_silver_projection_marker.sql
-- Tracks which Silver objects have already been projected into
-- documents/sentences -- analogous to schema_migrations' own bookkeeping,
-- so the projector is idempotent and resumable. Rebuilding Postgres from
-- Silver: TRUNCATE documents, sentences, silver_projections CASCADE; rerun
-- the projector over all of Silver -- no re-curation needed.

CREATE TABLE IF NOT EXISTS silver_projections (
    silver_uri   TEXT PRIMARY KEY,
    document_id  BIGINT REFERENCES documents(id),
    projected_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

- [ ] **Step 6: Write the failing projector tests**

Create `tests/test_db_silver_projector.py`:

```python
"""silver_projector.py is the only code path permitted to write to
documents/sentences (CLAUDE.md rule 3). Needs a live Postgres with the
sources/documents/sentences/silver_projections tables migrated -- self-skips
via the live_db fixture otherwise."""

from vietnlp.acquisition.sources import register_source
from vietnlp.platform.db.migrate import apply
from vietnlp.platform.db.silver_projector import project_pending


class _FakeSilver:
    def __init__(self, records: dict):
        self._records = records

    def list_keys(self, prefix: str = "silver/") -> list[str]:
        return list(self._records)

    def get_record(self, key: str) -> dict:
        return self._records[key]


def _silver_record(**overrides) -> dict:
    base = {
        "content_hash": "hash-1", "bronze_uri": "bronze/fixture-formal/2026-08-23/x.parquet",
        "source_id": "fixture-formal", "url": "https://fixture.local/x",
        "fetched_at": "2026-08-23T00:00:00+00:00", "lang": "vi", "register": "formal",
        "quality_score": 4.5, "text": "Trời đẹp. Đi chơi không?",
    }
    base.update(overrides)
    return base


def test_projects_a_silver_document_into_documents_and_sentences(live_db):
    apply(live_db)
    register_source(live_db, "fixture-formal", "public_corpus")
    silver = _FakeSilver({"silver/fixture-formal/2026-08-23/hash-1.parquet": _silver_record()})

    result = project_pending(live_db, silver)
    assert result == {"projected": 1}

    import psycopg

    with psycopg.connect(live_db) as conn:
        doc = conn.execute("SELECT bronze_uri, lang, register FROM documents WHERE content_hash = %s", ("hash-1",)).fetchone()
        assert doc == ("bronze/fixture-formal/2026-08-23/x.parquet", "vi", "formal")
        sentences = conn.execute(
            "SELECT text FROM sentences s JOIN documents d ON s.document_id = d.id "
            "WHERE d.content_hash = %s ORDER BY s.idx", ("hash-1",),
        ).fetchall()
        assert [s[0] for s in sentences] == ["Trời đẹp.", "Đi chơi không?"]


def test_is_idempotent_across_two_runs(live_db):
    apply(live_db)
    register_source(live_db, "fixture-formal", "public_corpus")
    silver = _FakeSilver({"silver/fixture-formal/2026-08-23/hash-2.parquet": _silver_record(content_hash="hash-2")})

    first = project_pending(live_db, silver)
    second = project_pending(live_db, silver)
    assert first == {"projected": 1}
    assert second == {"projected": 0}


def test_skips_the_dedup_manifest_object(live_db):
    apply(live_db)
    silver = _FakeSilver({"silver/_dedup_manifest.parquet": {}})
    result = project_pending(live_db, silver)
    assert result == {"projected": 0}
```

Note all three tests call `apply(live_db)` first — `live_db` hands each test
a fresh, empty schema (see `tests/conftest.py`), so `silver_projections`
(this task's migration `0004`) does not exist until migrations run.

- [ ] **Step 7: Run to verify failure**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --entrypoint pytest agents /app/tests/test_db_silver_projector.py -v'
```

Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 8: Implement the projector**

Create `src/vietnlp/platform/db/silver_projector.py`:

```python
"""The only code path permitted to write to Postgres's documents/sentences
tables (CLAUDE.md rule 3: Postgres is a projection of Gold/Silver, never
hand-edited). Rebuilding Postgres from Silver: TRUNCATE documents,
sentences, silver_projections CASCADE; rerun project_pending() over all of
Silver -- no re-curation needed.
"""

from __future__ import annotations

import psycopg

from .sentence_split import split_sentences

_MANIFEST_SUFFIX = "_dedup_manifest.parquet"


def project_pending(database_url: str, silver) -> dict:
    projected = 0
    with psycopg.connect(database_url) as conn:
        already = {r[0] for r in conn.execute("SELECT silver_uri FROM silver_projections").fetchall()}
        for key in silver.list_keys():
            if key.endswith(_MANIFEST_SUFFIX) or key in already:
                continue
            record = silver.get_record(key)

            source_row = conn.execute("SELECT id FROM sources WHERE name = %s", (record["source_id"],)).fetchone()
            if source_row is None:
                raise ValueError(f"no sources row named {record['source_id']!r} for Silver key {key!r}")
            source_pk = source_row[0]

            doc_row = conn.execute(
                """
                INSERT INTO documents (content_hash, source_id, url, fetched_at, lang, register, quality_score, bronze_uri)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (content_hash) DO NOTHING
                RETURNING id
                """,
                (
                    record["content_hash"], source_pk, record["url"], record["fetched_at"],
                    record["lang"], record["register"], record["quality_score"], record["bronze_uri"],
                ),
            ).fetchone()
            if doc_row is None:
                doc_row = conn.execute("SELECT id FROM documents WHERE content_hash = %s", (record["content_hash"],)).fetchone()
            document_id = doc_row[0]

            for idx, (sentence_text, char_start, char_end) in enumerate(split_sentences(record["text"])):
                conn.execute(
                    """
                    INSERT INTO sentences (document_id, idx, text, char_start, char_end)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (document_id, idx) DO NOTHING
                    """,
                    (document_id, idx, sentence_text, char_start, char_end),
                )

            conn.execute(
                "INSERT INTO silver_projections (silver_uri, document_id) VALUES (%s, %s) "
                "ON CONFLICT (silver_uri) DO NOTHING",
                (key, document_id),
            )
            conn.commit()
            projected += 1
    return {"projected": projected}


def main(argv: list[str] | None = None) -> int:
    import os

    from vietnlp.platform.db.migrate import DEFAULT_DATABASE_URL
    from vietnlp.platform.storage.silver import SilverStore

    database_url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    result = project_pending(database_url, SilverStore.from_env())
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 9: Run to verify pass**

```bash
tar czf - --exclude '.git' --exclude '__pycache__' --exclude '*.pyc' --exclude '.env' --exclude 'deepseek.key' --exclude 'data' src pyproject.toml tests deploy CLAUDE.md Makefile | ssh _59 'tar xzf - -C vietnlp'
ssh _59 'cd vietnlp/deploy && docker compose run --rm --entrypoint pytest agents /app/tests/test_db_silver_projector.py -v'
```

Expected: PASS, 3 tests (needs live Postgres, present on `_59`).

- [ ] **Step 10: Commit**

```bash
git add src/vietnlp/platform/db/sentence_split.py \
        src/vietnlp/platform/db/silver_projector.py \
        src/vietnlp/platform/db/migrations/0004_silver_projection_marker.sql \
        tests/test_db_sentence_split.py tests/test_db_silver_projector.py
git commit -m "feat: add sentence splitter and the Silver-to-Postgres projector"
```

---

### Task 10: Operator wiring (Makefile, docs, budget sizing)

**Files:**
- Modify: `Makefile`
- Modify: `deploy/README.md`

**Interfaces:**
- Consumes: Task 8's `curation_flow.main()`, Task 9's `silver_projector.main()`.
- Produces: `make run-curation`, `make project` operator commands.

- [ ] **Step 1: Add the Makefile targets**

In `Makefile`, add after the existing `run-acquisition` target:

```makefile
.PHONY: run-curation
run-curation: ## run curation_flow over all pending Bronze documents ($(HOST)); ARGS optional (e.g. ARGS="--limit 500")
	ssh $(HOST) "cd $(REMOTE)/deploy && docker compose run --rm --entrypoint python agents -m vietnlp.platform.flows.curation_flow $(ARGS)"

.PHONY: project
project: ## project all pending Silver documents into Postgres documents/sentences ($(HOST))
	ssh $(HOST) "cd $(REMOTE)/deploy && docker compose run --rm --entrypoint python agents -m vietnlp.platform.db.silver_projector"
```

- [ ] **Step 2: Document the new commands and the budget-sizing procedure**

In `deploy/README.md`, add a section after the existing P1a acquisition
worked examples (find that section first; match its heading style):

```markdown
## P1b: curation

Before running curation unbounded, size DeepSeek spend against the caps —
register classification hits every surviving document (the dominant cost
driver; quality-score and PII only hit borderline/ambiguous cases):

    make agents estimate language_register --count 100000 --input-tokens 60

Run curation over a bounded batch first:

    make run-curation ARGS="--limit 500"

Then project the resulting Silver documents into Postgres:

    make project

Both commands are idempotent — re-running `run-curation` skips Bronze
objects already recorded in `curation_processed`, and `project` skips
Silver objects already recorded in `silver_projections`.
```

- [ ] **Step 3: Commit**

```bash
git add Makefile deploy/README.md
git commit -m "docs: wire make run-curation / make project, document budget sizing"
```

---

### Task 11: Golden-file end-to-end test + live verification

**Files:**
- Create: `tests/test_flows_curation_e2e.py`
- Modify: `tests/conftest.py` (adds `live_deepseek_client`)
- Test: `/app/tests` (full offline suite, must stay green)

**Interfaces:**
- Consumes: everything from Tasks 1-10.
- Produces: proof the whole Bronze-to-Postgres pipeline works, both offline
  (mocked DeepSeek) and live (real DeepSeek, Postgres, MinIO on `_59`); a
  `live_deepseek_client` fixture other DeepSeek-touching stages can reuse in
  future plans, mirroring `live_db`/`live_store`/`live_silver_store`.

- [ ] **Step 1: Write the golden-file end-to-end test**

Create `tests/test_flows_curation_e2e.py`:

```python
"""End-to-end curation_flow test against the full 100-document fixture
corpus, DeepSeek mocked (spec's Testing section: 'one golden-file test
asserting the fixture corpus's known-good register/quality distribution
survives curation unchanged'). No live services needed -- SilverStore is
swapped for an in-memory stand-in that only implements put_record, since
curation_flow no longer needs bucket/client access directly (dedup-manifest
persistence is the caller's concern, not the flow's -- see curation_flow.py)."""

import json
from pathlib import Path

import httpx
import pytest

from vietnlp.platform.agents.budget import BudgetLedger
from vietnlp.platform.agents.cache import ResponseCache
from vietnlp.platform.agents.client import AgentClient
from vietnlp.platform.flows.curation_flow import curation_flow

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "corpus" / "fixture_corpus.jsonl"


class _FakeSilver:
    def __init__(self):
        self.records: list[dict] = []

    def put_record(self, record: dict) -> str:
        key = f"silver/{record['source_id']}/fake/{len(self.records)}.parquet"
        self.records.append(record)
        return key


def _load_fixture_as_bronze_records() -> list[dict]:
    records = []
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            records.append(
                {
                    "bronze_uri": f"bronze/{r['source_id']}/2026-08-23/{r['content_hash']}.parquet",
                    "content_hash": r["content_hash"],
                    "source_id": r["source_id"],
                    "url": r["url"],
                    "fetched_at": r["fetched_at"],
                    "raw_payload": r["text"].encode("utf-8"),
                }
            )
    return records


def _deepseek_handler(request: httpx.Request) -> httpx.Response:
    import json as _json

    body = _json.loads(request.content)
    system = body["messages"][0]["content"]
    if "Classify the register" in system:
        content = '{"register": "informal"}'
    elif "Rate the document" in system:
        content = '{"score": 4.5, "reason": "ok"}'
    else:
        content = '{"spans": []}'
    return httpx.Response(
        200,
        json={
            "choices": [{"message": {"content": content}}],
            "usage": {"prompt_tokens": 50, "completion_tokens": 10, "prompt_cache_hit_tokens": 0},
        },
    )


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-not-real")
    c = AgentClient(
        flow_run_id="curation-e2e-test",
        ledger=BudgetLedger(tmp_path / "b.db", flow_cap_usd=5.0, daily_cap_usd=5.0, total_cap_usd=5.0),
        cache=ResponseCache(tmp_path / "c.db"),
    )
    c._client = httpx.Client(
        base_url="https://api.deepseek.test",
        transport=httpx.MockTransport(_deepseek_handler),
        headers={"Authorization": "Bearer test-key-not-real"},
    )
    return c


def test_full_fixture_corpus_survives_curation(client):
    records = _load_fixture_as_bronze_records()
    silver = _FakeSilver()
    dead = []

    result = curation_flow(iter(records), silver, client, dead_letter_sink=lambda item: dead.append(item))

    assert result["processed"] == 100
    assert result["dead_lettered"] == 0, dead
    assert result["promoted"] == 100
    assert len(silver.records) == 100
    for record in silver.records:
        assert record["lang"] == "vi"
        assert 0.0 <= record["quality_score"] <= 5.0
        assert isinstance(record["pii_scrubbed"], bool)
        assert record["dedup_cluster_id"]  # every survivor is its own cluster (no fixture dup)
```

- [ ] **Step 2: Add a self-skipping live-DeepSeek test**

Spec's Testing section calls for this explicitly, alongside the mocked
offline suite: "a separate self-skipping live-DeepSeek test analogous to
the live-DB/live-MinIO pattern." In `tests/conftest.py`, add:

```python
def _live_deepseek_client():
    import os

    from vietnlp.platform.agents.client import AgentClient, _read_api_key, DeepSeekError

    try:
        _read_api_key()
    except DeepSeekError:
        return None
    return AgentClient(flow_run_id=f"live-check-{os.getpid()}")


@pytest.fixture
def live_deepseek_client():
    client = _live_deepseek_client()
    if client is None:
        pytest.skip("no DEEPSEEK_API_KEY / deepseek.key; run with real credentials to exercise this")
    yield client
    client.close()
```

Then, in `tests/test_flows_curation_e2e.py`, add:

```python
def test_register_classifier_against_real_deepseek(live_deepseek_client):
    """--no-deps stays green and spend-free (the fixture self-skips without
    credentials); a live run proves the real DeepSeek call and response
    shape actually work end to end."""
    from vietnlp.platform.agents.registry import get

    validated, result = get("register-classifier").run(
        live_deepseek_client, "Hôm nay trời đẹp quá, đi chơi cà phê không?"
    )
    assert validated["register"] in {"formal", "informal", "teencode", "non_diacritic", "mixed"}
    assert result.cached is False
    assert result.usd >= 0.0
```

- [ ] **Step 3: Sync, rebuild, run the full offline suite**

```bash
tar czf - --exclude '.git' --exclude '__pycache__' --exclude '*.pyc' --exclude '.env' --exclude 'deepseek.key' --exclude 'data' src pyproject.toml tests deploy CLAUDE.md Makefile | ssh _59 'tar xzf - -C vietnlp'
ssh _59 'cd vietnlp/deploy && docker compose build agents'
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests -q'
```

Expected: PASS, every offline test in the repo (P0 + P1a + this plan's
tasks), no Postgres/MinIO required for this pass.

- [ ] **Step 4: Live verification — migrate, seed Bronze, run curation for real, project**

```bash
ssh _59 'cd vietnlp/deploy && docker compose up -d --remove-orphans'
ssh _59 'cd vietnlp/deploy && docker compose run --rm --entrypoint python agents -m vietnlp.platform.db.migrate up'

ssh _59 'cd vietnlp/deploy && docker compose run --rm --entrypoint python agents -c "
from datetime import datetime, timezone
from vietnlp.acquisition.sources import register_source
from vietnlp.platform.db.migrate import DEFAULT_DATABASE_URL
from vietnlp.platform.storage.bronze import BronzeStore
import os

database_url = os.getenv(\"DATABASE_URL\", DEFAULT_DATABASE_URL)
register_source(database_url, \"p1b-live-check\", \"public_corpus\", enabled=True)
bronze = BronzeStore.from_env()
key = bronze.put_record({
    \"source_id\": \"p1b-live-check\",
    \"url\": \"https://fixture.local/p1b-live-check/000\",
    \"fetched_at\": datetime.now(timezone.utc),
    \"http_status\": 200,
    \"robots_decision\": \"no_robots\",
    \"content_type\": \"text/plain; charset=utf-8\",
    \"raw_payload\": \"Thành phố Hà Nội triển khai thêm tuyến xe buýt điện phục vụ người dân.\".encode(\"utf-8\"),
    \"license\": \"synthetic-fixture\",
})
print(\"seeded Bronze key:\", key)
"'

ssh _59 'cd vietnlp/deploy && docker compose run --rm --entrypoint python agents -m vietnlp.platform.flows.curation_flow'
ssh _59 'cd vietnlp/deploy && docker compose run --rm --entrypoint python agents -m vietnlp.platform.db.silver_projector'

ssh _59 'cd vietnlp/deploy && docker compose run --rm --entrypoint python agents -c "
import os
import psycopg
from vietnlp.platform.db.migrate import DEFAULT_DATABASE_URL

database_url = os.getenv(\"DATABASE_URL\", DEFAULT_DATABASE_URL)
with psycopg.connect(database_url) as conn:
    row = conn.execute(
        \"SELECT d.lang, d.register, d.quality_score, s.text FROM documents d \"
        \"JOIN sentences s ON s.document_id = d.id \"
        \"JOIN sources src ON src.id = d.source_id WHERE src.name = %s\",
        (\"p1b-live-check\",),
    ).fetchone()
    print(\"projected row:\", row)
    assert row is not None, \"expected a projected sentence for the seeded document\"
"'
```

Expected: the register-classification call actually hits the real DeepSeek
API (spend recorded — check with `make spend`); the final query prints a
real `documents`/`sentences` row with `lang = "vi"` and a non-null
`quality_score`.

- [ ] **Step 5: Commit**

```bash
git add tests/test_flows_curation_e2e.py tests/conftest.py
git commit -m "test: add golden-file + live-DeepSeek end-to-end curation tests"
```

This is the plan's final task. Once its live verification is confirmed,
proceed to `superpowers:subagent-driven-development`'s final whole-branch
review, then `superpowers:finishing-a-development-branch`, exactly as P1a's
plan did.
