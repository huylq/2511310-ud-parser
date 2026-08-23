# VietNLP Platform — Design Spec

**Date:** 2026-08-23
**Status:** Approved
**Scope:** Program-level architecture. Each phase gets its own spec and implementation plan.

## 1. Problem

Vietnamese NLP work repeatedly rebuilds the same substrate: scrape text, clean it,
segment words, tag it, and only then get to the actual research. Existing resources are
fragmented across formats, licenses, and quality levels, and almost none carry a
semantic or ontological layer.

This project builds that substrate once, as a production data platform, and exposes it
three ways: a relational corpus database, an OWL knowledge graph, and versioned
HuggingFace dataset releases.

**Out of scope:** training a generative Vietnamese LLM. The platform produces the
data and services such a model would consume or be evaluated against.

## 2. Goals and success criteria

| Goal | Success criterion |
|---|---|
| Reusable corpus | ~100K Silver sentences, deduped, quality-scored, provenance-traceable to Bronze |
| Treebank | ≥5K gold UD v2 sentences, inter-annotator κ ≥ 0.80 on POS, LAS agreement ≥ 90% |
| Ontology | Reasoner-consistent OWL 2 ontology, ≥500 curated classes, sampled alignment precision ≥ 0.90 vs Wikidata |
| Semantics | Logical forms for the gold treebank; ≥85% type-check against ontology signatures |
| Entity KB | Cross-document entity clusters with posterior confidence; B³ F1 ≥ 0.75 on a held-out set |
| Service | FastAPI endpoints for the full stack, p95 < 500 ms on single-sentence requests |
| Reproducibility | Every Serving artifact regenerable from Bronze by a single command |

## 3. Architecture decisions

### 3.1 Full data platform (chosen over Postgres-only)

The user selected a full platform: object storage, an orchestrator, and containerized
services. Cost: Docker is a hard prerequisite and is not installed on the target
machine. Benefit: the pilot's structure survives a 100× scale-up without a rewrite,
and provenance is a first-class artifact rather than a column.

**Components:** MinIO (S3-compatible object storage) · Postgres 16 + pgvector
(serving warehouse) · Apache Jena Fuseki (OWL 2 / SPARQL) · Prefect 3 (orchestration)
· FastAPI (serving) · DuckDB (ad-hoc Parquet analysis, no server).

**Port allocation.** This machine already runs a Homebrew Postgres 16 on 5432. The
containerized warehouse binds **5433** to avoid a silent connection to the wrong
database; MinIO 9000/9001, Fuseki 3030, Prefect 4200, FastAPI 8000. All are set in
`.env` and read from config, never hardcoded.

**Prefect over Airflow.** Both are real orchestrators; Prefect 3 is Python-native,
runs its server and workers without a scheduler/executor split, and expresses
retry/backoff/caching policy as decorators on ordinary functions. Airflow's operational
weight buys nothing at pilot scale.

### 3.2 Medallion layering with an immutable Bronze

Bronze holds the raw payload and fetch metadata, content-addressed by SHA-256 of the
payload. Nothing rewrites it. Silver and Gold are derived and disposable — a bug in
curation is fixed by re-running curation, not by patching records.

This is what makes the resource defensible: any annotation can be traced to the exact
bytes fetched from a URL at a timestamp, under a recorded robots decision and license.

### 3.3 Projections, not copies

Postgres and Fuseki are *projections* of Gold. They are rebuilt, never hand-edited.
This eliminates the class of bug where the graph and the table disagree and nobody
knows which is right.

### 3.4 DeepSeek proposes, validation disposes

Four uses, each with a validation gate:

| Use | Validation gate |
|---|---|
| Document quality scoring | Calibrated against a human-scored sample; scores are metadata, never filters applied blind |
| Annotation bootstrapping | Rule checks + baseline-model agreement; disagreements routed to human adjudication |
| Semantic parsing | Logical form must type-check against ontology predicate signatures or it is rejected |
| Ontology induction | Proposals enter a staging graph; promotion requires human curation + reasoner consistency |

No model output reaches Gold without passing its gate.

## 4. Data contracts

### 4.1 Bronze record (Parquet, partitioned `source/date`)

```
content_hash: str          # sha256 of raw_payload, primary identity
source_id: str
url: str
fetched_at: timestamp
http_status: int
robots_decision: str       # allowed | disallowed | no_robots
content_type: str
raw_payload: bytes
license: str
```

### 4.2 Silver record

```
content_hash: str          # inherited, links to Bronze
text: str                  # NFC-normalized, boilerplate removed
lang: str                  # ISO code from language ID
lang_confidence: float
register: str              # formal | informal | non_diacritic | teencode | mixed
quality_score: float       # 0..1
dedup_cluster: str         # MinHash cluster id
sentences: list[{idx, text, char_start, char_end}]
pii_scrubbed: bool
```

