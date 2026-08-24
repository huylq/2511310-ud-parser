# P1a: Acquisition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the acquisition half of P1 — a source-vetting gate plus three
acquisition paths (public-corpus loader, web discovery+extraction, polite
crawler) that all converge on the existing `BronzeStore`, orchestrated by one
Prefect flow with a structurally-enforced per-source kill switch.

**Architecture:** `corpus-scout` vets a source into Postgres's existing
`sources` table; `acquisition_flow` dispatches to the loader matching that
source's `tier` (already-deployed values: `public_corpus`, `news_gov_wiki`,
`forum_qa_blog`); every loader writes through `BronzeStore.put_record`
(already built, untouched). Nothing in this plan writes to Postgres
`documents`/`sentences` — that is P1b's projector's job exclusively.

**Tech Stack:** Python 3.11, psycopg3 (source vetting), httpx (polite
crawler), the official `mcp` Python SDK (z.ai MCP tool calls over Streamable
HTTP), Prefect 3 (flow orchestration), pytest.

**Spec:** `docs/superpowers/specs/2026-08-24-p1-acquisition-curation-design.md`

## Global Constraints

- Python 3.11 only.
- CLAUDE.md rule 3: Postgres and Fuseki are projections, never hand-edited.
  No task in this plan writes to `documents`/`sentences` — only to `sources`
  (operational vetting metadata, not corpus content, so writing it directly
  does not violate the rule).
- CLAUDE.md rule 4: no silent drops. Every loader dead-letters a record it
  cannot process, with its exception, via the same `dead_letter_sink:
  Callable[[tuple[dict, str]], None]` shape Task 6 of the P0 plan already
  established and fixed (single-tuple argument, not two positional args).
- Acquisition-ethics guardrails (CLAUDE.md, binding): public content only;
  respect `robots.txt` and per-host rate limits; hash author identifiers at
  ingest, never persist raw handles; no profile-level harvesting; per-source
  kill switch, re-checked at the start of every task-level retry, not just
  once at flow start; P6 social acquisition stays off (the `social` tier
  value exists in the schema and is never dispatched by any loader in this
  plan).
- `content_hash` in Bronze is always derived, never caller-supplied
  (`BronzeStore.put_record` already enforces this — P0, unchanged here).
- Existing `platform/agents/` (DeepSeek client, budget ledger, cache,
  policy, registry) is untouched by this plan except for one narrow,
  spec-mandated rename (Task 1): the `khong_dau` register label becomes
  `non_diacritic` everywhere it appears, including in `platform/agents/
  registry.py`'s `_REGISTERS` set and the `register-classifier` agent's
  system prompt. This is a label rename only, not a logic change — P0's
  "don't modify agents/ logic" constraint is about behavior, and this task
  changes zero behavior, only a string constant three call sites use.
- Server `_59` is a shared 8-vCPU/15-GB host, ~3-4 GB actually free, ~12
  unrelated containers. Every new dependency gets weighed against this
  before being added. Ports 6040-6049, services bind 127.0.0.1 only.
  `rsync` is not installed; sync is tar-over-SSH via `deploy/deploy.sh`.
- The default test gate (`docker compose run --rm --no-deps --entrypoint
  pytest agents /app/tests -q`) must stay green without Postgres or MinIO
  running. Every task's automated tests are either pure-logic (no I/O) or
  fake their external dependency (BronzeStore, the MCP client, HTTP) —
  genuine end-to-end live verification happens once, holistically, in
  Task 10, mirroring how P0's Task 8 proved the whole stack for real.
- Budget caps are hard stops (CLAUDE.md rule 5): $5/flow, $20/day, $200/
  total. Nothing in this plan calls DeepSeek — that is entirely P1b's
  concern (curation). This plan's only new spend-adjacent surface is z.ai
  MCP calls, which are not DeepSeek and are not budget-ledger-tracked;
  Task 10 documents that as an explicit, accepted scope boundary, not an
  oversight.

---

### Task 1: Rename the `khong_dau` register label to `non_diacritic`

**Files:**
- Modify: `src/vietnlp/acquisition/fixture_schema.py:18`
- Modify: `tests/fixtures/generate_fixture_corpus.py:60,74,78`
- Modify: `tests/test_fixture_corpus.py:37-45`
- Modify: `src/vietnlp/platform/agents/registry.py:67,221`
- Modify: `tests/test_registry.py:44-46`
- Regenerate: `tests/fixtures/corpus/fixture_corpus.jsonl`

**Interfaces:**
- Consumes: nothing from later tasks.
- Produces: every register value in the codebase is now
  `formal | informal | teencode | non_diacritic | mixed` — no code anywhere
  after this task uses the string `khong_dau`. Later curation tasks (P1b)
  rely on this being the one true spelling.

