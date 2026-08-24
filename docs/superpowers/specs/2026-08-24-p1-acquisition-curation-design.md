# P1: Acquisition + Curation — Design

Sub-project spec for VietNLP's P1 phase, argued from the whole-program design
(`docs/superpowers/specs/2026-08-23-vietnamese-nlp-platform-design.md`) and
bound by `CLAUDE.md`'s non-negotiable rules and guardrails. P0 (platform
bootstrap) is complete and merged to `main`; this spec covers the next phase:
turning acquisition + curation into a real, running pipeline that produces a
~100K-sentence Silver corpus.

## Goal

Acquire Vietnamese text from vetted public sources, clean and dedupe it, and
land it as a Silver-layer corpus that is genuinely re-derivable from Bronze
alone — with Postgres remaining a true projection, not a second source of
truth.

## What P0 already built (reused, not rebuilt)

- `BronzeStore` (`src/vietnlp/platform/storage/bronze.py`) — content-addressed
  MinIO storage, SHA-256 keyed, date-partitioned.
- The Postgres §4.3 schema (`src/vietnlp/platform/db/`), including
  `documents`, `sentences`, and `dead_letters`.
- The validate-then-dead-letter Prefect flow pattern
  (`src/vietnlp/platform/flows/bootstrap_flow.py`) — P1 replaces its stub
  projection with real curation logic, keeping the same shape.
- The 100-document fixture corpus (`tests/fixtures/corpus/fixture_corpus.jsonl`)
  as the offline golden-file substrate for every new stage's tests.
- `corpus-scout` and `curation-analyst` sub-agents (`.claude/agents/`),
  already defined, not yet exercised by any real pipeline.

## Architecture & Data Flow

```
corpus-scout vets source ──┐
                            ▼
              ACQUISITION (per source, on-demand)
   discovery (web-search-prime) / web-reader extraction /
   polite crawler / public corpus loaders
                            │
                            ▼
              BRONZE (existing, MinIO/Parquet,
                content-addressed, immutable)
                            │
              CURATION (periodic, over full Bronze pool)
   boilerplate strip → MinHash dedup (cross-source) →
   fastText lang-id → DeepSeek register classify →
   heuristic quality score (DeepSeek on borderline band) →
   regex PII scrub (DeepSeek fallback on ambiguous spans)
                            │
                            ▼
              SILVER (new, MinIO/Parquet,
                silver/{source}/{date}/*.parquet,
                mirrors Bronze's layout)
                            │
              curation-analyst reviews batch quality
                            │
                    PROJECTOR (new, small)
                            │
                            ▼
              Postgres `documents` / `sentences`
              (existing tables; now genuinely a
               projection, rebuildable by rerunning
               the projector over Silver)
```

Two new Prefect flows extend the pattern `bootstrap_flow.py` already proved:
`acquisition_flow` (one run per vetted source) and `curation_flow` (real
dedup/lang-id/quality/PII pipeline, same validate-then-dead-letter shape). A
third, much smaller piece — the projector — is the only code path allowed to
write to `documents`/`sentences`.

Both acquisition and curation are dispatched explicitly (`docker compose run
--rm --no-deps agents run <flow>`), never automatically — same discipline as
the rest of `platform/agents`.

## Acquisition (`acquisition/`)

### Source vetting gate

Before any source is crawled, `corpus-scout` (read-only, never fetches at
scale) checks `robots.txt`, license/ToS, and register fit, and produces a
source record written to Postgres's existing `sources` table (P0's
migration 0001 already defines `id, name, tier, base_url, license,
robots_policy, enabled` — this spec reuses that table rather than inventing
a parallel one; a small P1 migration adds the one column it's missing,
`rate_limit_seconds INT`).

**Reconciled with the deployed schema**: `sources.tier` is already
constrained to `news_gov_wiki | forum_qa_blog | social | public_corpus`, not
the `dataset|web|crawl` axis an earlier draft of this spec used. Those four
values map directly onto the three acquisition paths below, and the mapping
was clearly intentional in P0's schema design: `public_corpus` → the
dataset-loader path, `news_gov_wiki` → the web discovery+extraction path,
`forum_qa_blog` → the polite-crawl path, and `social` stays permanently
disabled — it's P6's domain, and the schema already reserves the value
without P1 ever needing to touch it.

