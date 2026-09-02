# Project 8: Serving API — Design

Compact skeleton — see `student-projects/01-word-seg-pos/spec.md` for the
full worked-example depth this compresses.

## Goal

Build a FastAPI service exposing `interfaces.serving.DocumentResponse`
(with nested `SentenceResponse`/`EntityResponse`) over the static,
offline fixture `tests/fixtures/serving/gold_fixture.json` — materialized
by running every other project's stub over the full 100-document fixture
corpus (see `tests/fixtures/generate_gold_fixture.py`). At minimum:

- `GET /documents/{id}` -> one `DocumentResponse`
- `GET /documents` -> a paginated list
- `GET /documents/{id}/entities` -> that document's entities

Design the exact route/query-param shape yourself; document it in
`spec.md`'s own extension (edit this file, or add an `API.md` in your
project directory) before implementing.

## Non-Goals

- A real Postgres-backed handler (P5's actual serving stage reads live
  Postgres; this project's scope is the API surface, contract, and
  correctness against the static fixture — swapping in a real DB
  connection later is explicitly out of scope for the 15 weeks).
- Authentication/authorization (not needed for an internal research
  service).

## The one hard invariant: UTF-8/diacritics round-trip

Per the plan's I/O contract table: **UTF-8/diacritics must round-trip
through JSON untouched.** FastAPI's default response encoding already
does this correctly (`ensure_ascii=False` behavior) — the trap is if you
add any manual `json.dumps(...)` call anywhere in your handler code
without passing `ensure_ascii=False`, which silently escapes every
non-ASCII character to a `\uXXXX` sequence. Test this explicitly: assert
a response body contains the literal diacritic characters, not escape
sequences.

## Testing

Required input classes: a document with entities, a document with zero
entities (a valid case, not an error — spans this happens to since the
NER stub only flags capitalized tokens), `degenerate` (a nonexistent
document id -> a proper 404, not a 500), `adversarial`.

Golden invariant (`tests/golden/test_serving_api_golden.py`, authored in
a later pass): `TestClient` returns exact fixture rows per endpoint,
offline, diacritics intact.
