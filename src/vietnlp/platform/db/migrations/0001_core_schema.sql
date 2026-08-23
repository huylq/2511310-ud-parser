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
