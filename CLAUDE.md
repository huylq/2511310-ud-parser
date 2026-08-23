# VietNLP — Vietnamese Language Understanding Platform

Charter for the whole program. Read this first every session. Phase-specific detail
lives in `docs/superpowers/specs/`.

## What this is

A production data platform that turns Vietnamese text from the open web into a
layered, queryable language resource: cleaned corpus → morpho-syntactic annotation →
treebank → ontology → first-order logical forms → probabilistic entity knowledge base.

The deliverable is **not a chatbot**. It is a database plus a service that any
Vietnamese NLP task can build on.

Three consumable faces, all projected from one source of truth:

| Face | Store | Consumer |
|---|---|---|
| Corpus + annotations | Postgres 16 + pgvector | SQL, Python client, FastAPI |
| Knowledge graph | Apache Jena Fuseki (OWL 2 / SPARQL) | Reasoning, entity lookup |
| Dataset releases | HuggingFace Hub | External researchers, training |

## Non-negotiable rules

1. **Bronze is immutable.** Raw fetches are content-addressed and never edited.
   Every downstream artifact must be reproducible from Bronze alone.
2. **DeepSeek output never enters Gold unvalidated.** The model proposes; rules,
   type checks, or humans dispose. An unvalidated model guess in the treebank or
   ontology destroys the credibility of the whole resource.
3. **Postgres and Fuseki are projections.** Never hand-edit them. Fix Gold, re-project.
4. **No silent drops.** A document that fails a stage goes to the dead-letter
   partition with its exception. Never `except: pass`.
5. **Budget caps hard-stop.** DeepSeek spend limits abort the flow, they do not warn.
6. **Social acquisition is off** until P6 is explicitly authorized. See Guardrails.

## Architecture

```
discovery (web-search-prime) ─┐
web-reader extraction         ├─→ BRONZE (MinIO/Parquet, immutable, content-hashed)
polite HTTP crawler           │        │
public corpus loaders        ─┘        ↓
                                   curation: boilerplate, MinHash dedup, language ID,
                                   PII scrub, DeepSeek quality score
                                       ↓
                                    SILVER (clean, segmented documents)
                                       ↓
                          linguistics: word seg → POS → UD parse → NER → coref
                          (underthesea / VnCoreNLP / PhoBERT baseline,
                           DeepSeek refinement, disagreement routed to humans)
                                       ↓
                                     GOLD (annotation layers + curated treebank
                                           + ontology instances + logical forms)
                                       ↓
                    ┌──────────────────┼──────────────────┐
                    ↓                  ↓                  ↓
              Postgres+pgvector    Fuseki (OWL)      HF dataset exports
                    └──────────→ FastAPI service ←───────┘
```

### Layers

- **Bronze** — raw payload + fetch metadata (URL, timestamp, robots decision, content
  hash, source tier). Parquet on MinIO, partitioned `source/date`.
- **Silver** — boilerplate-stripped, deduped, language-verified, PII-scrubbed,
  sentence-segmented, quality-scored documents.
- **Gold** — tokens, word segmentation, POS, UD dependencies, NER, coreference,
  FOL logical forms, curated treebank, ontology individuals.
- **Serving** — Postgres, Fuseki, HF exports. All regenerable.

DuckDB reads Parquet directly for ad-hoc analysis; do not load the warehouse for that.

### Modules

| Module | Responsibility |
|---|---|
| `platform/` | compose stack, Prefect flows, config, migrations, secrets, CI |
| `acquisition/` | discovery, extraction, crawling, public-corpus loaders |
| `curation/` | dedup, language ID, quality scoring, PII scrubbing |
| `linguistics/` | word segmentation, POS, UD parsing, NER, coreference |
| `treebank/` | UD v2 schema, adjudication workflow, IAA, CoNLL-U export |
| `ontology/` | OWL 2 ontology, external alignment, reasoner consistency checks |
| `semantics/` | UD → neo-Davidsonian FOL logical forms, type checking |
| `oupm/` | open-universe entity resolution (MCMC over unknown entity count) |
| `serving/` | FastAPI endpoints, model versioning |
| `export/` | HF datasets + cards, OWL dumps, benchmark harness |

Each module owns its stage, exposes a typed Python API and a CLI entry point, and
talks to neighbours only through layer artifacts — never by importing internals.

## Stack

- Python **3.11** via pyenv. The system Python 3.9 is too old; do not use it.
- Docker (or colima) — **hard prerequisite**, not currently installed on this machine.
- Postgres 16 + pgvector · MinIO · Apache Jena Fuseki · Prefect 3 · FastAPI
- Java 21 (present) for VnCoreNLP
- pandera for layer schema contracts · pytest · DuckDB for analysis

## Vietnamese-specific notes

- Vietnamese orthography is **syllable-segmented, not word-segmented**. Word
  segmentation is a real upstream task; never assume whitespace tokens are words.
- Preserve diacritics exactly. Normalize to **NFC** at ingest. Tone-mark placement
  varies by input method (`hoà` vs `hòa`) — normalize, but record the original form.
