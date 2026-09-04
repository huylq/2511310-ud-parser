# Project 8: Serving API

## Target

Build a FastAPI service exposing `interfaces.serving.DocumentResponse` (with nested
`SentenceResponse`/`EntityResponse`) over the static, offline fixture
`tests/fixtures/serving/gold_fixture.json` (materialized by running every other project's stub over
the full 100-document fixture corpus, see `tests/fixtures/generate_gold_fixture.py`).

At minimum:
- `GET /documents/{id}` → one `DocumentResponse`
- `GET /documents` → a paginated list
- `GET /documents/{id}/entities` → that document's entities

Design the exact route/query-param shape yourself; document it (edit `spec.md` or add an `API.md`
in this directory) **before** implementing.

## Independence

This project is self-contained and runs in parallel with all the others — you wait on no one.
Your data source is the static, committed fixture (`tests/fixtures/serving/gold_fixture.json`),
**not** any other student's live output, and you need no real database or any other project's merged
code. At merge time the professor points the API at the real Postgres projection and re-runs your
*unchanged* suite; that swap is the integration step, not your job.

## Required products

- `src/vietnlp/serving/` — a FastAPI app (`app.py` or similar entry point) plus any handler modules.
- `pyproject.toml` — **dependency additions only** (FastAPI/uvicorn/httpx are not yet project
  dependencies; do not touch or reorder anything else in the file).
- `tests/test_serving_*.py` — your own tests.
- `TESTING.md` (in this directory) — filled in with real design-decision rationale.
- `spec.md` extension or `API.md` — your documented route/query-param design.
- A passing gate: `student-projects/_gate/run_gate.sh 08-serving` → `Overall: PASS`.

## Requirements

### Before you start
1. Work on branch `student/08-serving` (cut from tag `curriculum-base`).
2. Set up the env: `python3.11 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"`.
3. Confirm the inherited suite is green: `pytest tests -q`.
4. Read in this order: `spec.md` → `plan.md` → `README.md` → `src/vietnlp/interfaces/serving.py` in full.

### You may use
- `tests/fixtures/serving/gold_fixture.json` as your data source (static, offline).
- `interfaces.serving.{DocumentResponse, SentenceResponse, EntityResponse}` — frozen contract.
- `fastapi`, `uvicorn`, `httpx` (add as dependencies in `pyproject.toml`).

### You must not
- Touch `src/vietnlp/interfaces/**`, `src/vietnlp/platform/**`, `src/vietnlp/acquisition/**`,
  `src/vietnlp/curation/**`, or any other project's module (`linguistics/`, `ontology/`, `semantics/`,
  `oupm/`, `treebank/`), `tests/fixtures/**`, or `student-projects/_gate/**`.
- Build a real Postgres-backed handler (out of scope) or authentication/authorization (not needed).
- Call a network API (offline-only tests).

### The one hard invariant: UTF-8/diacritics round-trip
**UTF-8/diacritics must round-trip through JSON untouched.** FastAPI's default response encoding does
this correctly (`ensure_ascii=False` behavior) — the trap is any manual `json.dumps(...)` in your
handler code without `ensure_ascii=False`, which silently escapes every non-ASCII character to a
`\uXXXX` sequence. Test this explicitly: assert a response body contains the literal diacritic
characters, not escape sequences.

**Grading note:** this `gate.yaml` has no `producers` (the `interfaces.serving` objects carry no
`source` field). Grading is almost entirely the golden `TestClient` test plus your own suite.

### Completion criteria
- Gate reports `Overall: PASS` (scope, clean install, your unit tests, golden test — `TestClient`
  returns exact fixture rows per endpoint, offline, diacritics intact — ≥6 own tests with all
  required input classes: `ensure_ascii`, `utf-8`, `degenerate`, `adversarial`, no live-only fixtures).
- A document with zero entities is a valid case (not an error); a nonexistent document id → a proper
  404, not a 500.
- `TESTING.md` + your `API.md`/spec extension explain the design.
- `git diff curriculum-base...student/08-serving --stat` touches only your `owned_paths`.
- You can explain any line of your submission and why it is there.

## Contributing on GitHub

The repo lives at `git@github.com:phunghx/VietnamesModel.git`
(HTTPS: `https://github.com/phunghx/VietnamesModel.git`). Your branch,
`student/08-serving`, is already pushed there, cut from tag
`curriculum-base`.

1. Clone and check out your branch:
   ```
   git clone git@github.com:phunghx/VietnamesModel.git
   cd VietnamesModel && git checkout student/08-serving
   ```
   If you don't have push access to this repo, fork it on GitHub first, add
   your fork as a second remote, and push your commits there instead — open
   the PR in step 4 from your fork's `student/08-serving` branch.
2. Commit early and often directly to `student/08-serving` (or its copy on
   your fork). This branch's commit history is part of what gets reviewed,
   not just the final diff.
3. Periodically sync interface fixes: `git fetch origin && git merge origin/main`.
   The professor only ever changes `main` to republish a genuine
   `interfaces/**` defect fix (see "Interface change control" in the
   top-level `student-projects/README.md`) — this should be rare.
4. When `student-projects/_gate/run_gate.sh 08-serving` reports
   `Overall: PASS` and `TESTING.md` is filled in, open a **Pull Request from
   `student/08-serving` into `main`** on GitHub. That PR is your
   submission — it is what gets folded into the final concatenation of all 9
   projects. Do not merge it yourself; the professor merges after the gate
   plus the manual review pass described in the top-level README.
5. Never touch `src/vietnlp/interfaces/**` or `student-projects/_gate/**` in
   your PR (both are in every project's `forbidden_paths` — the gate's scope
   check fails on any diff there). Found a real defect in one? Open a GitHub
   Issue describing it instead of editing it.

## Optional: checking against a merged upstream project

Your data source is the static, committed `gold_fixture.json` — regenerating
it from a real upstream module is the professor's job (it's built by
`tests/fixtures/generate_gold_fixture.py`, which lives under the frozen
`tests/fixtures/**`, out of your `owned_paths`). There is nothing for you to
pull from another student's branch directly; if you want to see your API
serve richer data, ask the professor whether an updated `gold_fixture.json`
has been regenerated after an upstream project merged — never regenerate it
yourself.