This record is the authorization. The crawler refuses to run against any
`source.id` that is not `enabled` — the per-source kill switch and
rate-limit guardrails are structural, not conventions the code merely
follows. `acquisition_flow` re-reads the `enabled` flag at the start of
every task-level retry, not just once at flow start, so disabling a source
mid-run stops it within one retry interval.

### Three acquisition paths, one per source `tier`

- **`public_corpus`** — bulk downloaders for established public Vietnamese
  corpora (OSCAR/CC-100 Vietnamese subset, Wikipedia dumps, existing
  VLSP/UIT datasets). One-shot imports, license metadata attached
  per-record, no live crawling.
- **`news_gov_wiki`** — `web-search-prime` discovers candidate URLs under an
  approved source's domain; `web-reader` extracts clean text. Used for
  news/government/formal sources where search-based discovery fits.
- **`forum_qa_blog`** — a rate-limited `httpx` crawler for forums/Q&A sites
  named by corpus-scout, one token bucket per `source.id` refilled at the
  vetted `rate_limit_seconds`, for paginated sites where search-based
  discovery doesn't apply well.

All three paths converge on `BronzeStore.put_record(...)` — no new Bronze
interface needed.

### Author-identifier hashing

Per CLAUDE.md ("hash author identifiers at ingest; never persist raw
handles"), hashing happens at extraction time, before a record ever reaches
`put_record`. The raw handle never exists on disk.

## Curation (`curation/`)

`curation_flow` runs periodically over all Bronze records not yet promoted to
a Silver batch. Each stage is a `@task` chained inside one `@flow`, following
`bootstrap_flow.py`'s shape exactly: a stage failure dead-letters the record
with its exception (CLAUDE.md rule 4 — no silent drops) and the pipeline
continues.

1. **Boilerplate strip** — safety net for public-loader imports that skip
   `web-reader`'s extraction-time stripping.
2. **MinHash dedup (cross-source)** — shingled MinHash signatures computed
   over the *full accumulated* Bronze pool, not just the current run's new
   records, LSH-bucketed for near-duplicate lookup at 100K-doc scale. A
   document colliding above threshold with an already-promoted Silver
   document is dead-lettered as `duplicate`, with the dead-letter row
   recording which Silver document it duplicated.
3. **fastText lang-id** confirms Vietnamese-family text, including
   non-diacritic input (character-n-gram based, so reasonably robust to
   missing diacritics).
4. **DeepSeek register classification** (`deepseek-chat`, every surviving
   document) — `formal | informal | non_diacritic | teencode | mixed`. This
   locks in spec §4.2's `non_diacritic` naming as the one true term going
   forward (see Fixture Corpus Rename below).
5. **Heuristic quality score** (length, script ratio, boilerplate residue,
   lang-id confidence), `deepseek-chat` invoked only for the borderline band.
   Below-threshold documents are dead-lettered as `low_quality`.
6. **PII scrub** — regex first (Vietnamese phone/email/national-ID/address/
   @handle patterns), `deepseek-chat` fallback only on regex-ambiguous spans.
   Scrubbed spans become typed placeholders — `[PHONE]`, `[EMAIL]`, `[ID]`,
   `[ADDRESS]`, `[HANDLE]` for the regex-caught categories, `[PERSON]` for
   names the DeepSeek fallback catches — never bare deletions, so sentence
   structure survives for later tokenization.
7. **Silver write** — survivors go to `SilverStore.put_record(...)`.

`curation-analyst` reviews each batch's stats (dedup rate, register balance,
dead-letter reasons, quality-score distribution) before the batch is
considered promotable to the projector.

## Silver Storage & the Postgres Projector

