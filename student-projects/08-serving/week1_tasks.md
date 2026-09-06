# Week 1 Tasks — Project 8: Serving API

**Branch:** `student/08-serving`
**This week's scope:** the first half of `plan.md`'s "Weeks 1-2 — API design"
task. Reading + research + a documented route design, finalized in Week 2
before Weeks 3-4's skeleton FastAPI app. **No code under `src/vietnlp/...`
yet.**

Note: unlike most of the other projects, your Week 1 deliverable is not
called `DESIGN.md` — `project.md`'s "Required products" already names it
`API.md` (or a `spec.md` extension). Use that name so you don't end up
maintaining two documents that say the same thing.

## Day 1 — Environment setup

1. Clone and check out your branch (fork first if you lack push access — see
   `project.md`'s "Contributing on GitHub"):
   ```
   git clone git@github.com:phunghx/VietnamesModel.git
   cd VietnamesModel && git checkout student/08-serving
   ```
2. Set up your environment:
   ```
   python3.11 -m venv .venv && source .venv/bin/activate
   pip install -e ".[dev]"
   ```
3. Confirm the inherited suite is green: `pytest tests -q`. Fails on a clean
   checkout → flag it to the professor.

## Day 1-2 — Required reading, in this exact order

1. `student-projects/08-serving/spec.md` — your goal, the three minimum
   endpoints, and the one hard invariant (UTF-8/diacritics round-trip).
2. `student-projects/08-serving/plan.md` — the 15-week breakdown.
3. `student-projects/08-serving/README.md` — quickstart + checklist.
4. `student-projects/08-serving/project.md` — your exact contract: target
   endpoints, owned/forbidden paths, completion criteria. Read "You must
   not" twice — the gate checks scope mechanically. Note this project's
   `gate.yaml` has **no `producers`** (the `interfaces.serving` objects carry
   no `source` field) — your grading is almost entirely the golden
   `TestClient` test plus your own suite, so get the route contract right
   now.
5. `src/vietnlp/interfaces/serving.py` — **in full.** This is the frozen
   `DocumentResponse`/`SentenceResponse`/`EntityResponse` contract your API
   must serialize.
6. `tests/fixtures/serving/gold_fixture.json` — open it and actually look at
   its shape: top-level structure, per-document fields, per-sentence fields,
   per-entity fields. This is your entire data source; know its shape cold
   before you design a single route.
7. If you're not already comfortable with FastAPI: read its official
   quickstart/tutorial on path parameters, query parameters, and response
   models — you'll design against these concepts today and tomorrow.

## Day 2-4 — Research task

1. **Route and query-param shape** — research common REST pagination
   patterns (page-number + page-size vs. cursor-based) and pick one for
   `GET /documents`.
2. **The UTF-8/diacritics trap** — research exactly why FastAPI's default
   JSON response encoding preserves non-ASCII characters correctly, and what
   specifically breaks it: any manual `json.dumps(...)` call in your handler
   code that omits `ensure_ascii=False` silently escapes every diacritic to
   a `\uXXXX` sequence. Decide now that you will never hand-roll JSON
   serialization in a handler — let FastAPI's response model do it.
3. **Error-response shape** — research how to return a proper `404` for a
   nonexistent document id in FastAPI (vs. letting an unhandled `KeyError`
   produce a bare `500`), since `spec.md`'s Non-Goals list this as a hard
   requirement, not a nice-to-have.

## Day 3-5 — Design your exact routes

Work through, for each of the three minimum endpoints, exactly:

- `GET /documents/{id}` — path param type, response model, 404 behavior for
  a nonexistent id.
- `GET /documents` — query params (page/limit or cursor — your choice, but
  state it precisely: names, types, defaults, max page size if any),
  response shape (does it wrap results in an envelope with pagination
  metadata, or return a bare list?).
- `GET /documents/{id}/entities` — response shape for a document with
  entities, and explicitly, response shape for a document with **zero**
  entities (a valid case per `spec.md`, not an error — don't design a 404 or
  empty-error response for this case).

For each route, work out one example request and its example response,
using a real document id and its real fields from `gold_fixture.json` — not
a hypothetical.

## Deliverable: `student-projects/08-serving/API.md`

Create this file (or extend `spec.md` directly — your choice, `project.md`
accepts either, but pick one and don't duplicate). It must contain:

- For each of the three routes: method, path, query params (name, type,
  default), response shape, and one worked example request/response pair
  using real `gold_fixture.json` data.
- Your pagination scheme and why you picked it.
- Your 404 behavior for a nonexistent document id, stated precisely (status
  code, response body shape).
- Your zero-entities response shape (still a `200`, an empty list — not an
  error).
- A short note on how you'll guarantee the UTF-8/diacritics invariant (i.e.
  "we rely on FastAPI's default response encoding and never call
  `json.dumps` by hand in a handler").

## Self-check before you call Week 1 done

- [ ] I can state the exact response shape for all three routes without
      looking at my notes.
- [ ] I've designed the zero-entities case as a normal `200`, not an error.
- [ ] I've designed the nonexistent-id case as a `404`, not left it to
      produce whatever FastAPI does by default on an unhandled exception.
- [ ] I understand exactly why a manual `json.dumps` without
      `ensure_ascii=False` would break diacritics, and I've decided not to
      hand-roll serialization anywhere.
- [ ] I have **not** written any code under `src/vietnlp/serving/` yet.

## What NOT to do this week

- Don't start the FastAPI app yet — Task 2 (skeleton app) is Weeks 3-4.
- Don't touch `src/vietnlp/interfaces/**`, `src/vietnlp/platform/**`,
  `src/vietnlp/acquisition/**`, `src/vietnlp/curation/**`, any other
  project's module (`linguistics/`, `ontology/`, `semantics/`, `oupm/`,
  `treebank/`), `tests/fixtures/**`, or `student-projects/_gate/**`.
- Don't design a real Postgres-backed handler or authentication — both are
  explicit Non-Goals for this project.
- Don't plan on regenerating `gold_fixture.json` yourself — it's a frozen
  fixture under `tests/fixtures/**`, out of your `owned_paths`; if you want
  richer data later, ask the professor whether it's been regenerated after
  an upstream project merged (see `project.md`'s "Optional: checking against
  a merged upstream project").

## Commit & push your Week 1 work

```
git add student-projects/08-serving/API.md
git commit -m "Week 1: route and query-param design (draft)"
git push origin student/08-serving   # or your fork, if you lack push access
```

Not a Pull Request yet — that's Week 15 (see `project.md`'s "Contributing on
GitHub"). This commit just keeps your progress visible and backed up.

## Looking ahead

Week 2 finishes this design task: lock in your final route/query-param shape
in `API.md` before writing any code. Weeks 3-4 (Task 2) then wire
`GET /documents/{id}` against `gold_fixture.json` loaded into memory (or
SQLite — your choice, it's a static fixture either way).