### 4.3 Postgres serving schema (core tables)

```sql
sources(id, name, tier, base_url, license, robots_policy, enabled)
documents(id, content_hash UNIQUE, source_id, url, fetched_at, lang,
          register, quality_score, bronze_uri)
sentences(id, document_id, idx, text, char_start, char_end)
tokens(id, sentence_id, idx, form, syllables, lemma, upos, xpos,
       feats, head, deprel, misc, run_id)
annotation_runs(id, stage, engine, engine_version, prompt_version,
                started_at, finished_at, status)
entities(id, canonical_name, ontology_class, wikidata_qid, posterior)
mentions(id, sentence_id, token_start, token_end, entity_id, confidence)
logical_forms(id, sentence_id, form_sexp, predicates, type_checked, run_id)
embeddings(sentence_id, model, vector vector(768))
dead_letters(id, stage, content_hash, error, payload_uri, occurred_at)
```

Every annotation row carries `run_id`. Competing annotations of the same sentence from
different engines coexist; the promoted layer is selected by run, not by deletion.

Schema contracts are enforced with `pandera` at each layer boundary. A schema change is
a breaking change and requires a migration.

## 5. Linguistic pipeline

### 5.1 Vietnamese-specific handling

Vietnamese orthography separates **syllables**, not words: `sinh viên` ("student") is
one word, two syllables. Whitespace tokens are never assumed to be words; word
segmentation is an explicit upstream stage, and `tokens.syllables` retains the
underlying syllable sequence.

Text is NFC-normalized at ingest. Tone-mark placement varies by input method
(`hoà` / `hòa`); the normalized form is stored and the original retained in Bronze.
Non-diacritic Vietnamese and teencode are tagged as registers, not discarded — they
are the colloquial signal the corpus otherwise lacks with social sources deferred.

### 5.2 Stages

Sentence segmentation → word segmentation → POS → UD v2 dependency parse → NER →
coreference. Baselines from underthesea, VnCoreNLP (Java 21), and PhoBERT-based
taggers run first; DeepSeek refines; where baseline and DeepSeek disagree above a
threshold, the sentence is routed to human adjudication and becomes treebank candidate
material. Annotation follows UD v2 aligned with UD_Vietnamese-VTB so the treebank is
comparable to published work.

## 6. Ontology and logic layers

### 6.1 Ontology

OWL 2 DL, authored with `owlready2`, consistency-checked with HermiT before any
promotion. A small upper ontology (Entity, Event, Agent, PhysicalObject, Place,
Organization, TimeInterval, Proposition) with Vietnamese domain concepts beneath it,
aligned to Wikidata QIDs, DBpedia-vi, and Vietnamese WordNet where those exist.
Alignment is recorded with provenance and a confidence, not asserted as identity.

### 6.2 First-order logical forms

Neo-Davidsonian event semantics: events are reified, roles are binary predicates.

*Nam mua một cuốn sách ở Hà Nội.* ("Nam bought a book in Hanoi.")

```
(exists (e x)
  (and (buy e)
       (agent e nam_1)
       (theme e x)
       (book x)
       (location e hanoi_1)
       (past e)))
```

Predicate signatures come from the ontology (`buy: Event`, `agent: Event × Agent`,
`theme: Event × PhysicalObject`), so a parse asserting `agent(e, hanoi_1)` fails its
type check and is rejected. Quantifier scope is stored scope-underspecified with a
preferred reading recorded separately, rather than forcing a single scoping at parse
time.

### 6.3 Open-universe entity resolution

The number of real-world entities behind a corpus of mentions is unknown — the defining
condition for an open-universe probability model. The generative model:

```
#Entity          ~ CRP(α)                     # unknown cardinality
type(e)          ~ Categorical(ontology classes)
canonical(e)     ~ NameModel(type(e))
entity(m)        ~ CRP assignment              # which entity a mention refers to
surface(m)       ~ NoisyName(canonical(entity(m)))
```

The `NoisyName` channel is Vietnamese-specific: given-name-only reference (*Nguyễn Văn
Nam* → *Nam*), diacritic-stripped variants (*Nam* / *nam*), honorific prefixes
(*anh/chị/ông/bà/em*), and family-name ambiguity — roughly 40% of Vietnamese people
share the surname *Nguyễn*, so surname match is near-worthless evidence and the model
must weight given names and context accordingly.

Inference: Metropolis-Hastings over the mention partition with split-merge moves.
Output is clusters with posterior confidence; only clusters above a threshold project
to Fuseki, while full posteriors stay in Postgres.

## 7. Error handling

