# VietNLP P0 Platform Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish P0 (platform bootstrap) so the exit criterion in the spec holds literally: `make up` brings the stack healthy, `make test` is green, and every later phase has a schema, a storage primitive, an orchestration primitive, and an offline fixture corpus to build on.

**Architecture:** Four new primitives sit alongside the already-deployed `platform/agents/` layer: a Postgres migration runner (`platform/db/`) that applies the §4.3 schema, a content-addressed MinIO Bronze store (`platform/storage/`), a Prefect 3 flow skeleton (`platform/flows/`) that proves retry/dead-letter wiring end-to-end on a committed 100-document synthetic fixture corpus, and a Fuseki dataset-provisioning helper (`platform/graph/`) that stays untested-in-production until P3 needs it. Every new integration point (Postgres, MinIO) gets a test that self-skips when the dependency is unreachable, so the default offline gate (`docker compose run --rm --no-deps ... pytest`) stays fast, and a live run against the deployed stack (Task 8) proves those same tests actually pass for real.

**Tech Stack:** Python 3.11, psycopg 3 (Postgres), pyarrow + minio-py (Bronze/MinIO), Prefect 3 (orchestration, ephemeral local mode — no server container), pandera + pandas (schema contracts), httpx + respx (Fuseki admin client + offline HTTP mocking, already a dev dependency).

**Spec:** `docs/superpowers/specs/2026-08-23-vietnamese-nlp-platform-design.md`

## Global Constraints

