"""Contract for Project 8 (Serving API) -- the FastAPI response envelope.

Nothing downstream consumes Project 8's output, so unlike Projects 1-7
these dataclasses carry no `source` field: Project 8 receives every other
project's output already materialized into a static fixture
(`tests/fixtures/serving/gold_fixture.json`, built by
`tests/fixtures/generate_gold_fixture.py` running the real stub pipeline
over the fixture corpus and projecting the result into the
migration-0001 shape) and simply serves rows back out of it.
Provenance lives on the *interior* objects being served
(`interfaces.ner.NamedEntity.source` etc.), not on the response envelope
wrapping them.

Mirrors `documents`, `sentences`, `entities`, `mentions` in
`platform/db/migrations/0001_core_schema.sql`. Field names match column
names exactly so a real FastAPI handler can construct these with
`DocumentResponse(**row)` off a DB cursor with no renaming step. Per the
plan's I/O contract table, the golden invariant is that `TestClient`
returns exact fixture rows per endpoint with UTF-8/diacritics round-tripped
through JSON untouched -- which requires the handler serialize with
`json.dumps(..., ensure_ascii=False)` / FastAPI's default UTF-8 response,
never the `ensure_ascii=True` default of bare `json.dumps`.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import pandera as pa

SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class SentenceResponse:
    id: int
    document_id: int
    idx: int
    text: str


@dataclass(frozen=True)
class EntityResponse:
    id: int
    canonical_name: str
    ontology_class: str | None
    wikidata_qid: str | None
    posterior: float | None


@dataclass(frozen=True)
class DocumentResponse:
    id: int
    content_hash: str
    url: str | None
    lang: str | None
    register: str | None
    quality_score: float | None
    sentences: tuple[SentenceResponse, ...] = ()
    entities: tuple[EntityResponse, ...] = ()


# Flat, one-row-per-document shape for the gate's schema-conformance check --
# pandera validates tabular rows, not the nested `sentences`/`entities` tuples
# directly, so nested collections are summarized to counts here. The nested
# shape itself is exercised by the golden-file `TestClient` test instead.
DOCUMENT_SCHEMA = pa.DataFrameSchema(
    {
        "id": pa.Column(int, pa.Check.gt(0)),
        "content_hash": pa.Column(str, pa.Check.str_length(min_value=1)),
        # coerce=True: a single-document DataFrame whose only quality_score
        # value is None gets pandas dtype "object", not float64 -- nullable=True
        # alone does not fix that dtype mismatch. coerce makes pandera cast the
        # column before checking, which handles the single-row-all-None case
        # that `validate_document_response` (one document at a time) hits
        # whenever a document has not yet been quality-scored.
        "quality_score": pa.Column(float, pa.Check.in_range(0.0, 1.0), nullable=True, coerce=True),
        "sentence_count": pa.Column(int, pa.Check.ge(0)),
        "entity_count": pa.Column(int, pa.Check.ge(0)),
    },
    strict=False,
)


def to_row(doc: DocumentResponse) -> dict:
    return {
        "id": doc.id,
        "content_hash": doc.content_hash,
        "url": doc.url,
        "lang": doc.lang,
        "register": doc.register,
        "quality_score": doc.quality_score,
        "sentence_count": len(doc.sentences),
        "entity_count": len(doc.entities),
    }


def validate_document_response(doc: DocumentResponse) -> DocumentResponse:
    """Raises `ValueError`/`pandera.errors.SchemaError` if: any nested
    `EntityResponse.posterior` falls outside [0, 1]; nested sentence `idx`
    values are not unique; or the flattened row fails `DOCUMENT_SCHEMA`."""
    idxs = [s.idx for s in doc.sentences]
    if len(idxs) != len(set(idxs)):
        raise ValueError(f"DocumentResponse {doc.id}: duplicate sentence idx values {idxs}")
    for e in doc.entities:
        if e.posterior is not None and not 0.0 <= e.posterior <= 1.0:
            raise ValueError(f"DocumentResponse {doc.id}: entity {e.id} posterior {e.posterior} outside [0,1]")
    DOCUMENT_SCHEMA.validate(pd.DataFrame([to_row(doc)]), lazy=False)
    return doc