This resolves a naming mismatch the P0 final whole-branch review flagged:
the fixture corpus used `khong_dau`, but spec §4.2 (and the DeepSeek
register-classifier's own prompt) already used `non_diacritic`. Left alone,
P1's real register classifier and the fixture's known-good baseline would
permanently disagree.

- [ ] **Step 1: Update the fixture schema's allowed register values**

In `src/vietnlp/acquisition/fixture_schema.py`, change line 18:

```python
_REGISTER_VALUES = {"formal", "informal", "teencode", "non_diacritic", "mixed"}
```

- [ ] **Step 2: Rename the generator's pool and source-id mapping**

In `tests/fixtures/generate_fixture_corpus.py`, rename the `KHONG_DAU` list
to `NON_DIACRITIC` (same content, just the name) and update both dict
literals that reference it:

```python
NON_DIACRITIC = [
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
    "formal": FORMAL, "informal": INFORMAL, "teencode": TEENCODE, "non_diacritic": NON_DIACRITIC,
}
_SOURCE_ID = {
    "formal": "fixture-formal", "informal": "fixture-informal",
    "teencode": "fixture-teencode", "non_diacritic": "fixture-nondiacritic",
}
```

The sentence text itself is unchanged — only the Python name, the dict key,
and the `source_id` value change (`fixture-khongdau` → `fixture-nondiacritic`,
matching the fused-word style of the other three `source_id`s).

- [ ] **Step 3: Update the contract test's expected register set**

In `tests/test_fixture_corpus.py`, update the docstring and assertion
(lines 37-45):

```python
def test_registers_are_balanced_across_four_categories():
    """CLAUDE.md flags informal/teencode/non_diacritic as the registers the
    corpus is otherwise short of; the fixture exercises all four, evenly, so
    later register-balance tests (curation, P1) have a known-good baseline."""
    records = _load()
    counts: dict[str, int] = {}
    for r in records:
        counts[r["register"]] = counts.get(r["register"], 0) + 1
    assert set(counts) == {"formal", "informal", "teencode", "non_diacritic"}
    assert all(count == 25 for count in counts.values()), counts
```

- [ ] **Step 4: Regenerate the committed fixture corpus**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint python agents /app/tests/fixtures/generate_fixture_corpus.py'
ssh _59 'cat vietnlp/tests/fixtures/corpus/fixture_corpus.jsonl' > tests/fixtures/corpus/fixture_corpus.jsonl
```

(Sync the modified generator to `_59` first — see `deploy/deploy.sh`'s
tar-over-SSH mechanism, same as every prior task's live-test step.)

- [ ] **Step 5: Rename the register label in the DeepSeek registry**

In `src/vietnlp/platform/agents/registry.py`, line 67:

```python
_REGISTERS = frozenset({"formal", "informal", "teencode", "non_diacritic", "mixed"})
```

And line 221 (inside the `register-classifier` agent's `system_prompt`):

```python
                "teencode, non_diacritic (Vietnamese written without diacritics), mixed. "
```

- [ ] **Step 6: Rename the registry test**

In `tests/test_registry.py`, rename the test at line 44 and update its body:

```python
def test_register_accepts_non_diacritic():
    """Non-diacritic Vietnamese is a register we track, not noise to discard."""
    assert get("register-classifier").validate({"register": "non_diacritic"}, "x")["register"] == "non_diacritic"
```

- [ ] **Step 7: Run every affected test file to verify green**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_fixture_corpus.py /app/tests/test_registry.py -v'
```

Expected: PASS, all tests (6 in `test_fixture_corpus.py`, the full
`test_registry.py` suite including the renamed test). Also run the full
suite once to confirm no other file references the old name:

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint sh agents -c "grep -rn khong_dau /app/src /app/tests || echo NONE_FOUND"'
```

Expected: `NONE_FOUND`.

- [ ] **Step 8: Commit**

```bash
git add src/vietnlp/acquisition/fixture_schema.py tests/fixtures/generate_fixture_corpus.py \
    tests/fixtures/corpus/fixture_corpus.jsonl tests/test_fixture_corpus.py \
    src/vietnlp/platform/agents/registry.py tests/test_registry.py
git commit -m "rename: khong_dau -> non_diacritic register label, spec-mandated (P0 review finding)"
```

---

### Task 2: Migration 0002 — `sources.rate_limit_seconds`

**Files:**
- Create: `src/vietnlp/platform/db/migrations/0002_source_rate_limit.sql`
- Modify: `tests/test_db_migrate.py` (add one test)

**Interfaces:**
- Consumes: `apply(database_url, migrations_dir)` / `status(...)` from
  `src/vietnlp/platform/db/migrate.py` (P0, unchanged).
- Produces: `sources.rate_limit_seconds INT NOT NULL DEFAULT 5` — the column
  Task 4 (source vetting module) and Task 8/9 (crawler, acquisition_flow)
  read to pace requests per source.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_db_migrate.py` (alongside the other `apply()`-based
tests):

```python
def test_apply_adds_rate_limit_seconds_column(live_db):
    apply(live_db)
    with psycopg.connect(live_db) as conn:
        cols = {
            r[0]
            for r in conn.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = current_schema() AND table_name = 'sources'"
            ).fetchall()
        }
    assert "rate_limit_seconds" in cols
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --entrypoint pytest agents /app/tests/test_db_migrate.py::test_apply_adds_rate_limit_seconds_column -v'
```

Expected: FAIL — `assert "rate_limit_seconds" in cols` (the column doesn't
exist yet; 0002 hasn't been written).

- [ ] **Step 3: Write the migration**

Create `src/vietnlp/platform/db/migrations/0002_source_rate_limit.sql`:

```sql
-- 0002_source_rate_limit.sql
-- Adds per-source politeness rate limiting for P1's acquisition crawler.
-- Postgres is a projection of Gold (CLAUDE.md rule 3): additive DDL only,
-- no data-fixing UPDATE/DELETE.

ALTER TABLE sources ADD COLUMN IF NOT EXISTS rate_limit_seconds INT NOT NULL DEFAULT 5;
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --entrypoint pytest agents /app/tests/test_db_migrate.py -v'
```

Expected: PASS, all tests in the file (the existing ones plus this new
one) — run with dependencies up (no `--no-deps`) since this needs live
Postgres; the live-DB tests here are not self-skipping by design.

- [ ] **Step 5: Commit**

```bash
git add src/vietnlp/platform/db/migrations/0002_source_rate_limit.sql tests/test_db_migrate.py
git commit -m "feat: add sources.rate_limit_seconds for per-source crawl politeness"
```

---

### Task 3: Shared live-dependency test fixtures + source vetting module

**Files:**
- Create: `tests/conftest.py`
- Modify: `tests/test_db_migrate.py` (remove local `live_db`/
  `_live_database_url`, now provided by `conftest.py`)
- Modify: `tests/test_storage_bronze.py` (remove local `live_store`/
  `_live_store`, now provided by `conftest.py`)
- Create: `src/vietnlp/acquisition/sources.py`
- Test: `tests/test_acquisition_sources.py`

**Interfaces:**
- Consumes: `apply`, `DEFAULT_DATABASE_URL` from `platform/db/migrate.py`;
  `BronzeStore` from `platform/storage/bronze.py` (only for the moved
  `live_store` fixture, unchanged behavior).
- Produces: `SourceRecord` (frozen dataclass: `id, name, tier, base_url,
  license, robots_policy, enabled, rate_limit_seconds`), `SourceError
  (RuntimeError)`, `register_source(database_url, name, tier, *,
  base_url=None, license=None, robots_policy=None, rate_limit_seconds=5,
  enabled=True) -> int`, `get_source(database_url, name) -> SourceRecord`,
  `list_enabled_sources(database_url, tier=None) -> list[SourceRecord]`.
  Tasks 6-9 all consume `SourceRecord` and `get_source`/`list_enabled_sources`.
  The shared `live_db` and `live_store` pytest fixtures in `conftest.py`
  are consumed by this task's own tests and by every later task's live
  tests.

The P0 final whole-branch review flagged "two near-identical live-probe
fixtures with no shared home" as a Minor, non-blocking finding. This task
resolves it as a side effect of needing the same pattern a third time.

- [ ] **Step 1: Move both live-dependency fixtures into `conftest.py`**

Read the current `live_db` fixture (and its `_live_database_url` helper)
from `tests/test_db_migrate.py`, and the current `live_store` fixture (and
its `_live_store` helper) from `tests/test_storage_bronze.py`. Cut them out
of both files verbatim — no behavior change — and create
`tests/conftest.py`:

```python
"""Shared pytest fixtures for tests that touch live Postgres or MinIO.

Both fixtures probe for a reachable live dependency and self-skip if it
isn't there, so `pytest -q` (no --no-deps override) stays green without any
service running. `make test-live` proves the same tests pass for real.
"""
import os
from urllib.parse import quote

import psycopg
import pytest
from minio.error import S3Error

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
```

Note the `search_path` fix from P0's Task 8 (`{schema},public`, not just
`{schema}`) is preserved exactly — this is the same fixture, just relocated.

Remove the now-duplicate `import os`, `from urllib.parse import quote`, and
the two fixture/helper definitions from `tests/test_db_migrate.py` — its
`live_db`-using tests are otherwise unchanged, since pytest auto-discovers
fixtures from `conftest.py` in the same directory tree with no import
needed. Do the same for `live_store` in `tests/test_storage_bronze.py`.

- [ ] **Step 2: Run the moved-fixture tests to confirm nothing broke**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --entrypoint pytest agents /app/tests/test_db_migrate.py /app/tests/test_storage_bronze.py -v'
```

Expected: PASS, same test counts as before this task (9 in
`test_db_migrate.py` including Task 2's new test, 9 in
`test_storage_bronze.py`) — the fixtures moved, nothing about their
behavior changed.

- [ ] **Step 3: Write the failing test for source vetting**

Create `tests/test_acquisition_sources.py`:

```python
"""Source vetting record: corpus-scout's authorization gate for acquisition.
Live-Postgres tests, self-skipping under --no-deps (see conftest.py)."""
import pytest

from vietnlp.acquisition.sources import SourceError, get_source, list_enabled_sources, register_source


def test_register_then_get_round_trips(live_db):
    register_source(live_db, "test-news", "news_gov_wiki", base_url="https://news.example.vn", license="cc-by")
    record = get_source(live_db, "test-news")
    assert record.name == "test-news"
    assert record.tier == "news_gov_wiki"
    assert record.base_url == "https://news.example.vn"
    assert record.enabled is True
    assert record.rate_limit_seconds == 5  # default


def test_register_rejects_unknown_tier(live_db):
    with pytest.raises(SourceError, match="tier"):
        register_source(live_db, "test-bad-tier", "not_a_real_tier")


def test_get_source_raises_for_unregistered_name(live_db):
    with pytest.raises(SourceError, match="no source named"):
        get_source(live_db, "never-registered")


def test_register_is_idempotent_by_name(live_db):
    register_source(live_db, "test-idempotent", "public_corpus", rate_limit_seconds=5)
    register_source(live_db, "test-idempotent", "public_corpus", rate_limit_seconds=10)
    record = get_source(live_db, "test-idempotent")
    assert record.rate_limit_seconds == 10  # second registration updates, doesn't duplicate


def test_list_enabled_sources_excludes_disabled(live_db):
    register_source(live_db, "test-enabled", "forum_qa_blog", enabled=True)
    register_source(live_db, "test-disabled", "forum_qa_blog", enabled=False)
    names = {s.name for s in list_enabled_sources(live_db, tier="forum_qa_blog")}
    assert "test-enabled" in names
    assert "test-disabled" not in names


def test_list_enabled_sources_filters_by_tier(live_db):
    register_source(live_db, "test-tier-a", "news_gov_wiki")
    register_source(live_db, "test-tier-b", "public_corpus")
    names = {s.name for s in list_enabled_sources(live_db, tier="news_gov_wiki")}
    assert "test-tier-a" in names
    assert "test-tier-b" not in names
```

- [ ] **Step 4: Run the test to verify it fails**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --entrypoint pytest agents /app/tests/test_acquisition_sources.py -v'
```

Expected: FAIL — `ModuleNotFoundError: No module named 'vietnlp.acquisition.sources'`.

- [ ] **Step 5: Write the implementation**

Create `src/vietnlp/acquisition/sources.py`:

```python
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
```

- [ ] **Step 6: Run the test to verify it passes**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --entrypoint pytest agents /app/tests/test_acquisition_sources.py -v'
```

Expected: PASS, 6 tests.

- [ ] **Step 7: Commit**

```bash
git add tests/conftest.py tests/test_db_migrate.py tests/test_storage_bronze.py \
    src/vietnlp/acquisition/sources.py tests/test_acquisition_sources.py
git commit -m "feat: source vetting module, and consolidate live-dependency test fixtures into conftest.py"
```

---

### Task 4: Acquisition primitives — rate limiter and author-hashing

**Files:**
- Create: `src/vietnlp/acquisition/rate_limiter.py`
- Create: `src/vietnlp/acquisition/anonymize.py`
- Test: `tests/test_acquisition_rate_limiter.py`
- Test: `tests/test_acquisition_anonymize.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `TokenBucket` (dataclass: `rate_limit_seconds: float`) with
  `.acquire(*, _sleep=time.sleep, _now=time.monotonic) -> float` (blocks
  until allowed, returns actual wait seconds); `hash_author_id(raw: str) ->
  str`. Task 8 (crawler) consumes `TokenBucket`; Tasks 7/8 may consume
  `hash_author_id` wherever a source exposes a structured author/username
  field distinct from the document body.

- [ ] **Step 1: Write the failing tests for the rate limiter**

Create `tests/test_acquisition_rate_limiter.py`:

```python
"""Pure logic, deterministic clock/sleep injection -- no real waiting in tests."""
import pytest

from vietnlp.acquisition.rate_limiter import TokenBucket


def _fail_if_called(*_args, **_kwargs):
    raise AssertionError("should not have slept")


def test_first_acquire_does_not_wait():
    bucket = TokenBucket(rate_limit_seconds=5.0)
    waited = bucket.acquire(_sleep=_fail_if_called, _now=lambda: 100.0)
    assert waited == 0.0


def test_second_acquire_within_interval_waits_the_remainder():
    bucket = TokenBucket(rate_limit_seconds=5.0)
    clock = iter([100.0, 102.0])
    sleeps = []
    bucket.acquire(_now=lambda: next(clock), _sleep=_fail_if_called)
    waited = bucket.acquire(_now=lambda: next(clock), _sleep=sleeps.append)
    assert waited == 3.0
    assert sleeps == [3.0]


def test_acquire_after_interval_elapsed_does_not_wait():
    bucket = TokenBucket(rate_limit_seconds=5.0)
    clock = iter([100.0, 106.0])
    bucket.acquire(_now=lambda: next(clock), _sleep=_fail_if_called)
    waited = bucket.acquire(_now=lambda: next(clock), _sleep=_fail_if_called)
    assert waited == 0.0
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_acquisition_rate_limiter.py -v'
```

Expected: FAIL — `ModuleNotFoundError: No module named 'vietnlp.acquisition.rate_limiter'`.

- [ ] **Step 3: Implement the rate limiter**

Create `src/vietnlp/acquisition/rate_limiter.py`:

```python
"""Token-bucket rate limiting, one bucket per source.

Politeness is structural, not advisory: acquire() blocks until a request is
allowed, so a caller cannot outrun the vetted rate_limit_seconds by mistake.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class TokenBucket:
    rate_limit_seconds: float
    _last_request_at: float | None = field(default=None, repr=False)

    def acquire(self, *, _sleep=time.sleep, _now=time.monotonic) -> float:
        """Block until a request is allowed. Returns the actual wait (seconds)."""
        now = _now()
        waited = 0.0
        if self._last_request_at is not None:
            elapsed = now - self._last_request_at
            waited = max(0.0, self.rate_limit_seconds - elapsed)
            if waited > 0:
                _sleep(waited)
        self._last_request_at = now + waited
        return waited
```

- [ ] **Step 4: Run the rate-limiter tests to verify they pass**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_acquisition_rate_limiter.py -v'
```

Expected: PASS, 3 tests.

- [ ] **Step 5: Write the failing tests for author-hashing**

Create `tests/test_acquisition_anonymize.py`:

```python
"""CLAUDE.md: hash author identifiers at ingest, never persist raw handles."""
from vietnlp.acquisition.anonymize import hash_author_id


def test_hash_is_stable_for_identical_input(monkeypatch):
    monkeypatch.setenv("VIETNLP_AUTHOR_HASH_SALT", "test-salt")
    assert hash_author_id("nguyen_van_a") == hash_author_id("nguyen_van_a")


def test_hash_differs_for_different_input(monkeypatch):
    monkeypatch.setenv("VIETNLP_AUTHOR_HASH_SALT", "test-salt")
    assert hash_author_id("user_one") != hash_author_id("user_two")


def test_hash_is_sha256_hex_length(monkeypatch):
    monkeypatch.setenv("VIETNLP_AUTHOR_HASH_SALT", "test-salt")
    assert len(hash_author_id("someone")) == 64


def test_hash_changes_with_different_salt(monkeypatch):
    monkeypatch.setenv("VIETNLP_AUTHOR_HASH_SALT", "salt-a")
    h1 = hash_author_id("same_user")
    monkeypatch.setenv("VIETNLP_AUTHOR_HASH_SALT", "salt-b")
    h2 = hash_author_id("same_user")
    assert h1 != h2
```

- [ ] **Step 6: Run the tests to verify they fail**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_acquisition_anonymize.py -v'
```

Expected: FAIL — `ModuleNotFoundError: No module named 'vietnlp.acquisition.anonymize'`.

- [ ] **Step 7: Implement author-hashing**

Create `src/vietnlp/acquisition/anonymize.py`:

```python
"""Author-identifier hashing (CLAUDE.md: hash at ingest, never persist raw
handles). The salt lives in the environment, never in code or logs -- same
secrecy discipline as the DeepSeek API key in platform/agents/client.py.
"""

from __future__ import annotations

import hashlib
import os

_SALT_ENV = "VIETNLP_AUTHOR_HASH_SALT"


def hash_author_id(raw: str) -> str:
    """SHA-256 of the raw handle, salted so the hash cannot be reversed by
    dictionary-matching against a list of known usernames."""
    salt = os.getenv(_SALT_ENV, "")
    return hashlib.sha256((salt + raw).encode("utf-8")).hexdigest()
```

- [ ] **Step 8: Run the tests to verify they pass**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_acquisition_anonymize.py -v'
```

Expected: PASS, 4 tests.

- [ ] **Step 9: Commit**

```bash
git add src/vietnlp/acquisition/rate_limiter.py src/vietnlp/acquisition/anonymize.py \
    tests/test_acquisition_rate_limiter.py tests/test_acquisition_anonymize.py
git commit -m "feat: rate limiter and author-identifier hashing primitives for acquisition"
```

---

### Task 5: z.ai MCP client wrapper (web-search-prime, web-reader)

**Files:**
- Create: `src/vietnlp/acquisition/mcp_client.py`
- Test: `tests/test_acquisition_mcp_client.py`
- Modify: `pyproject.toml` (add `mcp` dependency)
- Modify: `deploy/Dockerfile` (install it)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `MCPError(RuntimeError)`, `web_search(query: str, count: int =
  10) -> list[dict]` (each dict has at least `url`, and typically `title`,
  `snippet`), `web_read(url: str) -> str`. Task 7 (web discovery) consumes
  both.

**Why this exists:** CLAUDE.md's architecture names `web-search-prime` and
`web-reader` as pipeline stages, but those are MCP tools available to an
interactive Claude Code session — not to unattended Python running in the
`agents` container on `_59`. Both are plain HTTP-transport MCP servers
(`https://api.z.ai/api/mcp/web_search_prime/mcp` and `https://api.z.ai/api/
mcp/web_reader/mcp`, Bearer-token authenticated), so this module speaks the
MCP protocol directly via the official `mcp` Python SDK, the same way
`platform/agents/client.py` speaks DeepSeek's HTTP API directly.

**A genuine open question this task must resolve empirically, not by
assumption:** the exact shape of `web_search_prime`'s and `webReader`'s
tool-call results (their argument names, and whether results come back as a
JSON string, a list of content blocks, or something else) is not fully
knowable without a live call. Step 6 below is where this gets resolved for
real — do not skip it or assume the parsing code in Step 3 is correct until
Step 6 confirms it against the live server.

- [ ] **Step 1: Add the `mcp` dependency**

In `pyproject.toml`, add to `[project].dependencies`:

```toml
    "mcp>=1.0",
```

In `deploy/Dockerfile`, add `mcp>=1.0` to the existing multi-line
dependency install (the same `RUN pip install --no-cache-dir ...` block
Task 1 of the P0 plan already extended once).

- [ ] **Step 2: Write the failing tests (offline, no network involved)**

Create `tests/test_acquisition_mcp_client.py`:

```python
"""The missing-credential guard is the one thing about this module fully
knowable and testable offline, since it's checked before any network call
is made. Step 6 of this task (a manual, not-committed verification) is
where the real result shape gets checked against the live z.ai server --
that step is not a pytest test, because it needs a real ZAI_API_KEY this
offline suite must never depend on."""
import pytest

from vietnlp.acquisition.mcp_client import MCPError, web_read, web_search


def test_web_search_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("ZAI_API_KEY", raising=False)
    with pytest.raises(MCPError, match="ZAI_API_KEY"):
        web_search("Vietnamese news today")


def test_web_read_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("ZAI_API_KEY", raising=False)
    with pytest.raises(MCPError, match="ZAI_API_KEY"):
        web_read("https://example.vn/article")
```

(Two tests here deliberately: the missing-credential guard is the one thing
fully knowable and testable offline without pinning down the live server's
exact wire format. Step 6's live test is where the true round trip gets
proven.)

- [ ] **Step 3: Run the tests to verify they fail**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_acquisition_mcp_client.py -v'
```

Expected: FAIL — `ModuleNotFoundError: No module named 'vietnlp.acquisition.mcp_client'`.

- [ ] **Step 4: Write the implementation**

Create `src/vietnlp/acquisition/mcp_client.py`:

```python
"""Thin synchronous wrapper around z.ai's web-search-prime and web-reader
MCP tools, called directly over MCP's Streamable HTTP transport. This runs
as unattended Python in a Prefect flow -- there is no Claude Code MCP
runtime available here -- so it speaks the MCP protocol itself via the
official `mcp` SDK, the same way platform/agents/client.py speaks
DeepSeek's HTTP API directly rather than through any wrapper.
"""

from __future__ import annotations

import asyncio
import json
import os

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

_SEARCH_URL = "https://api.z.ai/api/mcp/web_search_prime/mcp"
_READER_URL = "https://api.z.ai/api/mcp/web_reader/mcp"
_API_KEY_ENV = "ZAI_API_KEY"


class MCPError(RuntimeError):
    pass


def _api_key() -> str:
    key = os.getenv(_API_KEY_ENV, "").strip()
    if not key:
        raise MCPError(f"{_API_KEY_ENV} not set. (Value is never logged.)")
    return key


async def _call_tool(url: str, tool_name: str, arguments: dict) -> list[str]:
    headers = {"Authorization": f"Bearer {_api_key()}"}
    async with streamablehttp_client(url, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            if result.isError:
                raise MCPError(f"{tool_name} returned an error: {result.content}")
            # MCP tool results are a list of content blocks; text-typed
            # blocks carry `.text` (per the MCP spec). Non-text block types
            # are not expected from either of these two tools.
            texts = [block.text for block in result.content if hasattr(block, "text")]
            if not texts:
                raise MCPError(f"{tool_name} returned no text content: {result.content!r}")
            return texts


def web_search(query: str, count: int = 10) -> list[dict]:
    """Discover candidate URLs for a query. Returns a list of dicts, each
    with at least a `url` key."""
    texts = asyncio.run(_call_tool(_SEARCH_URL, "web_search_prime", {"query": query, "count": count}))
    combined = "\n".join(texts)
    try:
        parsed = json.loads(combined)
    except json.JSONDecodeError as exc:
        raise MCPError(
            f"web_search_prime result was not JSON as expected: {exc}. "
            f"Raw text (first 500 chars): {combined[:500]!r}"
        ) from exc
    results = parsed if isinstance(parsed, list) else parsed.get("results", [])
    return results


def web_read(url: str) -> str:
    """Extract clean text from one URL."""
    texts = asyncio.run(_call_tool(_READER_URL, "webReader", {"url": url}))
    return "\n".join(texts)
```

- [ ] **Step 5: Run the offline tests to verify they pass**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_acquisition_mcp_client.py -v'
```

Expected: PASS, 2 tests.

- [ ] **Step 6: Resolve the real result shape against the live server**

This step is not optional polish — it is where Step 4's parsing
assumptions get checked against reality. `ZAI_API_KEY` needs to be added to
`deploy/.env` on `_59` first (ask for this credential if it is not already
available; do not fabricate or reuse a key from an unrelated context
without confirming it is the right one for a deployed service).

Once the key is in place, run a small ad-hoc check (not a committed test —
a one-off verification):

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint python agents -c "
from vietnlp.acquisition.mcp_client import web_search, web_read
results = web_search(\"Viet Nam thoi tiet hom nay\", count=3)
print(\"web_search result:\", results)
if results:
    text = web_read(results[0][\"url\"])
    print(\"web_read text (first 300 chars):\", text[:300])
"'
```

If the actual result shape differs from Step 4's assumptions (e.g. the tool
name is not exactly `web_search_prime`/`webReader`, the argument is not
`query`/`url`, or the JSON structure differs from `list[dict]` with a `url`
key), fix `mcp_client.py` to match what you actually observed — do not
force the real server to match the guess. Add a comment at the top of
`web_search`/`web_read` noting the ground truth you found (e.g. "confirmed
2026-08-24 against the live z.ai server: result is a JSON array of
{title, url, snippet}"). If the parsing needed to change, add a matching
unit test to `tests/test_acquisition_mcp_client.py` covering the corrected
shape with a `respx`-mocked response, so the offline suite protects the
corrected behavior going forward.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml deploy/Dockerfile src/vietnlp/acquisition/mcp_client.py tests/test_acquisition_mcp_client.py
git commit -m "feat: z.ai MCP client for web-search-prime and web-reader, callable from unattended Python"
```

---

### Task 6: Public corpus loader (`tier: public_corpus`)

**Files:**
- Create: `src/vietnlp/acquisition/loaders/__init__.py`
- Create: `src/vietnlp/acquisition/loaders/public_corpus.py`
- Test: `tests/test_acquisition_loaders_public_corpus.py`

**Interfaces:**
- Consumes: `SourceRecord` from `acquisition/sources.py` (Task 3).
- Produces: `load_jsonl_corpus(path: Path, source: SourceRecord, bronze,
  dead_letter_sink: Callable[[tuple[dict, str]], None] | None = None) ->
  dict` returning `{"loaded": int, "dead_lettered": int}`. `bronze` is
  typed as `BronzeStore` but the test fakes it — see Step 1.

Public corpora (OSCAR/CC-100 Vietnamese subset, Wikipedia dumps, existing
VLSP/UIT datasets) are large, licensed bulk downloads fetched out-of-band,
not something this loader fetches itself. It reads a local JSONL file, one
document per line: `{"text": str, "url": str | null, "license": str |
null}`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_acquisition_loaders_public_corpus.py`:

```python
"""Offline: fakes BronzeStore.put_record rather than requiring live MinIO --
end-to-end proof against the real store happens once, holistically, in
Task 10's deploy verification, not per-loader here."""
import json

from vietnlp.acquisition.loaders.public_corpus import load_jsonl_corpus
from vietnlp.acquisition.sources import SourceRecord


class _FakeBronzeStore:
    def __init__(self):
        self.records: list[dict] = []

    def put_record(self, record: dict) -> str:
        self.records.append(record)
        return f"bronze/fake/{len(self.records)}.parquet"


def _source(**overrides) -> SourceRecord:
    defaults = dict(
        id=1, name="test-corpus", tier="public_corpus", base_url=None,
        license="cc-by", robots_policy=None, enabled=True, rate_limit_seconds=5,
    )
    defaults.update(overrides)
    return SourceRecord(**defaults)


def _write_jsonl(tmp_path, lines: list[dict]):
    path = tmp_path / "corpus.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for line in lines:
            f.write(json.dumps(line) + "\n")
    return path


def test_loads_every_valid_line(tmp_path):
    path = _write_jsonl(tmp_path, [
        {"text": "Xin chao Viet Nam.", "url": "https://corpus.example/1", "license": "cc-by"},
        {"text": "Cau thu hai.", "url": "https://corpus.example/2", "license": "cc-by"},
    ])
    bronze = _FakeBronzeStore()
    result = load_jsonl_corpus(path, _source(), bronze)
    assert result == {"loaded": 2, "dead_lettered": 0}
    assert len(bronze.records) == 2
    assert bronze.records[0]["source_id"] == "test-corpus"
    assert bronze.records[0]["raw_payload"] == "Xin chao Viet Nam.".encode("utf-8")


def test_dead_letters_a_line_with_empty_text(tmp_path):
    path = _write_jsonl(tmp_path, [{"text": "", "url": "https://corpus.example/1"}])
    bronze = _FakeBronzeStore()
    caught = []
    result = load_jsonl_corpus(path, _source(), bronze, dead_letter_sink=caught.append)
    assert result == {"loaded": 0, "dead_lettered": 1}
    assert len(caught) == 1


def test_dead_letters_a_line_missing_text_key(tmp_path):
    path = _write_jsonl(tmp_path, [{"url": "https://corpus.example/1"}])
    bronze = _FakeBronzeStore()
    result = load_jsonl_corpus(path, _source(), bronze)
    assert result == {"loaded": 0, "dead_lettered": 1}


def test_falls_back_to_source_license_when_line_omits_it(tmp_path):
    path = _write_jsonl(tmp_path, [{"text": "Noi dung."}])
    bronze = _FakeBronzeStore()
    load_jsonl_corpus(path, _source(license="source-default-license"), bronze)
    assert bronze.records[0]["license"] == "source-default-license"


def test_skips_blank_lines(tmp_path):
    path = tmp_path / "corpus.jsonl"
    path.write_text('{"text": "Mot."}\n\n{"text": "Hai."}\n', encoding="utf-8")
    bronze = _FakeBronzeStore()
    result = load_jsonl_corpus(path, _source(), bronze)
    assert result == {"loaded": 2, "dead_lettered": 0}
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_acquisition_loaders_public_corpus.py -v'
```

Expected: FAIL — `ModuleNotFoundError: No module named 'vietnlp.acquisition.loaders'`.

- [ ] **Step 3: Write the implementation**

Create `src/vietnlp/acquisition/loaders/__init__.py` (empty file).

Create `src/vietnlp/acquisition/loaders/public_corpus.py`:

```python
"""Loads a local, pre-downloaded public-corpus JSONL dump into Bronze.

Public corpora (OSCAR/CC-100 Vietnamese, Wikipedia dumps, VLSP/UIT
datasets) are downloaded out-of-band -- they are large, licensed bulk
files, not something this loader fetches itself.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from vietnlp.acquisition.sources import SourceRecord

DeadLetterSink = Callable[[tuple[dict, str]], None]


def load_jsonl_corpus(
    path: Path,
    source: SourceRecord,
    bronze,
    dead_letter_sink: DeadLetterSink | None = None,
) -> dict:
    """Read `path`'s JSONL lines and write each as a Bronze record.

    Returns {"loaded": int, "dead_lettered": int}.
    """
    loaded = 0
    dead_lettered = 0
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            text = raw.get("text")
            if not text:
                dead_lettered += 1
                if dead_letter_sink is not None:
                    dead_letter_sink((raw, "missing or empty 'text' field"))
                continue

            record = {
                "source_id": source.name,
                "url": raw.get("url") or f"corpus://{source.name}",
                "fetched_at": datetime.now(timezone.utc),
                "http_status": 200,
                "robots_decision": "not_applicable",
                "content_type": "text/plain; charset=utf-8",
                "raw_payload": text.encode("utf-8"),
                "license": raw.get("license") or source.license or "unknown",
            }
            bronze.put_record(record)
            loaded += 1
    return {"loaded": loaded, "dead_lettered": dead_lettered}
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_acquisition_loaders_public_corpus.py -v'
```

Expected: PASS, 5 tests.

- [ ] **Step 5: Commit**

```bash
git add src/vietnlp/acquisition/loaders/__init__.py src/vietnlp/acquisition/loaders/public_corpus.py \
    tests/test_acquisition_loaders_public_corpus.py
git commit -m "feat: public-corpus JSONL loader for tier=public_corpus sources"
```

---

### Task 7: Web discovery + extraction loader (`tier: news_gov_wiki`)

**Files:**
- Create: `src/vietnlp/acquisition/loaders/web_discovery.py`
- Test: `tests/test_acquisition_loaders_web_discovery.py`

**Interfaces:**
- Consumes: `web_search`, `web_read`, `MCPError` from `acquisition/
  mcp_client.py` (Task 5); `SourceRecord` from `acquisition/sources.py`
  (Task 3).
- Produces: `discover_and_extract(source: SourceRecord, query: str, bronze,
  max_results: int = 10, dead_letter_sink=None) -> dict` returning
  `{"loaded": int, "dead_lettered": int}`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_acquisition_loaders_web_discovery.py`:

```python
"""Offline: monkeypatches web_search/web_read (Task 5's module-level
functions) and fakes BronzeStore, so no live network or MinIO is needed."""
from vietnlp.acquisition.loaders.web_discovery import discover_and_extract
from vietnlp.acquisition.mcp_client import MCPError
from vietnlp.acquisition.sources import SourceRecord


class _FakeBronzeStore:
    def __init__(self):
        self.records: list[dict] = []

    def put_record(self, record: dict) -> str:
        self.records.append(record)
        return f"bronze/fake/{len(self.records)}.parquet"


def _source(**overrides) -> SourceRecord:
    defaults = dict(
        id=1, name="test-news", tier="news_gov_wiki", base_url="https://news.example.vn",
        license="cc-by", robots_policy="allowed", enabled=True, rate_limit_seconds=5,
    )
    defaults.update(overrides)
    return SourceRecord(**defaults)


def test_extracts_every_in_domain_hit(monkeypatch):
    hits = [
        {"url": "https://news.example.vn/a", "title": "A"},
        {"url": "https://news.example.vn/b", "title": "B"},
    ]
    monkeypatch.setattr("vietnlp.acquisition.loaders.web_discovery.web_search", lambda q, count=10: hits)
    monkeypatch.setattr("vietnlp.acquisition.loaders.web_discovery.web_read", lambda url: f"content of {url}")

    bronze = _FakeBronzeStore()
    result = discover_and_extract(_source(), "tin tuc hom nay", bronze)
    assert result == {"loaded": 2, "dead_lettered": 0}
    assert bronze.records[0]["url"] == "https://news.example.vn/a"
    assert bronze.records[0]["raw_payload"] == b"content of https://news.example.vn/a"


def test_dead_letters_hits_outside_the_source_domain(monkeypatch):
    hits = [{"url": "https://not-the-vetted-domain.example/a", "title": "A"}]
    monkeypatch.setattr("vietnlp.acquisition.loaders.web_discovery.web_search", lambda q, count=10: hits)
    monkeypatch.setattr(
        "vietnlp.acquisition.loaders.web_discovery.web_read",
        lambda url: (_ for _ in ()).throw(AssertionError("should not extract an out-of-domain hit")),
    )

    bronze = _FakeBronzeStore()
    caught = []
    result = discover_and_extract(_source(), "query", bronze, dead_letter_sink=caught.append)
    assert result == {"loaded": 0, "dead_lettered": 1}
    assert "outside" in caught[0][1]


def test_dead_letters_on_extraction_failure(monkeypatch):
    hits = [{"url": "https://news.example.vn/broken", "title": "Broken"}]
    monkeypatch.setattr("vietnlp.acquisition.loaders.web_discovery.web_search", lambda q, count=10: hits)

    def _raise(url):
        raise MCPError("extraction failed")

    monkeypatch.setattr("vietnlp.acquisition.loaders.web_discovery.web_read", _raise)

    bronze = _FakeBronzeStore()
    result = discover_and_extract(_source(), "query", bronze)
    assert result == {"loaded": 0, "dead_lettered": 1}


def test_dead_letters_empty_extracted_text(monkeypatch):
    hits = [{"url": "https://news.example.vn/empty", "title": "Empty"}]
    monkeypatch.setattr("vietnlp.acquisition.loaders.web_discovery.web_search", lambda q, count=10: hits)
    monkeypatch.setattr("vietnlp.acquisition.loaders.web_discovery.web_read", lambda url: "   ")

    bronze = _FakeBronzeStore()
    result = discover_and_extract(_source(), "query", bronze)
    assert result == {"loaded": 0, "dead_lettered": 1}


def test_raises_if_source_has_no_base_url(monkeypatch):
    import pytest
    monkeypatch.setattr("vietnlp.acquisition.loaders.web_discovery.web_search", lambda q, count=10: [])
    with pytest.raises(ValueError, match="base_url"):
        discover_and_extract(_source(base_url=None), "query", _FakeBronzeStore())
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_acquisition_loaders_web_discovery.py -v'
```

Expected: FAIL — `ModuleNotFoundError: No module named 'vietnlp.acquisition.loaders.web_discovery'`.

- [ ] **Step 3: Write the implementation**

Create `src/vietnlp/acquisition/loaders/web_discovery.py`:

```python
"""Web discovery + extraction, for tier=news_gov_wiki sources.

Calls web_search (the z.ai MCP client) to find candidate URLs under the
source's vetted domain, then web_read to extract clean text from each,
writing every extracted document to Bronze.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable
from urllib.parse import urlparse

from vietnlp.acquisition.mcp_client import MCPError, web_read, web_search
from vietnlp.acquisition.sources import SourceRecord

DeadLetterSink = Callable[[tuple[dict, str]], None]


def discover_and_extract(
    source: SourceRecord,
    query: str,
    bronze,
    max_results: int = 10,
    dead_letter_sink: DeadLetterSink | None = None,
) -> dict:
    """Search `query` scoped to `source.base_url`'s domain, extract each
    hit, write to Bronze. Returns {"loaded": int, "dead_lettered": int}."""
    if not source.base_url:
        raise ValueError(f"source {source.name!r} has no base_url; cannot scope discovery")
    domain = urlparse(source.base_url).netloc

    hits = web_search(f"{query} site:{domain}", count=max_results)

    loaded = 0
    dead_lettered = 0
    for hit in hits:
        url = hit.get("url")
        if not url or urlparse(url).netloc != domain:
            dead_lettered += 1
            if dead_letter_sink is not None:
                dead_letter_sink((hit, "search result outside source's vetted domain"))
            continue
        try:
            text = web_read(url)
        except MCPError as exc:
            dead_lettered += 1
            if dead_letter_sink is not None:
                dead_letter_sink((hit, str(exc)))
            continue
        if not text.strip():
            dead_lettered += 1
            if dead_letter_sink is not None:
                dead_letter_sink((hit, "web_read returned empty text"))
            continue

        record = {
            "source_id": source.name,
            "url": url,
            "fetched_at": datetime.now(timezone.utc),
            "http_status": 200,
            "robots_decision": "allowed",  # source is enabled: corpus-scout already vetted robots.txt
            "content_type": "text/plain; charset=utf-8",
            "raw_payload": text.encode("utf-8"),
            "license": source.license or "unknown",
        }
        bronze.put_record(record)
        loaded += 1
    return {"loaded": loaded, "dead_lettered": dead_lettered}
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_acquisition_loaders_web_discovery.py -v'
```

Expected: PASS, 5 tests.

- [ ] **Step 5: Commit**

```bash
git add src/vietnlp/acquisition/loaders/web_discovery.py tests/test_acquisition_loaders_web_discovery.py
git commit -m "feat: web discovery + extraction loader for tier=news_gov_wiki sources"
```

---

### Task 8: Polite crawler loader (`tier: forum_qa_blog`)

**Files:**
- Create: `src/vietnlp/acquisition/loaders/crawler.py`
- Test: `tests/test_acquisition_loaders_crawler.py`

**Interfaces:**
- Consumes: `TokenBucket` from `acquisition/rate_limiter.py` (Task 4);
  `hash_author_id` from `acquisition/anonymize.py` (Task 4); `SourceRecord`
  from `acquisition/sources.py` (Task 3).
- Produces: `crawl_source(source: SourceRecord, seed_urls: list[str],
  bronze, fetch: Callable[[str], httpx.Response] | None = None,
  dead_letter_sink=None) -> dict` returning `{"loaded": int, "dead_lettered":
  int}`. `fetch` is injectable so tests never make a real HTTP call.

Paginated forums/Q&A sites where search-based discovery (Task 7's approach)
doesn't apply well — this loader is handed an explicit seed list (e.g. a
thread index page's URLs) rather than discovering pages itself.

- [ ] **Step 1: Write the failing test**

Create `tests/test_acquisition_loaders_crawler.py`:

```python
"""Offline: injects a fake `fetch` callable and fakes BronzeStore -- no real
HTTP request or live MinIO needed. The TokenBucket's real timing is exercised
via Task 4's own tests; here we only check crawl_source calls .acquire()
once per URL."""
import httpx

from vietnlp.acquisition.loaders.crawler import crawl_source
from vietnlp.acquisition.sources import SourceRecord


class _FakeBronzeStore:
    def __init__(self):
        self.records: list[dict] = []

    def put_record(self, record: dict) -> str:
        self.records.append(record)
        return f"bronze/fake/{len(self.records)}.parquet"


def _source(**overrides) -> SourceRecord:
    defaults = dict(
        id=1, name="test-forum", tier="forum_qa_blog", base_url="https://forum.example.vn",
        license="cc-by", robots_policy="allowed", enabled=True, rate_limit_seconds=5,
    )
    defaults.update(overrides)
    return SourceRecord(**defaults)


def _fake_fetch(responses: dict[str, httpx.Response]):
    def fetch(url: str) -> httpx.Response:
        return responses[url]
    return fetch


def test_crawls_every_seed_url():
    urls = ["https://forum.example.vn/thread/1", "https://forum.example.vn/thread/2"]
    responses = {u: httpx.Response(200, text=f"post body for {u}") for u in urls}
    bronze = _FakeBronzeStore()
    result = crawl_source(_source(), urls, bronze, fetch=_fake_fetch(responses))
    assert result == {"loaded": 2, "dead_lettered": 0}
    assert bronze.records[0]["raw_payload"] == b"post body for https://forum.example.vn/thread/1"


def test_dead_letters_a_non_200_response():
    urls = ["https://forum.example.vn/thread/gone"]
    responses = {urls[0]: httpx.Response(404, text="not found")}
    bronze = _FakeBronzeStore()
    result = crawl_source(_source(), urls, bronze, fetch=_fake_fetch(responses))
    assert result == {"loaded": 0, "dead_lettered": 1}


def test_dead_letters_empty_body():
    urls = ["https://forum.example.vn/thread/empty"]
    responses = {urls[0]: httpx.Response(200, text="")}
    bronze = _FakeBronzeStore()
    result = crawl_source(_source(), urls, bronze, fetch=_fake_fetch(responses))
    assert result == {"loaded": 0, "dead_lettered": 1}


def test_rejects_a_url_outside_source_domain():
    urls = ["https://not-vetted.example/thread/1"]
    bronze = _FakeBronzeStore()
    caught = []
    result = crawl_source(_source(), urls, bronze, fetch=_fake_fetch({}), dead_letter_sink=caught.append)
    assert result == {"loaded": 0, "dead_lettered": 1}
    assert "outside" in caught[0][1]


def test_paces_requests_through_a_token_bucket(monkeypatch):
    acquired = []
    import vietnlp.acquisition.loaders.crawler as crawler_module

    original_bucket_cls = crawler_module.TokenBucket

    class _TrackingBucket(original_bucket_cls):
        def acquire(self, **kwargs):
            acquired.append(True)
            return 0.0

    monkeypatch.setattr(crawler_module, "TokenBucket", _TrackingBucket)

    urls = ["https://forum.example.vn/thread/1", "https://forum.example.vn/thread/2"]
    responses = {u: httpx.Response(200, text="body") for u in urls}
    crawl_source(_source(), urls, _FakeBronzeStore(), fetch=_fake_fetch(responses))
    assert len(acquired) == 2  # once per URL, before each request
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_acquisition_loaders_crawler.py -v'
```

Expected: FAIL — `ModuleNotFoundError: No module named 'vietnlp.acquisition.loaders.crawler'`.

- [ ] **Step 3: Write the implementation**

Create `src/vietnlp/acquisition/loaders/crawler.py`:

```python
"""Politeness-rate-limited crawler for tier=forum_qa_blog sources.

Handed an explicit seed list (e.g. a thread index's URLs) rather than
discovering pages itself -- paginated forum/Q&A structure varies too much
per site for one generic discovery strategy to handle well.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable
from urllib.parse import urlparse

import httpx

from vietnlp.acquisition.rate_limiter import TokenBucket
from vietnlp.acquisition.sources import SourceRecord

DeadLetterSink = Callable[[tuple[dict, str]], None]
Fetcher = Callable[[str], httpx.Response]


def _default_fetch(url: str) -> httpx.Response:
    return httpx.get(url, timeout=15.0)


def crawl_source(
    source: SourceRecord,
    seed_urls: list[str],
    bronze,
    fetch: Fetcher | None = None,
    dead_letter_sink: DeadLetterSink | None = None,
) -> dict:
    """Fetch each URL in `seed_urls`, one token-bucket-paced request at a
    time, writing survivors to Bronze. Returns {"loaded": int,
    "dead_lettered": int}."""
    fetch = fetch or _default_fetch
    domain = urlparse(source.base_url).netloc if source.base_url else None
    bucket = TokenBucket(rate_limit_seconds=source.rate_limit_seconds)

    loaded = 0
    dead_lettered = 0
    for url in seed_urls:
        if domain is not None and urlparse(url).netloc != domain:
            dead_lettered += 1
            if dead_letter_sink is not None:
                dead_letter_sink(({"url": url}, "URL outside source's vetted domain"))
            continue

        bucket.acquire()
        response = fetch(url)
        if response.status_code != 200:
            dead_lettered += 1
            if dead_letter_sink is not None:
                dead_letter_sink(({"url": url}, f"HTTP {response.status_code}"))
            continue
        body = response.text
        if not body.strip():
            dead_lettered += 1
            if dead_letter_sink is not None:
                dead_letter_sink(({"url": url}, "empty response body"))
            continue

        record = {
            "source_id": source.name,
            "url": url,
            "fetched_at": datetime.now(timezone.utc),
            "http_status": response.status_code,
            "robots_decision": "allowed",  # source is enabled: corpus-scout already vetted robots.txt
            "content_type": response.headers.get("content-type", "text/html"),
            "raw_payload": body.encode("utf-8"),
            "license": source.license or "unknown",
        }
        bronze.put_record(record)
        loaded += 1
    return {"loaded": loaded, "dead_lettered": dead_lettered}
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_acquisition_loaders_crawler.py -v'
```

Expected: PASS, 5 tests.

- [ ] **Step 5: Commit**

```bash
git add src/vietnlp/acquisition/loaders/crawler.py tests/test_acquisition_loaders_crawler.py
git commit -m "feat: rate-limited crawler loader for tier=forum_qa_blog sources"
```

---

### Task 9: `acquisition_flow` (Prefect orchestration)

**Files:**
- Create: `src/vietnlp/platform/flows/acquisition_flow.py`
- Test: `tests/test_flows_acquisition.py`

**Interfaces:**
- Consumes: `get_source`, `SourceError` from `acquisition/sources.py`
  (Task 3); `load_jsonl_corpus` (Task 6), `discover_and_extract` (Task 7),
  `crawl_source` (Task 8).
- Produces: `acquisition_flow(source_name: str, database_url: str, bronze,
  *, jsonl_path: Path | None = None, query: str | None = None,
  seed_urls: list[str] | None = None) -> dict` — a Prefect `@flow`
  returning `{"loaded": int, "dead_lettered": int}`. Dispatches to the
  loader matching `get_source(...).tier`, re-checking `enabled` before
  each dispatch so a mid-run kill-switch flip is honored.

- [ ] **Step 1: Write the failing test**

Create `tests/test_flows_acquisition.py`:

```python
"""Offline via Prefect's official test harness (no server, no network) plus
fakes for the loaders -- consistent with every other flow test in this repo."""
import pytest
from prefect.testing.utilities import prefect_test_harness

from vietnlp.acquisition.sources import SourceError, SourceRecord
from vietnlp.platform.flows.acquisition_flow import acquisition_flow


@pytest.fixture(autouse=True, scope="module")
def _prefect_test_mode():
    with prefect_test_harness():
        yield


class _FakeBronzeStore:
    pass  # never actually touched; the fake loaders below don't call it


def _source(**overrides) -> SourceRecord:
    defaults = dict(
        id=1, name="test-source", tier="public_corpus", base_url=None,
        license="cc-by", robots_policy=None, enabled=True, rate_limit_seconds=5,
    )
    defaults.update(overrides)
    return SourceRecord(**defaults)


def test_dispatches_public_corpus_tier_to_the_jsonl_loader(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "vietnlp.platform.flows.acquisition_flow.get_source",
        lambda database_url, name: _source(tier="public_corpus"),
    )
    called = {}

    def fake_loader(path, source, bronze, dead_letter_sink=None):
        called["path"] = path
        called["source"] = source
        return {"loaded": 5, "dead_lettered": 0}

    monkeypatch.setattr("vietnlp.platform.flows.acquisition_flow.load_jsonl_corpus", fake_loader)

    jsonl = tmp_path / "corpus.jsonl"
    jsonl.write_text("", encoding="utf-8")
    result = acquisition_flow("test-source", "postgresql://fake", _FakeBronzeStore(), jsonl_path=jsonl)
    assert result == {"loaded": 5, "dead_lettered": 0}
    assert called["path"] == jsonl


def test_dispatches_news_gov_wiki_tier_to_web_discovery(monkeypatch):
    monkeypatch.setattr(
        "vietnlp.platform.flows.acquisition_flow.get_source",
        lambda database_url, name: _source(tier="news_gov_wiki", base_url="https://news.example.vn"),
    )
    called = {}

    def fake_discover(source, query, bronze, dead_letter_sink=None):
        called["query"] = query
        return {"loaded": 3, "dead_lettered": 1}

    monkeypatch.setattr("vietnlp.platform.flows.acquisition_flow.discover_and_extract", fake_discover)

    result = acquisition_flow("test-source", "postgresql://fake", _FakeBronzeStore(), query="tin tuc")
    assert result == {"loaded": 3, "dead_lettered": 1}
    assert called["query"] == "tin tuc"


def test_dispatches_forum_qa_blog_tier_to_the_crawler(monkeypatch):
    monkeypatch.setattr(
        "vietnlp.platform.flows.acquisition_flow.get_source",
        lambda database_url, name: _source(tier="forum_qa_blog", base_url="https://forum.example.vn"),
    )
    called = {}

    def fake_crawl(source, seed_urls, bronze, dead_letter_sink=None):
        called["seed_urls"] = seed_urls
        return {"loaded": 2, "dead_lettered": 0}

    monkeypatch.setattr("vietnlp.platform.flows.acquisition_flow.crawl_source", fake_crawl)

    urls = ["https://forum.example.vn/1"]
    result = acquisition_flow("test-source", "postgresql://fake", _FakeBronzeStore(), seed_urls=urls)
    assert result == {"loaded": 2, "dead_lettered": 0}
    assert called["seed_urls"] == urls


def test_refuses_a_disabled_source(monkeypatch):
    """A source flipped to enabled=False must never dispatch a loader --
    this is the structural kill-switch, not a convention."""
    monkeypatch.setattr(
        "vietnlp.platform.flows.acquisition_flow.get_source",
        lambda database_url, name: _source(enabled=False),
    )
    with pytest.raises(SourceError, match="not enabled"):
        acquisition_flow("test-source", "postgresql://fake", _FakeBronzeStore())


def test_refuses_a_source_with_mismatched_tier_arguments(monkeypatch):
    """news_gov_wiki tier with no query given is a caller error, not a
    silent no-op."""
    monkeypatch.setattr(
        "vietnlp.platform.flows.acquisition_flow.get_source",
        lambda database_url, name: _source(tier="news_gov_wiki", base_url="https://news.example.vn"),
    )
    with pytest.raises(ValueError, match="query"):
        acquisition_flow("test-source", "postgresql://fake", _FakeBronzeStore())
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_flows_acquisition.py -v'
```

Expected: FAIL — `ModuleNotFoundError: No module named 'vietnlp.platform.flows.acquisition_flow'`.

- [ ] **Step 3: Write the implementation**

Create `src/vietnlp/platform/flows/acquisition_flow.py`:

```python
"""Acquisition orchestration: dispatches to the loader matching a vetted
source's tier. The kill switch is structural, not conventional -- a
disabled source's `get_source` call raises before any loader runs, on
every invocation, so disabling a source mid-run stops the very next
retry.
"""

from __future__ import annotations

from pathlib import Path

from prefect import flow

from vietnlp.acquisition.loaders.crawler import crawl_source
from vietnlp.acquisition.loaders.public_corpus import load_jsonl_corpus
from vietnlp.acquisition.loaders.web_discovery import discover_and_extract
from vietnlp.acquisition.sources import SourceError, get_source


@flow(name="acquisition")
def acquisition_flow(
    source_name: str,
    database_url: str,
    bronze,
    *,
    jsonl_path: Path | None = None,
    query: str | None = None,
    seed_urls: list[str] | None = None,
) -> dict:
    source = get_source(database_url, source_name)
    if not source.enabled:
        raise SourceError(f"source {source_name!r} is not enabled; refusing to acquire")

    if source.tier == "public_corpus":
        if jsonl_path is None:
            raise ValueError("tier=public_corpus requires jsonl_path")
        return load_jsonl_corpus(jsonl_path, source, bronze)

    if source.tier == "news_gov_wiki":
        if query is None:
            raise ValueError("tier=news_gov_wiki requires query")
        return discover_and_extract(source, query, bronze)

    if source.tier == "forum_qa_blog":
        if seed_urls is None:
            raise ValueError("tier=forum_qa_blog requires seed_urls")
        return crawl_source(source, seed_urls, bronze)

    raise SourceError(f"tier {source.tier!r} has no acquisition path (social is P6, permanently off)")
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests/test_flows_acquisition.py -v'
```

Expected: PASS, 5 tests. (Like `bootstrap_flow.py`'s tests in P0, this is
NOT self-skipping — `prefect_test_harness()` is genuinely offline, so this
must pass for real under `--no-deps`, not skip.)

- [ ] **Step 5: Commit**

```bash
git add src/vietnlp/platform/flows/acquisition_flow.py tests/test_flows_acquisition.py
git commit -m "feat: acquisition_flow dispatches per-source-tier loaders with a structural kill switch"
```

---

### Task 10: Wiring, deploy, and P1a exit-criteria verification

**Files:**
- Modify: `Makefile`
- Modify: `deploy/.env.example`
- Modify: `deploy/README.md`

**Interfaces:**
- Consumes: everything from Tasks 1-9.
- Produces: a deployed, live-verified acquisition pipeline. No new Python
  interfaces.

This proves P1a's exit criterion: the full offline suite stays green
without any live dependency, and a real (small, single-source) acquisition
run against server `_59` actually writes to Bronze — the same
"prove it live, not just offline" discipline P0's Task 8 established.

- [ ] **Step 1: Add the new secrets to `deploy/.env.example`**

```
# P1a: z.ai MCP tools (web-search-prime, web-reader) — see
# src/vietnlp/acquisition/mcp_client.py
ZAI_API_KEY=

# P1a: salts author-identifier hashing so it can't be dictionary-reversed
# against a list of known usernames — see src/vietnlp/acquisition/anonymize.py
VIETNLP_AUTHOR_HASH_SALT=
```

Add both to the real `deploy/.env` on `_59` (mode 600, gitignored, never
synced from/to the repo — same discipline as every existing secret there).
`VIETNLP_AUTHOR_HASH_SALT` can be any random string generated once and kept
stable (rotating it changes every future hash of the same input, which is
fine — it never needs to match a past run's hashes).

- [ ] **Step 2: Add a `run-acquisition` Makefile target**

Add after the existing `migrate` target in `Makefile`:

```makefile
.PHONY: run-acquisition
run-acquisition: ## run acquisition_flow for one source ($(HOST)); SOURCE=name required
	ssh $(HOST) "cd $(REMOTE)/deploy && docker compose run --rm --entrypoint python agents -m vietnlp.platform.flows.acquisition_flow $(SOURCE)"
```

This target assumes `acquisition_flow.py` gains a small `if __name__ ==
"__main__":` CLI entry point. Add one to
`src/vietnlp/platform/flows/acquisition_flow.py`:

```python
def main(argv: list[str] | None = None) -> int:
    import os
    import sys

    from vietnlp.platform.db.migrate import DEFAULT_DATABASE_URL
    from vietnlp.platform.storage.bronze import BronzeStore

    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print("usage: python -m vietnlp.platform.flows.acquisition_flow SOURCE_NAME [--query TEXT]", file=sys.stderr)
        return 2
    source_name = argv[0]
    query = argv[argv.index("--query") + 1] if "--query" in argv else None

    database_url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    bronze = BronzeStore.from_env()
    result = acquisition_flow(source_name, database_url, bronze, query=query)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Document the P1a source-registration + run workflow**

Append to `deploy/README.md`, at the end of the file:

```markdown
## P1a: registering and running an acquisition source

Before any source can be acquired, register it (corpus-scout should have
already vetted it — robots.txt, license, register fit):

\`\`\`
docker compose run --rm --entrypoint python agents -c "
from vietnlp.acquisition.sources import register_source
register_source(
    'postgresql://vietnlp:PASSWORD@postgres:5432/vietnlp',
    name='example-news-source',
    tier='news_gov_wiki',
    base_url='https://news.example.vn',
    license='cc-by',
    robots_policy='allowed',
)
"
\`\`\`

Then run it:

\`\`\`
make run-acquisition HOST=_59 REMOTE=vietnlp SOURCE=example-news-source
\`\`\`

`public_corpus` and `forum_qa_blog` sources need `--jsonl-path`/seed-URL
arguments the one-liner CLI above doesn't yet expose — call
`acquisition_flow` directly from a Python one-liner for those tiers until a
richer CLI exists.
```

- [ ] **Step 4: Sync, build, and run the offline gate**

```bash
tar czf - --exclude '.git' --exclude '__pycache__' --exclude '.env' --exclude 'deepseek.key' --exclude 'data' \
    src pyproject.toml tests deploy CLAUDE.md Makefile | ssh _59 'tar xzf - -C vietnlp'
ssh _59 'cd vietnlp/deploy && docker compose build agents'
ssh _59 'cd vietnlp/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests -q'
```

Expected: PASS. This plan added 0 (Task 1, renames existing tests/assertions
in place, no new test functions) + 1 (Task 2) + 6 (Task 3) + 7 (Task 4) + 2
(Task 5) + 5 (Task 6) + 5 (Task 7) + 5 (Task 8) + 5 (Task 9) = 36 new tests
on top of P0's 79 (the count after P0's own final fix round) = 115 total,
with the same live-dependency tests that were already self-skipping (4 DB +
2 MinIO from P0) still skipping — this plan adds no new self-skipping
tests, since every new offline test fakes its external dependency instead.

- [ ] **Step 5: Register one real test source and run acquisition live**

Pick one small, already-known-safe source for this proof (e.g. a single
Wikipedia article exported as a one-line JSONL file, or a real vetted news
domain with a narrow query) — this is a genuine live run against a real
public source, so keep it small and unambiguously within CLAUDE.md's
public-content-only guardrail.

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --entrypoint python agents -c "
from vietnlp.acquisition.sources import register_source
register_source(\"postgresql://vietnlp:PASSWORD@postgres:5432/vietnlp\", \"p1a-smoke-test\", \"public_corpus\", license=\"public-domain\")
"'
# create a tiny one-line JSONL smoke-test file on the server, then:
make run-acquisition HOST=_59 REMOTE=vietnlp SOURCE=p1a-smoke-test
```

Expected: `{'loaded': 1, 'dead_lettered': 0}`, and the object genuinely
exists in Bronze — confirm with:

```bash
ssh _59 'cd vietnlp/deploy && docker compose run --rm --entrypoint python agents -c "
from vietnlp.platform.storage.bronze import BronzeStore
store = BronzeStore.from_env()
print(store.client().list_objects(store.bucket, prefix=\"bronze/p1a-smoke-test/\", recursive=True).__class__)
for obj in store.client().list_objects(store.bucket, prefix=\"bronze/p1a-smoke-test/\", recursive=True):
    print(obj.object_name)
"'
```

- [ ] **Step 6: Commit the wiring changes**

```bash
git add Makefile deploy/.env.example deploy/README.md src/vietnlp/platform/flows/acquisition_flow.py
git commit -m "chore: wire make run-acquisition, document P1a secrets and source-registration workflow"
```

---

## Self-Review Notes

- **Spec coverage:** source vetting gate (§ Acquisition, Source vetting
  gate) — Task 3. Three acquisition-path tiers — Tasks 6, 7, 8, dispatched
  by Task 9. Author-identifier hashing — Task 4 (primitive), available to
  Tasks 7/8 wherever a source surfaces a structured author field.
  Per-source kill switch re-checked every retry — Task 9's `get_source`
  call happens fresh on every `acquisition_flow` invocation, which Prefect
  retries call fresh by construction (no cached `SourceRecord` carried
  across a retry). z.ai MCP integration — Task 5, including the honest
  "verify against live reality" step the spec's own uncertainty about the
  exact result shape requires. `sources.rate_limit_seconds` — Task 2.
  Fixture/registry naming resolution — Task 1.
- **Placeholder scan:** no TBD/TODO/FIXME. Task 5's Step 6 is the one place
  this plan asks an implementer to verify something empirically rather than
  handing over guaranteed-correct code — that is flagged explicitly as a
  named, load-bearing verification step with a clear fallback (fix the
  parsing to match reality, add a regression test), not a vague "handle
  this later."
- **Type consistency:** `SourceRecord`'s fields (Task 3) are used
  identically by every later task's `_source(**overrides)` test helper and
  by `acquisition_flow`'s tier dispatch. `DeadLetterSink = Callable[[tuple[
  dict, str]], None]` matches P0's Task 6 fix exactly, reused verbatim
  across Tasks 6, 7, 8. `bronze.put_record(record) -> str` is called
  identically (keyword-free, same field set: `source_id, url, fetched_at,
  http_status, robots_decision, content_type, raw_payload, license`) by
  all three loaders, matching `BronzeStore.put_record`'s actual P0
  signature exactly (confirmed by reading the current file, not from
  memory).
- **Known forward risk, not this plan's to fix:** `Agent.run()` in
  `platform/agents/registry.py` calls DeepSeek once per document, but
  `policy.py`'s routing table already documents `batch_size=20` (quality_
  score, language_register) and `batch_size=10` (pii_flag, boilerplate_
  check) as the intended cost-efficient call pattern for P1b's curation
  stages. Realizing that batching means either extending `Agent`/`registry.
  py` to support a batched call shape, or curation building its own batched
  prompt+parse logic around `AgentClient.run()` directly. This plan (P1a)
  never calls DeepSeek and is unaffected; it is flagged here so P1b's
  planning treats it as a real, already-known design question rather than
  rediscovering it mid-implementation.