**`SilverStore`** (`platform/storage/silver.py`) mirrors `BronzeStore`: same
content-addressing, same date-partitioned key layout
(`silver/{source_id}/{date}/{hash}.parquet`), but carries curation's output
fields (`register`, `quality_score`, `dedup_cluster_id`, `pii_scrubbed: bool`)
instead of Bronze's raw-fetch fields — plus `bronze_uri: str`, the original
Bronze object key each Silver record was derived from. This is required, not
optional: `documents.bronze_uri` already exists in P0's schema (`NOT NULL`),
so the projector needs Silver to carry that provenance pointer forward, not
just Silver's own key. `content_hash` computation and the date-partitioning
key logic are factored out of `bronze.py` into a shared
`platform/storage/_content_addressed.py` so both stores use one
implementation, not two copies.

**The projector** (`platform/db/silver_projector.py`) is the *only* code path
permitted to write to Postgres's `documents`/`sentences` tables — this is
where CLAUDE.md rule 3 ("Postgres is a projection... fix Gold, re-project")
becomes structurally true for Silver, not just Gold. It reads Silver Parquet
objects not yet projected (tracked via a `projected_at` marker, analogous to
`schema_migrations`), sentence-segments each document's `text` with a light
rule-based splitter (Vietnamese sentence-final punctuation + abbreviation
guards — not the real UD-parse pipeline, which is P2's job), and inserts —
populating `documents.bronze_uri` from the Silver record's carried-forward
field, `documents.source_id` by looking up the `sources` row by name, and
`documents.lang`/`register`/`quality_score` directly from Silver's own
fields. Rebuilding Postgres from scratch: drop `documents`/`sentences`,
reset the projection marker, rerun the projector over all of Silver — no
re-curation needed.

## Fixture Corpus Rename

The P0 fixture corpus (`tests/fixtures/corpus/fixture_corpus.jsonl`) and its
schema (`src/vietnlp/acquisition/fixture_schema.py`) use `khong_dau` as the
non-diacritic register value; spec §4.2 names it `non_diacritic`. This P1
plan's first task renames the value across the fixture data, the schema, and
`bootstrap_flow.py`'s consumers, so curation's real register classifier and
the fixture's known-good baseline use one name from day one — this was
flagged as an open naming mismatch in P0's final whole-branch review and is
resolved here before more code depends on either spelling.

## Testing

Follows the P0 pattern: the renamed fixture corpus is curation's offline
golden-file input. Every stage (dedup, lang-id, quality-score, PII-scrub)
gets a pure-logic unit test, plus one golden-file test asserting the fixture
corpus's known-good register/quality distribution survives curation
unchanged. DeepSeek-touching stages (register classification, quality-score
borderline band, PII fallback) get their calls mocked in the default offline
suite (same `respx`-style approach as the Fuseki admin tests), plus a
separate self-skipping live-DeepSeek test analogous to the live-DB/live-MinIO
pattern — `--no-deps` stays green and spend-free; a live run proves the real
calls work.

## Budget Sizing

Register classification hits every surviving document — the dominant cost
driver, since quality-score and PII-fallback only hit borderline bands.
Before P1 executes for real, size actual spend using `platform/agents`'s
existing `estimate` command against a realistic borderline-rate assumption,
checked against the $5/flow, $20/day, $200/total caps (CLAUDE.md rule 5:
caps hard-stop, they do not warn). If per-document register classification
threatens the total cap at 100K-document scale, the documented fallback is
downgrading it to heuristics-first-then-DeepSeek-on-borderline — the same
shape already used for quality scoring.

## Non-Goals (explicitly out of scope for P1)

- Real word segmentation, POS tagging, UD parsing, NER, coreference — P2.
- Ontology instances, ontology alignment — P3.
- FOL logical forms, entity resolution — P4.
- Serving API, HF dataset export, benchmark harness — P5.
- Social acquisition (Facebook/Threads/TikTok) — P6, stays disabled.

## Open Risks Carried Into the Implementation Plan

- Exact MinHash threshold and shingle size need empirical tuning against the
  fixture corpus plus a small real sample — not fixed in this spec, decided
  during implementation with a documented rationale.
- fastText model choice/version and its licensing need a quick check during
  planning (not yet vetted).
- Cross-source dedup at LSH scale needs a decision on where the LSH index
  lives (in-process per curation run vs. a small persistent index) — deferred
  to the implementation plan.