- Detect and flag non-diacritic Vietnamese ("khong dau") and teencode; they are a
  distinct register, not noise to discard.
- Follow **UD v2**, aligned with UD_Vietnamese-VTB, so the treebank is comparable to
  existing work.
- Benchmark against VLSP shared tasks, UIT-VSFC, ViQuAD.

## Working agreements

- Brainstorm → spec → plan → implement. Specs live in `docs/superpowers/specs/`.
- TDD. Golden-file tests for every annotation stage. A committed ~100-document
  fixture corpus keeps the full pipeline testable without network or API spend.
- Contract tests at every layer boundary; a schema change is a breaking change.
- The benchmark harness is a regression gate, not a report.
- Docs and code comments in English.
- Secrets from environment or `deepseek.key`; never commit them, never log them.

## Guardrails

**Acquisition ethics — binding.** Public content only. Respect `robots.txt` and
per-host rate limits. Hash author identifiers at ingest; never persist raw handles.
No profile-level harvesting. Per-source kill switch. Honor opt-out requests.

**Never build:** credentialed login automation, anti-bot evasion, or any access to
private or login-walled content.

**P6 social acquisition (Facebook / Threads / TikTok) is deferred and ships
disabled.** It violates those platforms' ToS and touches personal data under
Vietnam's PDPD (13/2023/NĐ-CP). Enabling it requires setting an explicit
authorization flag that names the legal basis, recorded in the repo. Until then,
colloquial register comes from forums and Q&A sites.

## Phases

| Phase | Goal | Status |
|---|---|---|
| P0 | Platform bootstrap: Docker, compose stack, schemas, config, DeepSeek client | not started |
| P1 | Acquisition + curation → ~100K-sentence Silver corpus | not started |
| P2 | Linguistic core + treebank | not started |
| P3 | Ontology + entity linking | not started |
| P4 | FOL semantics + OUPM entity resolution | not started |
| P5 | Serving API, HF export, benchmark suite | not started |
| P6 | Social acquisition — **gated, off by default** | deferred |

Phase 1 target scale is a **pilot: ~100K sentences**. Design for more, do not build
for more.

## Commands

```
make deploy        # sync + build + test + start the stack on server _59
make test          # pytest inside the container (offline, no API spend)
make agents        # list sub-agents and the model each one uses
make routes        # the task -> model cost table
make spend         # DeepSeek spend against the flow/daily/total caps
make cache         # cache hit rates per task and prompt version
make tunnel        # forward postgres/minio to localhost
make ps | logs | down
```

Populated during P1-P5: `make migrate`, `make bench`, `make export`.

## Sub-agents

Two layers, both tiered so routine work does not run on an expensive model.

**Development (`.claude/agents/`)** — specialists invoked during a session:

| Agent | Model | Use |
|---|---|---|
| `corpus-scout` | haiku | Source discovery, robots/licence vetting |
| `cost-auditor` | haiku | Spend, cache rates, routing audits |
| `curation-analyst` | sonnet | Silver-layer data quality |
| `vietnamese-linguist` | sonnet | Word segmentation, POS, UD review |
| `platform-engineer` | sonnet | Docker, migrations, deployment |
| `treebank-adjudicator` | opus | Contested gold-treebank rulings |
| `ontology-engineer` | opus | OWL 2 modelling, reasoner inconsistency |
| `semantics-engineer` | opus | UD -> FOL, scope, type checking |
| `oupm-modeler` | opus | Open-universe entity resolution, MCMC |

Opus is reserved for decisions that are expensive to get wrong and are not caught
downstream. Everything with a mechanical validator runs cheaper.

**Runtime (`src/vietnlp/platform/agents/`)** — the pipeline's model access:

- `policy.py` — the task -> model table. Callers name a *task*, never a model.
  An unknown task raises; there is no default, because a default model is a
  silent bill.
- `budget.py` — SQLite spend ledger on a volume. Checks affordability *before*
  each call and aborts on breach.
- `cache.py` — responses keyed by task + prompt version + model + content hash.
  **Bump `prompt_version` on any prompt edit**, or the cache serves answers from
  the old prompt forever.
- `registry.py` — sub-agent definitions. An `Agent` cannot be constructed without
  a validator, so rule 2 is enforced structurally rather than by convention.
- `client.py` — the only code that spends money. Call order is load-bearing:
  cache -> budget -> API -> record -> store.

`deepseek-reasoner` is reserved for `semantic_parse`, `ontology_induction`,
`parse_adjudication` and `entity_disambiguation` — the tasks whose errors no cheap
validator can detect. Bulk curation stays on `deepseek-chat`.

## Deployment

The stack runs on server `_59` (`118.69.218.59`), a **shared** 8-vCPU/15-GB host
with ~3-4 GB free, no GPU, and a dozen unrelated containers. Every service has a
hard memory limit; ports use the free 6040-6049 block and bind to 127.0.0.1 only.
See `deploy/README.md`.