Prefect retries with exponential backoff on transient failures. A document that fails a
stage is written to `dead_letters` with its exception and payload URI — never dropped
silently. Writes are idempotent via content addressing, so re-runs are safe. The
DeepSeek client enforces per-flow budget caps that **abort** the flow on breach, caches
responses by `content_hash + prompt_version`, and never logs key material.

## 8. Testing and evaluation

- pytest, offline, against a committed ~100-document fixture corpus
- golden-file tests per annotation stage
- pandera contract tests at layer boundaries
- one end-to-end integration test through the full pipeline
- benchmark harness as a **regression gate**:

| Task | Benchmark | Metric |
|---|---|---|
| Word segmentation | VLSP 2013 | F1 |
| POS tagging | VLSP 2013 | accuracy |
| NER | VLSP 2016/2018 | F1 |
| Dependency parsing | UD_Vietnamese-VTB | UAS / LAS |
| Sentiment | UIT-VSFC | macro-F1 |
| Reading comprehension | ViQuAD | EM / F1 |
| Semantic parsing | held-out gold set | exact match + predicate-argument F1 |
| Entity resolution | held-out gold clusters | B³ / CEAF / MUC |

## 9. Ethics and legal

Public content only. `robots.txt` and per-host rate limits respected. Author
identifiers hashed at ingest; raw handles never persisted. No profile-level harvesting.
Per-source kill switch. Opt-out requests honored.

**Never built:** credentialed login automation, anti-bot evasion, access to private or
login-walled content.

**P6 social acquisition is deferred and ships disabled.** Facebook/Threads/TikTok
scraping violates those platforms' terms of service and touches personal data governed
by Vietnam's PDPD (Decree 13/2023/NĐ-CP). Enabling it requires an explicit
authorization flag naming the legal basis, recorded in the repository. Until then,
colloquial register is sourced from forums and Q&A sites.

## 10. Phases and exit criteria

| Phase | Deliverable | Exit criterion |
|---|---|---|
| P0 | Platform bootstrap | `make up` brings the stack healthy; `make test` green; DeepSeek client with budget caps |
| P1 | Acquisition + curation | ~100K Silver sentences, dedup rate reported, quality scores calibrated against human sample |
| P2 | Linguistic core + treebank | Full annotation pipeline; ≥5K gold UD sentences at target IAA |
| P3 | Ontology + entity linking | Reasoner-consistent ontology ≥500 classes; mentions linked with confidence |
| P4 | Semantics + OUPM | Logical forms for gold treebank ≥85% type-checked; entity clusters at B³ F1 ≥ 0.75 |
| P5 | Serving + export | FastAPI endpoints live; HF release with dataset cards; benchmark harness gating CI |
| P6 | Social acquisition | **Gated.** Not started without recorded authorization |

### Model output that cannot be trusted: character offsets

Verified against the live API during deployment: asking the model for character
offsets into Vietnamese text returns spans that are wrong by a few characters
(`Đại học Quốc gia Hà Nội` reported at 8, actually at 10). LLMs do not count
characters reliably and diacritics worsen it.

The pipeline therefore asks the model only to *name* entities, copying their text
exactly, and locates the spans locally by search. This keeps the anti-hallucination
guarantee — an entity absent from the source cannot be located, so it is rejected —
while removing a task the model cannot perform. Apply the same principle elsewhere:
never ask a model for a value that can be computed deterministically from its own
output.

## 11. Risks

| Risk | Mitigation |
|---|---|
| Docker not installed | P0 blocker, resolved first; colima acceptable |
| System Python 3.9 too old | pyenv-managed 3.11 pinned in P0 |
| DeepSeek cost overrun | Per-flow hard budget caps; response caching; quality scoring runs on samples before full corpus |
| **P4 semantic parsing exceeds the total budget** | Measured on the deployed stack: `semantic_parse` on `deepseek-reasoner` costs ~$0.0018/sentence, so the full 100K pilot is **~$465** against a $200 total cap. The cap would hard-stop P4 mid-flow. Decide before P4 starts: parse a stratified sample (~10-20K sentences) rather than the whole corpus, or raise the cap deliberately. Bulk curation is not the problem — quality scoring and register labelling are each under $1 for the same 100K. |
| Annotation quality too low to be a credible resource | IAA thresholds as phase exit criteria; DeepSeek never writes Gold directly |
| Scope creep across five subsystems | Phase gates; one spec and one plan per phase |
| Legal exposure from social data | P6 deferred and disabled; guardrails binding on all phases |
| Ontology drifts from corpus reality | Induction proposals grounded in corpus term clusters; alignment precision sampled each phase |

## 12. Next step

Write the P0 implementation plan: Docker prerequisite, compose stack, Postgres schema
and migrations, MinIO buckets, Fuseki dataset, Prefect deployment, config and secrets
handling, DeepSeek client with budget ledger, fixture corpus, and the test harness.