- Python 3.11 only (charter forbids the host's system 3.9). The Docker image already pins `python:3.11-slim`; nothing in this plan touches that.
- CLAUDE.md rule 1: Bronze is immutable, content-addressed by SHA-256. `BronzeStore.put_record` must derive `content_hash` itself and never trust a caller-supplied one.
- CLAUDE.md rule 2: DeepSeek output never enters Gold unvalidated. Not directly exercised by this plan (no DeepSeek calls here), but the validate-then-dead-letter pattern in Task 6 is the same shape P1/P2 will reuse for model output.
- CLAUDE.md rule 3: Postgres and Fuseki are projections, never hand-edited. Migrations in this plan are pure schema DDL — no data-fixing `UPDATE`/`DELETE` statements, ever.
- CLAUDE.md rule 4: no silent drops. A record that fails validation is dead-lettered with its exception, never dropped.
- Migrations are forward-only and idempotent (`CREATE ... IF NOT EXISTS` where relevant, tracked in a `schema_migrations` table).
- Existing `src/vietnlp/platform/agents/` (policy, budget, cache, client, registry, cli) is **done, tested, and deployed**. Nothing in this plan modifies its logic — only `deploy/Dockerfile` and `deploy/docker-compose.yml` get touched, and only to add new dependencies / raise one memory limit.
- Server `_59` (118.69.218.59) is a **shared** 8-vCPU/15-GB host, ~3-4 GB actually free, no GPU, ~12 unrelated containers already running. Every service has a hard memory limit. Free port block is 6040-6049; current allocations: postgres 6042, MinIO 6043/6044, Fuseki 6045 (profile-gated). Services bind to 127.0.0.1 only.
- `rsync` is not installed on `_59`; `deploy/deploy.sh` already uses tar-over-SSH. Do not reintroduce an rsync dependency.
- Secrets live only in `deploy/.env` on the server (mode 600, gitignored, never synced from/to the repo). Never echo a secret value, not even truncated.
- The default test gate (`docker compose run --rm --no-deps --entrypoint pytest agents /app/tests -q`, wired into `deploy/deploy.sh` and `make test`) must stay green **without** Postgres or MinIO running. New tests that need a live dependency self-skip via a connectivity probe in a fixture — see Task 3 and Task 4 for the exact pattern. Task 8 runs the suite again **with** dependencies up to prove those tests actually pass, not just skip.
- Bronze's real data contract (spec §4.1) uses `raw_payload: bytes`. The committed fixture corpus is plain-text JSONL and cannot hold raw bytes cleanly, so it substitutes a `text: str` field and its own schema (`FIXTURE_SCHEMA`, Task 5) — that schema is explicitly documented as validating the fixture's shape, not the production Bronze contract. Do not conflate the two.

---

### Task 1: New dependencies wired into the image

**Files:**
- Modify: `pyproject.toml`
- Modify: `deploy/Dockerfile`

**Interfaces:**
- Consumes: nothing.
- Produces: `psycopg`, `pyarrow`, `minio`, `prefect`, `pandera`, `pandas` and `respx` importable inside the built `vietnlp-agents` image. Every later task's code depends on these being present.

Two things are being fixed here, not just added: (1) `respx` is already declared as a dev dependency in `pyproject.toml` but the Dockerfile never installs it — Task 7's tests need it and would otherwise fail in the container while passing on nobody's machine, because nobody has run them anywhere yet. (2) the five new runtime dependencies for Tasks 2-7.

- [ ] **Step 1: Add the new dependencies to `pyproject.toml`**

Edit the `[project]` `dependencies` list and the `dev` extra:

```toml
[project]
name = "vietnlp"
version = "0.1.0"
description = "Vietnamese Language Understanding Platform"
requires-python = ">=3.11"
dependencies = [
    "httpx>=0.27",
    "psycopg[binary]>=3.1",
    "pyarrow>=15",
    "minio>=7.2",
    "prefect>=3.0",
    "pandera>=0.20",
    "pandas>=2.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "respx>=0.21"]

[project.scripts]
vietnlp-agents = "vietnlp.platform.agents.cli:main"
vietnlp-migrate = "vietnlp.platform.db.migrate:main"
```

(The `vietnlp-migrate` script target is added now so Task 3 does not need to touch this file again; `vietnlp.platform.db.migrate:main` does not exist until Task 2/3, which is fine — `pip install -e .` only records the entry point, it does not import it.)

- [ ] **Step 2: Update the Dockerfile's dependency pre-install layer**

`deploy/Dockerfile` currently has:

```dockerfile
COPY pyproject.toml /app/
RUN pip install --no-cache-dir httpx>=0.27 pytest>=8.0
```

Replace that `RUN` line with the full set, dependencies and dev extras together, so the layer cache holds until `pyproject.toml` next changes:

```dockerfile
COPY pyproject.toml /app/
RUN pip install --no-cache-dir \
    httpx>=0.27 pytest>=8.0 respx>=0.21 \
    "psycopg[binary]>=3.1" pyarrow>=15 minio>=7.2 prefect>=3.0 pandera>=0.20 pandas>=2.0
```

Leave the rest of the Dockerfile untouched.

- [ ] **Step 3: Build and smoke-test the image locally on the deploy target**

There is no local Python 3.11 on this development machine, so the check runs on `_59` where Docker actually lives. Sync and build without starting services:

```bash
tar czf - --exclude '.git' --exclude '__pycache__' --exclude '.env' --exclude 'deepseek.key' --exclude 'data' \
    src pyproject.toml tests deploy CLAUDE.md | ssh _59 'tar xzf - -C vietnlp'
ssh _59 'cd vietnlp/deploy && docker compose build agents'
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint python agents -c \
    "import psycopg, pyarrow, minio, prefect, pandera, pandas, respx; print(\"ok\")"'
```

Expected: the build succeeds and the last command prints `ok`. If `respx` or any of the five fails to import, the version pin is wrong or the pip install step was mistyped — fix before continuing, do not skip this check.

- [ ] **Step 4: Run the existing offline test suite to confirm nothing regressed**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests -q'
```

Expected: PASS, same 46 tests as before (this task adds no new test files).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml deploy/Dockerfile
git commit -m "build: add psycopg, pyarrow, minio, prefect, pandera and fix missing respx in the image"
```

---

### Task 2: Migration runner — file discovery and ordering (pure logic)

**Files:**
- Create: `src/vietnlp/platform/db/__init__.py`
- Create: `src/vietnlp/platform/db/migrate.py`
- Test: `tests/test_db_migrate.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `Migration` (dataclass: `version: str`, `name: str`, `path: Path`, `sql: str`), `list_migrations(migrations_dir: Path = DEFAULT_MIGRATIONS_DIR) -> list[Migration]`, `pending(applied: set[str], migrations: list[Migration]) -> list[Migration]`, `DEFAULT_MIGRATIONS_DIR: Path`. Task 3 adds `apply()`, `status()`, `main()` to this same file and consumes these four names.

This task is deliberately split from Task 3: the ordering logic below never touches a database and is fully unit-testable offline. Task 3 adds the part that actually needs Postgres.

- [ ] **Step 1: Write the failing test**

Create `tests/test_db_migrate.py`:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_db_migrate.py -v'
```

Expected: FAIL / ERROR — `ModuleNotFoundError: No module named 'vietnlp.platform.db'`.

(Sync the new test file to the server first with the same `tar czf - ... | ssh _59 'tar xzf - -C vietnlp'` command from Task 1 Step 3 — every subsequent task assumes this sync-before-test step and will not repeat it verbatim.)

- [ ] **Step 3: Write the minimal implementation**

Create `src/vietnlp/platform/db/__init__.py` (empty file).

Create `src/vietnlp/platform/db/migrate.py`:

```python
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
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_db_migrate.py -v'
```

Expected: PASS, 5 tests.

- [ ] **Step 5: Commit**

```bash
git add src/vietnlp/platform/db/__init__.py src/vietnlp/platform/db/migrate.py tests/test_db_migrate.py
git commit -m "feat: migration file discovery and ordering (pure logic, no database yet)"
```

---

### Task 3: Core schema migration + apply/status/CLI

**Files:**
- Create: `src/vietnlp/platform/db/migrations/0001_core_schema.sql`
- Modify: `src/vietnlp/platform/db/migrate.py`
- Modify: `tests/test_db_migrate.py`

**Interfaces:**
- Consumes: `Migration`, `list_migrations`, `pending`, `DEFAULT_MIGRATIONS_DIR` from Task 2.
- Produces: `DEFAULT_DATABASE_URL: str` (already defined in Task 2), `apply(database_url: str, migrations_dir: Path = DEFAULT_MIGRATIONS_DIR) -> list[str]` (returns versions applied, in order), `status(database_url: str, migrations_dir: Path = DEFAULT_MIGRATIONS_DIR) -> list[tuple[str, str, bool]]` (version, name, is_applied), `main(argv=None) -> int` (CLI: `up` | `status`). Task 6's flow does not use this table directly in P0 (the stub flow does not write to Postgres), but P1's real curation flow will call `apply()` once at startup — this is the interface it will import.

- [ ] **Step 1: Write the schema migration**

Create `src/vietnlp/platform/db/migrations/0001_core_schema.sql`. This is the serving schema from spec §4.3, verbatim in structure. Two deliberate omissions, both noted inline: no `vector` index yet (an `ivfflat` index built against zero rows is low quality and would need rebuilding once embeddings exist — that is a P4/P5 concern), and `id` columns use `BIGSERIAL` rather than UUID (simpler for a ~100K-row pilot, and nothing in the spec requires globally-unique IDs across databases).

```sql
-- 0001_core_schema.sql
-- Serving schema per spec S4.3. Postgres is a projection of Gold (CLAUDE.md
-- rule 3): this migration only ever adds structure, never patches data.
--
-- Deferred by design: no ivfflat index on embeddings.vector yet (building one
-- against zero rows produces a low-quality index that would need rebuilding
-- anyway once P4/P5 populate it -- add it then, against real data).

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS sources (
    id            BIGSERIAL PRIMARY KEY,
    name          TEXT NOT NULL UNIQUE,
    tier          TEXT NOT NULL CHECK (tier IN ('news_gov_wiki', 'forum_qa_blog', 'social', 'public_corpus')),
    base_url      TEXT,
    license       TEXT,
    robots_policy TEXT,
    enabled       BOOLEAN NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS documents (
    id            BIGSERIAL PRIMARY KEY,
    content_hash  TEXT NOT NULL UNIQUE,
    source_id     BIGINT NOT NULL REFERENCES sources(id),
    url           TEXT,
    fetched_at    TIMESTAMPTZ NOT NULL,
    lang          TEXT,
    register      TEXT,
    quality_score REAL,
    bronze_uri    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS documents_source_id ON documents(source_id);

CREATE TABLE IF NOT EXISTS sentences (
    id          BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    idx         INT NOT NULL,
    text        TEXT NOT NULL,
    char_start  INT NOT NULL,
    char_end    INT NOT NULL,
    UNIQUE (document_id, idx)
);
CREATE INDEX IF NOT EXISTS sentences_document_id ON sentences(document_id);

CREATE TABLE IF NOT EXISTS annotation_runs (
    id             BIGSERIAL PRIMARY KEY,
    stage          TEXT NOT NULL,
    engine         TEXT NOT NULL,
    engine_version TEXT,
    prompt_version TEXT,
    started_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at    TIMESTAMPTZ,
    status         TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'succeeded', 'failed'))
);

CREATE TABLE IF NOT EXISTS tokens (
    id        BIGSERIAL PRIMARY KEY,
    sentence_id BIGINT NOT NULL REFERENCES sentences(id) ON DELETE CASCADE,
    idx       INT NOT NULL,
    form      TEXT NOT NULL,
    syllables TEXT[] NOT NULL,
    lemma     TEXT,
    upos      TEXT,
    xpos      TEXT,
    feats     JSONB,
    head      INT,
    deprel    TEXT,
    misc      JSONB,
    run_id    BIGINT NOT NULL REFERENCES annotation_runs(id),
    UNIQUE (sentence_id, idx, run_id)
);
CREATE INDEX IF NOT EXISTS tokens_sentence_id ON tokens(sentence_id);

CREATE TABLE IF NOT EXISTS entities (
    id             BIGSERIAL PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    ontology_class TEXT,
    wikidata_qid   TEXT,
    posterior      REAL
);

CREATE TABLE IF NOT EXISTS mentions (
    id          BIGSERIAL PRIMARY KEY,
    sentence_id BIGINT NOT NULL REFERENCES sentences(id) ON DELETE CASCADE,
    token_start INT NOT NULL,
    token_end   INT NOT NULL,
    entity_id   BIGINT REFERENCES entities(id),
    confidence  REAL
);
CREATE INDEX IF NOT EXISTS mentions_sentence_id ON mentions(sentence_id);
CREATE INDEX IF NOT EXISTS mentions_entity_id ON mentions(entity_id);

CREATE TABLE IF NOT EXISTS logical_forms (
    id            BIGSERIAL PRIMARY KEY,
    sentence_id   BIGINT NOT NULL REFERENCES sentences(id) ON DELETE CASCADE,
    form_sexp     TEXT NOT NULL,
    predicates    TEXT[] NOT NULL DEFAULT '{}',
    type_checked  BOOLEAN NOT NULL DEFAULT false,
    run_id        BIGINT NOT NULL REFERENCES annotation_runs(id)
);
CREATE INDEX IF NOT EXISTS logical_forms_sentence_id ON logical_forms(sentence_id);

CREATE TABLE IF NOT EXISTS embeddings (
    sentence_id BIGINT NOT NULL REFERENCES sentences(id) ON DELETE CASCADE,
    model       TEXT NOT NULL,
    vector      vector(768) NOT NULL,
    PRIMARY KEY (sentence_id, model)
);

CREATE TABLE IF NOT EXISTS dead_letters (
    id           BIGSERIAL PRIMARY KEY,
    stage        TEXT NOT NULL,
    content_hash TEXT,
    error        TEXT NOT NULL,
    payload_uri  TEXT,
    occurred_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS dead_letters_stage ON dead_letters(stage);
```

- [ ] **Step 2: Write the failing integration test**

Append to `tests/test_db_migrate.py`:

```python
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
    scoped_url = f"{url}?options={quote(f'-c search_path={schema}')}"
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
```

- [ ] **Step 3: Run the test to verify it fails**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_db_migrate.py -v'
```

Expected: FAIL at collection — `ImportError: cannot import name 'apply' from 'vietnlp.platform.db.migrate'`. This happens regardless of whether Postgres is reachable, because the import itself fails before any fixture runs.

- [ ] **Step 4: Implement `apply`, `status` and `main`**

Append to `src/vietnlp/platform/db/migrate.py` (add `import os` and `import psycopg` to the top-of-file imports alongside the existing `re`/`dataclass`/`Path` imports):

```python
import os

import psycopg


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
```

- [ ] **Step 5: Run the test to verify it passes (or correctly self-skips)**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_db_migrate.py -v'
```

Expected under `--no-deps` (Postgres not running, `postgres` hostname does not resolve): the 5 pure-logic tests PASS, the 3 live-DB tests SKIP with reason `no reachable Postgres`. This is correct — Task 8 proves they pass for real once the stack is up.

- [ ] **Step 6: Commit**

```bash
git add src/vietnlp/platform/db/migrations/0001_core_schema.sql src/vietnlp/platform/db/migrate.py tests/test_db_migrate.py
git commit -m "feat: apply/status/CLI for the core Postgres schema (spec S4.3)"
```

---

### Task 4: Content-addressed Bronze storage on MinIO

**Files:**
- Create: `src/vietnlp/platform/storage/__init__.py`
- Create: `src/vietnlp/platform/storage/bronze.py`
- Test: `tests/test_storage_bronze.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `content_hash(payload: bytes) -> str`, `bronze_key(source_id: str, fetched_at: datetime, hash_hex: str) -> str`, `BronzeError(RuntimeError)`, `BronzeStore` (dataclass: `endpoint, access_key, secret_key, bucket="vietnlp-bronze", secure=False`) with `.from_env() -> BronzeStore`, `.ensure_bucket() -> None`, `.put_record(record: dict) -> str` (returns the object key), `.get_record(key: str) -> dict`. P1's acquisition flow is the eventual caller of `put_record`/`get_record`; this task's job is only to make that primitive correct and tested.

`record` for `put_record` must carry `raw_payload: bytes`, `source_id: str`, `fetched_at: datetime`, and the rest of spec §4.1's fields (`url`, `http_status`, `robots_decision`, `content_type`, `license`). `content_hash` is computed here, never taken from the caller — that is what makes the store honest about Bronze immutability (CLAUDE.md rule 1).

- [ ] **Step 1: Write the failing test (pure helpers + missing-secret guard)**

Create `tests/test_storage_bronze.py`:

```python
"""Content-addressed Bronze storage. Pure helpers are tested offline; the
put/get round trip against a live MinIO is a self-skipping integration test
(see `live_store` below), mirroring the pattern in test_db_migrate.py."""

import hashlib
import os
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
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_storage_bronze.py -v'
```

Expected: FAIL — `ModuleNotFoundError: No module named 'vietnlp.platform.storage'`.

- [ ] **Step 3: Write the implementation**

Create `src/vietnlp/platform/storage/__init__.py` (empty file).

Create `src/vietnlp/platform/storage/bronze.py`:

```python
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
        secure = endpoint.startswith("https://")
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
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_storage_bronze.py -v'
```

Expected: PASS, 5 tests.

- [ ] **Step 5: Add the self-skipping live round-trip test**

Append to `tests/test_storage_bronze.py`:

```python
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
```

- [ ] **Step 6: Run the full file again**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_storage_bronze.py -v'
```

Expected under `--no-deps`: the 5 pure tests PASS, the 2 live tests SKIP.

- [ ] **Step 7: Commit**

```bash
git add src/vietnlp/platform/storage/__init__.py src/vietnlp/platform/storage/bronze.py tests/test_storage_bronze.py
git commit -m "feat: content-addressed Bronze storage on MinIO"
```

---

### Task 5: Fixture corpus — generator, schema, contract test

**Files:**
- Create: `src/vietnlp/acquisition/fixture_schema.py`
- Create: `tests/fixtures/generate_fixture_corpus.py`
- Create: `tests/fixtures/corpus/fixture_corpus.jsonl` (generated output, committed)
- Test: `tests/test_fixture_corpus.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `FIXTURE_SCHEMA` (pandera `DataFrameSchema`), `validate_fixture_record(record: dict) -> dict` (raises `pandera.errors.SchemaError`). `tests/fixtures/corpus/fixture_corpus.jsonl`: 100 JSON-lines records, each with keys `content_hash, source_id, url, fetched_at, http_status, robots_decision, content_type, text, license, register`. Task 6's flow consumes both this file's shape and `validate_fixture_record`.

`FIXTURE_SCHEMA` is explicitly **not** the production Bronze contract. Spec §4.1 stores `raw_payload: bytes`; the fixture is plain-text JSONL and cannot hold raw bytes cleanly, so it substitutes a `text: str` field. `BronzeStore` (Task 4) already implements the real byte-based contract — this schema exists only to validate the committed fixture and the stub flow's input, both of which are deliberately text-shaped.

- [ ] **Step 1: Write the failing contract test**

Create `tests/test_fixture_corpus.py`:

```python
"""The fixture corpus is the offline substrate for every later test (CLAUDE.md
Working Agreements: "A committed ~100-document fixture corpus keeps the full
pipeline testable without network or API spend"). These tests are its contract.
"""
import json
import unicodedata
from pathlib import Path

from vietnlp.acquisition.fixture_schema import validate_fixture_record

CORPUS_PATH = Path(__file__).parent / "fixtures" / "corpus" / "fixture_corpus.jsonl"


def _load():
    with CORPUS_PATH.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def test_corpus_file_exists():
    assert CORPUS_PATH.exists(), "run tests/fixtures/generate_fixture_corpus.py"


def test_corpus_has_exactly_100_documents():
    assert len(_load()) == 100


def test_every_document_is_fixture_schema_valid():
    for record in _load():
        validate_fixture_record(record)  # raises SchemaError on the first invalid row


def test_content_hashes_are_unique():
    hashes = [r["content_hash"] for r in _load()]
    assert len(hashes) == len(set(hashes))


def test_registers_are_balanced_across_four_categories():
    """CLAUDE.md flags informal/teencode/khong_dau as the registers the corpus
    is otherwise short of; the fixture exercises all four, evenly, so later
    register-balance tests (curation, P1) have a known-good baseline."""
    records = _load()
    counts: dict[str, int] = {}
    for r in records:
        counts[r["register"]] = counts.get(r["register"], 0) + 1
    assert set(counts) == {"formal", "informal", "teencode", "khong_dau"}
    assert all(count == 25 for count in counts.values()), counts


def test_text_is_nfc_normalized():
    for r in _load():
        assert r["text"] == unicodedata.normalize("NFC", r["text"])
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_fixture_corpus.py -v'
```

Expected: FAIL — `ModuleNotFoundError: No module named 'vietnlp.acquisition.fixture_schema'` (and the corpus file does not exist yet either).

- [ ] **Step 3: Write the fixture schema**

Create `src/vietnlp/acquisition/fixture_schema.py`:

```python
"""Pandera contract for the committed synthetic fixture corpus.

This is NOT the production Bronze contract (spec S4.1 uses raw_payload:
bytes; see platform/storage/bronze.py for that). The fixture is plain-text
JSONL, so it substitutes a decoded `text` field -- JSONL cannot hold raw
bytes cleanly. The content_hash check keeps the derived-identity invariant
honest even in this substitute shape: content_hash must always be
sha256(text.encode()), never a value trusted from the input.
"""

from __future__ import annotations

import hashlib

import pandas as pd
import pandera as pa

_REGISTER_VALUES = {"formal", "informal", "teencode", "khong_dau", "mixed"}
_ROBOTS_VALUES = {"allowed", "disallowed", "no_robots"}

FIXTURE_SCHEMA = pa.DataFrameSchema(
    {
        "content_hash": pa.Column(str, pa.Check.str_matches(r"^[0-9a-f]{64}$")),
        "source_id": pa.Column(str, pa.Check.str_length(min_value=1)),
        "url": pa.Column(str, pa.Check.str_startswith("https://")),
        "fetched_at": pa.Column(str, pa.Check.str_length(min_value=1)),
        "http_status": pa.Column(int, pa.Check.in_range(100, 599)),
        "robots_decision": pa.Column(str, pa.Check.isin(_ROBOTS_VALUES)),
        "content_type": pa.Column(str, pa.Check.str_length(min_value=1)),
        "text": pa.Column(str, pa.Check.str_length(min_value=1)),
        "license": pa.Column(str, pa.Check.str_length(min_value=1)),
        "register": pa.Column(str, pa.Check.isin(_REGISTER_VALUES)),
    },
    strict=False,
    checks=pa.Check(
        lambda df: df["content_hash"] == df["text"].apply(
            lambda t: hashlib.sha256(t.encode("utf-8")).hexdigest()
        ),
        error="content_hash must equal sha256(text) -- identity is derived, never trusted from input",
    ),
)


def validate_fixture_record(record: dict) -> dict:
    """Validate one fixture-shaped record. Raises pandera.errors.SchemaError."""
    df = pd.DataFrame([record])
    validated = FIXTURE_SCHEMA.validate(df, lazy=False)
    return validated.iloc[0].to_dict()
```

- [ ] **Step 4: Write the corpus generator**

Create `tests/fixtures/generate_fixture_corpus.py`:

```python
"""Generates the committed synthetic fixture corpus.

Not scraped, not real user content -- every sentence here is written for this
repository, specifically so the pipeline has ~100 documents to test against
without network access or API spend (CLAUDE.md Working Agreements). Output is
deterministic: re-running this script reproduces byte-identical JSONL.

Run: python tests/fixtures/generate_fixture_corpus.py
"""
from __future__ import annotations

import hashlib
import itertools
import json
from datetime import datetime, timezone
from pathlib import Path

FETCHED_AT = datetime(2026, 8, 23, 0, 0, tzinfo=timezone.utc)

FORMAL = [
    "Bộ Giáo dục và Đào tạo công bố lịch thi tốt nghiệp trung học phổ thông năm nay.",
    "Ngân hàng Nhà nước giữ nguyên lãi suất điều hành trong quý này.",
    "Đội tuyển bóng đá quốc gia giành chiến thắng trong trận đấu giao hữu tối qua.",
    "Thành phố Hà Nội triển khai thêm tuyến xe buýt điện phục vụ người dân.",
    "Các nhà khoa học công bố nghiên cứu mới về biến đổi khí hậu tại đồng bằng sông Cửu Long.",
    "Chính phủ ban hành nghị định hướng dẫn thi hành luật đất đai sửa đổi.",
    "Tập đoàn công nghệ trong nước ra mắt sản phẩm phần mềm dịch thuật tiếng Việt.",
    "Bệnh viện trung ương tổ chức chương trình khám sức khỏe miễn phí cho người cao tuổi.",
    "Trường đại học quốc gia công bố kết quả tuyển sinh đợt hai.",
    "Sở Giao thông Vận tải thông báo kế hoạch sửa chữa cầu đường trong tháng tới.",
]

INFORMAL = [
    "Hôm nay trời đẹp quá, đi cà phê không?",
    "Tao vừa ăn phở xong, ngon dã man luôn.",
    "Mai đi học sớm nha, đừng trễ nữa đó.",
    "Bộ phim tối qua coi hay ghê, mày xem chưa?",
    "Cuối tuần này rảnh không, đi chơi Đà Lạt đi.",
    "Nay mưa to quá trời, chắc kẹt xe dữ lắm.",
    "Đói bụng ghê, kiếm gì ăn thôi mọi người ơi.",
    "Con mèo nhà tao nghịch banh quá trời luôn.",
    "Bài tập cô giao khó ghê, ai làm xong chưa vậy.",
    "Chiều nay đá bóng không, thiếu người quá.",
]

TEENCODE = [
    "Hnay ranh ko, di choi di :))",
    "T thay bit r, hay v.",
    "Mai hoc som nha, dg quen do.",
    "Phim nay hay v, coi chua a.",
    "Doi bung wa, an gi bh.",
    "Ny t bao dang gian, hix.",
    "Trg hom nay dong ng kinh khung.",
    "Bai kt kho v troi, lam sao lam het.",
    "Cuoi tuan ranh k, di chill k.",
    "Mua to v troi oi, ket xe cmnr.",
]

KHONG_DAU = [
    "Bo Giao duc va Dao tao cong bo lich thi tot nghiep trung hoc pho thong nam nay.",
    "Ngan hang Nha nuoc giu nguyen lai suat dieu hanh trong quy nay.",
    "Hom nay troi dep qua, di ca phe khong?",
    "Tao vua an pho xong, ngon da man luon.",
    "Mai di hoc som nha, dung tre nua do.",
    "Doi tuyen bong da quoc gia gianh chien thang trong tran dau giao huu toi qua.",
    "Cuoi tuan nay ranh khong, di choi Da Lat di.",
    "Thanh pho Ha Noi trien khai them tuyen xe buyt dien phuc vu nguoi dan.",
    "Nay mua to qua troi, chac ket xe du lam.",
    "Truong dai hoc quoc gia cong bo ket qua tuyen sinh dot hai.",
]

_REGISTER_POOLS = {
    "formal": FORMAL, "informal": INFORMAL, "teencode": TEENCODE, "khong_dau": KHONG_DAU,
}
_SOURCE_ID = {
    "formal": "fixture-formal", "informal": "fixture-informal",
    "teencode": "fixture-teencode", "khong_dau": "fixture-khongdau",
}


def _documents_for(register: str, pool: list[str]) -> list[dict]:
    docs: list[tuple[int, str]] = [(i, sentence) for i, sentence in enumerate(pool)]
    pairs = itertools.islice(itertools.combinations(range(len(pool)), 2), 15)
    docs += [(10 + i, f"{pool[a]} {pool[b]}") for i, (a, b) in enumerate(pairs)]

    records = []
    for idx, text in docs:
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        records.append({
            "content_hash": h,
            "source_id": _SOURCE_ID[register],
            "url": f"https://fixture.local/{_SOURCE_ID[register]}/{idx:03d}",
            "fetched_at": FETCHED_AT.isoformat(),
            "http_status": 200,
            "robots_decision": "allowed",
            "content_type": "text/plain; charset=utf-8",
            "text": text,
            "license": "synthetic-fixture",
            "register": register,
        })
    return records


def build_corpus() -> list[dict]:
    records = []
    for register, pool in _REGISTER_POOLS.items():
        records.extend(_documents_for(register, pool))
    return records


def main() -> None:
    records = build_corpus()
    assert len(records) == 100, f"expected 100 fixture documents, got {len(records)}"
    out = Path(__file__).parent / "corpus" / "fixture_corpus.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"wrote {len(records)} records to {out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run the generator**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint python agents /app/tests/fixtures/generate_fixture_corpus.py'
```

Expected: `wrote 100 records to /app/tests/fixtures/corpus/fixture_corpus.jsonl`. Copy the generated file back so it is committed from the working tree, not left only inside the container:

```bash
ssh _59 'cat vietnlp/tests/fixtures/corpus/fixture_corpus.jsonl' > tests/fixtures/corpus/fixture_corpus.jsonl
```

- [ ] **Step 6: Run the contract test to verify it passes**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_fixture_corpus.py -v'
```

Expected: PASS, 5 tests.

- [ ] **Step 7: Commit**

```bash
git add src/vietnlp/acquisition/fixture_schema.py tests/fixtures/generate_fixture_corpus.py tests/fixtures/corpus/fixture_corpus.jsonl tests/test_fixture_corpus.py
git commit -m "test: committed 100-document synthetic fixture corpus with its schema contract"
```

---

### Task 6: Prefect bootstrap flow (retry + dead-letter wiring)

**Files:**
- Create: `src/vietnlp/platform/flows/__init__.py`
- Create: `src/vietnlp/platform/flows/bootstrap_flow.py`
- Test: `tests/test_flows_bootstrap.py`

**Interfaces:**
- Consumes: `validate_fixture_record` from Task 5 (`vietnlp.acquisition.fixture_schema`); `tests/fixtures/corpus/fixture_corpus.jsonl` from Task 5.
- Produces: `bronze_to_silver_stub(records: Iterable[dict], dead_letter_sink: Callable[[dict, str], None] | None = None) -> dict` returning `{"processed": int, "dead_lettered": int}`. This is a **stub** — P1's real curation flow replaces `_stub_silver_projection` with actual dedup/language-ID/quality-scoring logic and keeps the same validate-then-dead-letter shape and the same `dead_letter_sink` injection point (which P1 wires to a real `dead_letters` table writer using Task 3's schema).

Runs Prefect in its default **ephemeral local mode** — no separate Prefect server container. The spec's reason for choosing Prefect (§3.1: "expresses retry/backoff/caching policy as decorators on ordinary functions") does not require a running server for P0; a server/UI is a P1+ decision once flows exist that need scheduling. Tests use Prefect's own `prefect_test_harness`, which is the documented way to test flows offline — no network, no server process.

- [ ] **Step 1: Write the failing test**

Create `tests/test_flows_bootstrap.py`:

```python
"""Uses Prefect's official offline test harness -- no server, no network,
consistent with the offline pytest requirement in CLAUDE.md."""
import json
from pathlib import Path

import pytest
from prefect.testing.utilities import prefect_test_harness

from vietnlp.platform.flows.bootstrap_flow import bronze_to_silver_stub

CORPUS_PATH = Path(__file__).parent / "fixtures" / "corpus" / "fixture_corpus.jsonl"


@pytest.fixture(autouse=True, scope="module")
def _prefect_test_mode():
    with prefect_test_harness():
        yield


def _load_fixture(n: int | None = None) -> list[dict]:
    with CORPUS_PATH.open(encoding="utf-8") as f:
        records = [json.loads(line) for line in f]
    return records[:n] if n else records


def test_processes_every_valid_fixture_record():
    result = bronze_to_silver_stub(_load_fixture())
    assert result == {"processed": 100, "dead_lettered": 0}


def test_invalid_record_is_dead_lettered_not_dropped():
    """CLAUDE.md rule 4: no silent drops."""
    good = _load_fixture(3)
    bad = dict(good[0])
    bad["content_hash"] = "not-a-real-hash"  # breaks the derived-hash check

    caught = []
    result = bronze_to_silver_stub(good + [bad], dead_letter_sink=caught.append)

    assert result == {"processed": 3, "dead_lettered": 1}
    assert len(caught) == 1
    assert caught[0][0] == bad
    assert "content_hash" in caught[0][1]


def test_without_a_sink_the_record_is_still_counted_not_silently_lost():
    bad = dict(_load_fixture(1)[0])
    bad["url"] = "ftp://not-https"  # fails the fixture schema's url check

    result = bronze_to_silver_stub([bad])
    assert result == {"processed": 0, "dead_lettered": 1}
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_flows_bootstrap.py -v'
```

Expected: FAIL — `ModuleNotFoundError: No module named 'vietnlp.platform.flows'`.

- [ ] **Step 3: Write the implementation**

Create `src/vietnlp/platform/flows/__init__.py` (empty file).

Create `src/vietnlp/platform/flows/bootstrap_flow.py`:

```python
"""P0's only flow: proves the orchestration wiring end-to-end with a stub.

Real Bronze-to-Silver logic belongs to P1 (curation/). This flow exists to
(a) demonstrate retry/backoff as task decorators, the reason Prefect was
chosen over Airflow (spec S3.1), and (b) prove the dead-letter path works
before anything depends on it -- CLAUDE.md rule 4: no silent drops, ever.
"""

from __future__ import annotations

from typing import Callable, Iterable

from pandera.errors import SchemaError
from prefect import flow, task

from vietnlp.acquisition.fixture_schema import validate_fixture_record

DeadLetterSink = Callable[[dict, str], None]


@task
def _validate(record: dict) -> dict:
    """Deterministic; a schema failure is a data problem, not a transient
    one, so this task does not retry."""
    return validate_fixture_record(record)


@task(retries=2, retry_delay_seconds=1)
def _stub_silver_projection(record: dict) -> dict:
    """Placeholder for the real curation stage (P1). The retry policy models
    the transient I/O failures a real projection step would actually see."""
    return {"content_hash": record["content_hash"], "silver_stub": True}


@flow(name="bronze-to-silver-stub")
def bronze_to_silver_stub(
    records: Iterable[dict], dead_letter_sink: DeadLetterSink | None = None
) -> dict:
    processed = 0
    dead_lettered = 0
    for record in records:
        try:
            validated = _validate(record)
            _stub_silver_projection(validated)
            processed += 1
        except SchemaError as exc:
            dead_lettered += 1
            if dead_letter_sink is not None:
                dead_letter_sink(record, str(exc))
    return {"processed": processed, "dead_lettered": dead_lettered}
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_flows_bootstrap.py -v'
```

Expected: PASS, 3 tests. (`prefect_test_harness` needs no network and no live Postgres/MinIO, so these pass under `--no-deps` too — this is the one integration-shaped test in the plan that is *not* self-skipping, because Prefect's ephemeral mode makes it genuinely offline.)

- [ ] **Step 5: Commit**

```bash
git add src/vietnlp/platform/flows/__init__.py src/vietnlp/platform/flows/bootstrap_flow.py tests/test_flows_bootstrap.py
git commit -m "feat: Prefect bootstrap flow proving retry and dead-letter wiring end-to-end"
```

---

### Task 7: Fuseki dataset provisioning helper

**Files:**
- Create: `src/vietnlp/platform/graph/__init__.py`
- Create: `src/vietnlp/platform/graph/fuseki_admin.py`
- Test: `tests/test_fuseki_admin.py`
- Modify: `deploy/README.md`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `FusekiError(RuntimeError)`, `dataset_exists(base_url: str, name: str, *, auth: tuple[str, str] | None = None) -> bool`, `create_dataset(base_url: str, name: str, *, auth: tuple[str, str] | None = None) -> None` (idempotent). P3's ontology work is the eventual caller, once the `graph` compose profile is actually turned on.

Fuseki sits behind the `graph` compose profile and is not started by default (spec §10: not needed until P3). This task adds a **tested primitive**, entirely via `respx`-mocked HTTP — no live Fuseki required, none started in this plan.

- [ ] **Step 1: Write the failing test**

Create `tests/test_fuseki_admin.py`:

```python
"""Fuseki's admin HTTP API, entirely offline via respx -- no live Fuseki
required. The `graph` compose profile stays off until P3 needs it (spec S10);
this only makes sure the primitive P3 will call is already correct."""
import httpx
import pytest
import respx

from vietnlp.platform.graph.fuseki_admin import FusekiError, create_dataset, dataset_exists

BASE = "http://fuseki.test:3030"


@respx.mock
def test_dataset_exists_true_on_200():
    respx.get(f"{BASE}/$/datasets/vietnlp").mock(return_value=httpx.Response(200, json={}))
    assert dataset_exists(BASE, "vietnlp") is True


@respx.mock
def test_dataset_exists_false_on_404():
    respx.get(f"{BASE}/$/datasets/vietnlp").mock(return_value=httpx.Response(404))
    assert dataset_exists(BASE, "vietnlp") is False


@respx.mock
def test_dataset_exists_raises_on_unexpected_status():
    respx.get(f"{BASE}/$/datasets/vietnlp").mock(return_value=httpx.Response(500))
    with pytest.raises(FusekiError, match="unexpected status"):
        dataset_exists(BASE, "vietnlp")


@respx.mock
def test_create_dataset_posts_tdb2_when_absent():
    respx.get(f"{BASE}/$/datasets/vietnlp").mock(return_value=httpx.Response(404))
    create = respx.post(f"{BASE}/$/datasets").mock(return_value=httpx.Response(200))
    create_dataset(BASE, "vietnlp")
    assert create.called
    sent = create.calls.last.request.content.decode()
    assert "dbName=vietnlp" in sent and "dbType=tdb2" in sent


@respx.mock
def test_create_dataset_is_idempotent_when_already_present():
    respx.get(f"{BASE}/$/datasets/vietnlp").mock(return_value=httpx.Response(200, json={}))
    create = respx.post(f"{BASE}/$/datasets").mock(return_value=httpx.Response(200))
    create_dataset(BASE, "vietnlp")
    assert not create.called, "must not re-create an existing dataset"
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_fuseki_admin.py -v'
```

Expected: FAIL — `ModuleNotFoundError: No module named 'vietnlp.platform.graph'`.

- [ ] **Step 3: Write the implementation**

Create `src/vietnlp/platform/graph/__init__.py` (empty file).

Create `src/vietnlp/platform/graph/fuseki_admin.py`:

```python
"""Fuseki dataset provisioning, via its HTTP admin API.

Not exercised against a live server in P0: Fuseki sits behind the `graph`
compose profile and is not needed until P3 (spec S10). This module exists
now so P3 has a tested primitive to call rather than starting from a shell
script written under deadline.
"""

from __future__ import annotations

import httpx


class FusekiError(RuntimeError):
    pass


def dataset_exists(base_url: str, name: str, *, auth: tuple[str, str] | None = None) -> bool:
    resp = httpx.get(f"{base_url}/$/datasets/{name}", auth=auth, timeout=10.0)
    if resp.status_code == 200:
        return True
    if resp.status_code == 404:
        return False
    raise FusekiError(f"unexpected status checking dataset {name!r}: {resp.status_code}")


def create_dataset(base_url: str, name: str, *, auth: tuple[str, str] | None = None) -> None:
    """Idempotent: a dataset that already exists is left untouched."""
    if dataset_exists(base_url, name, auth=auth):
        return
    resp = httpx.post(
        f"{base_url}/$/datasets", data={"dbName": name, "dbType": "tdb2"}, auth=auth, timeout=10.0,
    )
    if resp.status_code not in (200, 201):
        raise FusekiError(f"failed to create dataset {name!r}: {resp.status_code} {resp.text[:300]}")
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_fuseki_admin.py -v'
```

Expected: PASS, 5 tests.

- [ ] **Step 5: Document the manual P3 activation step**

Append to `deploy/README.md`, after the existing "Operating" section:

```markdown
## Fuseki (P3, not started by default)

Fuseki is behind the `graph` compose profile and is not needed until ontology
work (P3) begins. To turn it on:

\`\`\`
docker compose --profile graph up -d fuseki
docker compose run --rm --no-deps --entrypoint python agents -c "
from vietnlp.platform.graph.fuseki_admin import create_dataset
import os
create_dataset('http://fuseki:3030', 'vietnlp', auth=('admin', os.environ['FUSEKI_ADMIN_PASSWORD']))
"
\`\`\`

`create_dataset` is idempotent -- safe to re-run.
```

- [ ] **Step 6: Commit**

```bash
git add src/vietnlp/platform/graph/__init__.py src/vietnlp/platform/graph/fuseki_admin.py tests/test_fuseki_admin.py deploy/README.md
git commit -m "feat: Fuseki dataset provisioning helper, tested offline for P3 to use"
```

---

### Task 8: Wiring, deploy, and P0 exit-criteria verification

**Files:**
- Modify: `Makefile`
- Modify: `deploy/docker-compose.yml`
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: everything from Tasks 1-7.
- Produces: a deployed, verified P0. No new Python interfaces.

This task proves the spec's literal P0 exit criterion (§10): *"`make up` brings the stack healthy; `make test` green; DeepSeek client with budget caps."* The DeepSeek client part is already done. This task adds `make up`, adds `make migrate`, and — critically — runs the full test suite **with** Postgres and MinIO actually running, so the tests that self-skip under `--no-deps` in Tasks 3 and 4 are proven to pass for real, not just to skip cleanly.

- [ ] **Step 1: Add `up`, `migrate` and `test-live` targets to the Makefile**

Add after the existing `deploy` target in `Makefile`:

```makefile
.PHONY: up
up: ## start the stack from the already-built image (no rebuild, no test run)
	ssh $(HOST) "cd $(REMOTE)/deploy && docker compose up -d --remove-orphans"

.PHONY: migrate
migrate: ## apply pending Postgres migrations on $(HOST)
	ssh $(HOST) "cd $(REMOTE)/deploy && docker compose run --rm --entrypoint python agents -m vietnlp.platform.db.migrate up"

.PHONY: test-live
test-live: ## full test suite against the live stack (exercises the integration tests that self-skip under `make test`)
	ssh $(HOST) "cd $(REMOTE)/deploy && docker compose run --rm --entrypoint pytest agents /app/tests -q"
```

Note `migrate` and `test-live` deliberately omit `--no-deps` — they need Postgres (and, for `test-live`, MinIO) actually running, which `docker compose run` starts automatically via the existing `depends_on: postgres: condition: service_healthy` on the `agents` service.

- [ ] **Step 2: Raise the `agents` service memory limit for Prefect's ephemeral mode**

Prefect's local ephemeral mode (Task 6) runs a temporary SQLite-backed API in-process, adding overhead beyond a typical DeepSeek dispatch call. The host has headroom for this (postgres 768M + minio 512M leaves several GB free out of the ~3-4 GB actually available), so raise the cap now rather than discovering an OOM mid-flow-test later.

In `deploy/docker-compose.yml`, change the `agents` service's memory limit:

```yaml
  agents:
    profiles: ["tools"]
    restart: "no"
    ...
    deploy:
      resources:
        limits:
          memory: 1G   # was 512M -- Prefect's ephemeral local API/SQLite needs headroom beyond DeepSeek dispatch
```

- [ ] **Step 3: Update CLAUDE.md's Commands section**

Replace the line `Populated during P1-P5: `make migrate`, `make bench`, `make export`.` with:

```markdown
make migrate       # apply pending Postgres migrations (server _59)
make test-live     # full test suite against the live stack (Postgres + MinIO)

Populated during P1-P5: `make bench`, `make export`.
```

- [ ] **Step 4: Update CLAUDE.md's Phase table**

Change the P0 row's status from `not started` to:

```markdown
| P0 | Platform bootstrap: Docker, compose stack, schemas, config, DeepSeek client | done — schema migrated, Bronze store and bootstrap flow tested live on `_59` |
```

- [ ] **Step 5: Sync, build, and run the offline gate**

```bash
tar czf - --exclude '.git' --exclude '__pycache__' --exclude '.env' --exclude 'deepseek.key' --exclude 'data' \
    src pyproject.toml tests deploy CLAUDE.md | ssh _59 'tar xzf - -C vietnlp'
ssh _59 'cd vietnlp/deploy && docker compose build agents'
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests -q'
```

Expected: PASS. Count should be the pre-existing 46 plus this plan's new tests: 5 (Task 2) + 3 (Task 3, offline subset) + 5 (Task 4, offline subset) + 5 (Task 5) + 3 (Task 6) + 5 (Task 7) = 26 new, with the 3 DB-live and 2 MinIO-live tests among them showing as SKIPPED, not FAILED.

- [ ] **Step 6: Start the stack and apply the migration**

```bash
ssh _59 'cd vietnlp/deploy && docker compose up -d --remove-orphans'
ssh _59 'cd vietnlp/deploy && docker compose ps'
make migrate HOST=_59 REMOTE=vietnlp
```

Expected: `docker compose ps` shows `postgres` and `minio` healthy; `make migrate` prints `applied: 0001`.

- [ ] **Step 7: Run the full suite against the live stack**

```bash
make test-live HOST=_59 REMOTE=vietnlp
```

Expected: PASS, and — this is the actual proof this task exists to produce — the 3 Postgres-live tests from Task 3 and the 2 MinIO-live tests from Task 4 now **execute and pass**, rather than skip. If any of them fail here while passing offline, the bug is in the live wiring (connection string, bucket permissions, network alias), not the logic — check `docker compose logs postgres minio` before changing test code.

- [ ] **Step 8: Regression-check the existing agents layer still works**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps agents routes'
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps agents agents'
```

Expected: both print their tables exactly as before Task 1's dependency additions — confirms the new dependencies did not shadow or break anything in `platform/agents/`.

- [ ] **Step 9: Commit the wiring changes**

```bash
git add Makefile deploy/docker-compose.yml CLAUDE.md
git commit -m "chore: wire make up/migrate/test-live, raise agents memory for Prefect, mark P0 done"
```

---

## Self-Review Notes

- **Spec coverage:** §4.3 schema — Task 3. MinIO/Bronze content-addressing — Task 4. Prefect flow with retry/backoff decorators — Task 6. Fixture corpus (§8 "committed ~100-document fixture corpus") — Task 5. Fuseki (§10, gated to P3) — Task 7, deliberately untested-live, consistent with the gate. DeepSeek client with budget ledger — already done pre-plan (`platform/agents/`), referenced not rebuilt. `make up`/`make test` exit criterion (§10) — Task 8. Docker prerequisite — resolved pre-plan (confirmed on `_59`). Config/secrets handling — already established (`deploy/.env` pattern), not re-litigated.
- **Placeholder scan:** no TBD/TODO/FIXME; every step carries runnable code or an exact command, not a description of one.
- **Type consistency:** `BronzeStore.put_record`/`get_record` use `raw_payload: bytes` consistently between Task 4's implementation and its tests. `bronze_to_silver_stub`'s `dead_letter_sink: Callable[[dict, str], None]` signature matches its call site in Task 6 and its test assertions (`caught[0]` is a `(dict, str)` tuple via `list.append`). `apply()`/`status()` signatures in Task 3 match every call site in Task 3's tests and Task 8's Makefile invocation.
- **Known forward risk, not this plan's to fix:** the spec's risk table already records that a full-corpus `semantic_parse` run in P4 would cost ~$465 against the $200 total budget cap. Nothing in P0 spends against that cap (no DeepSeek calls in this plan), so it is out of scope here — flagged again only so whoever picks up P1/P4 planning sees it twice.
