# Project 8: Serving API — 15-Week Implementation Plan

Compact skeleton — see `student-projects/01-word-seg-pos/plan.md` for the
full worked-example depth this compresses.

**Gate:** `student-projects/_gate/run_gate.sh 08-serving` — note this
project's `gate.yaml` has no `producers` (see its own comment for why);
your grading is almost entirely the golden `TestClient` test plus your
own suite.

## Global Constraints

Same as Project 1's. Your code: `src/vietnlp/serving/` (an `app.py` or
similar FastAPI entry point, plus any handler modules you split out).

## Task breakdown

- [ ] **Weeks 1-2 — API design.** Read `interfaces/serving.py` in full.
  Design your exact routes and query parameters; write them down before
  coding.
- [ ] **Weeks 3-4 — Skeleton FastAPI app.** Wire `GET /documents/{id}`
  against `tests/fixtures/serving/gold_fixture.json` loaded into memory
  (or SQLite, your choice — it's a static fixture either way).
- [ ] **Weeks 5-6 — Remaining endpoints + pagination.**
- [ ] **Weeks 7-8 — UTF-8 round-trip verification.** Write the explicit
  diacritics-round-trip test from spec.md; fix any manual
  `json.dumps` call that doesn't pass `ensure_ascii=False`.
- [ ] **Weeks 9-10 — Error handling.** 404 for a nonexistent document id;
  never a bare 500 for an expected "not found" case.
- [ ] **Weeks 11-12 — Golden test.**
  `tests/golden/test_serving_api_golden.py` once authored.
- [ ] **Weeks 13-14 — `TESTING.md` + full gate pass.**
- [ ] **Week 15 — Submission.**
