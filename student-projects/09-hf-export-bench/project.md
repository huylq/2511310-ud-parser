# Project 9: HF Export & Benchmark Harness

## Target

Build the terminal export + evaluation project (nothing downstream consumes its output): denormalize
the fixture documents into a flat one-row-per-sentence export shape and write a HuggingFace-dataset-
shaped directory with a dataset card, plus a benchmark harness that scores against three format-shape
stand-ins and produces `BenchmarkReport`s.

```
export_document(doc: dict) -> list[interfaces.export.ExportRow]
```

`doc` is one row of `tests/fixtures/serving/gold_fixture.json`'s shape. Benchmark targets are the three
stand-ins in `tests/fixtures/benchmark/*_stub.jsonl` (VLSP NER, UIT-VSFC, ViQuAD — **explicitly not the
real shared-task data**, see `tests/fixtures/benchmark/README.md`). `source` must be `"real"`.

## Independence

This project is self-contained and runs in parallel with all the others — you wait on no one.
Your export source and benchmark targets are the committed fixtures (`gold_fixture.json` and
`tests/fixtures/benchmark/*_stub.jsonl`), **not** any other student's live output. It is the
terminal project — nothing downstream consumes your work. At merge time the professor re-exports from
the real projection and re-runs your *unchanged* suite; that is the integration step, not your job.

## Required products

- `src/vietnlp/export/exporter.py` — the `export_document()` implementation (module: `vietnlp.export.exporter`).
- Any other files under `src/vietnlp/export/**` you need (dataset writer, card generator, benchmark harness).
- `pyproject.toml` — **dependency additions only** (e.g. `datasets`/`huggingface_hub` if you use them;
  do not touch or reorder anything else in the file).
- `tests/test_export_*.py` — your own tests.
- `TESTING.md` (in this directory) — filled in with real design-decision rationale, including your
  dataset-format choice (`datasets.Dataset`-loadable vs. your own JSONL-per-split — document why).
- A passing gate: `student-projects/_gate/run_gate.sh 09-hf-export-bench` → `Overall: PASS`.

## Requirements

### Before you start
1. Work on branch `student/09-hf-export-bench` (cut from tag `curriculum-base`).
2. Set up the env: `python3.11 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"`.
3. Confirm the inherited suite is green: `pytest tests -q`.
4. Read in this order: `spec.md` → `plan.md` → `README.md` → `src/vietnlp/interfaces/export.py` in full.

### You may use
- `tests/fixtures/serving/gold_fixture.json` as your export source.
- `tests/fixtures/benchmark/*_stub.jsonl` as your benchmark targets.
- `interfaces.export.{ExportRow, BenchmarkReport, REQUIRED_CARD_SECTIONS, validate_export_rows, validate_dataset_card}` — frozen contract.
- `datasets` / `huggingface_hub` (optional — add as dependencies only if you use them).

### You must not
- Touch `src/vietnlp/interfaces/**`, `src/vietnlp/platform/**`, `src/vietnlp/acquisition/**`,
  `src/vietnlp/curation/**`, or any other project's module (`linguistics/`, `ontology/`, `semantics/`,
  `oupm/`, `treebank/`, `serving/`), `tests/fixtures/**`, or `student-projects/_gate/**`.
- Source or license the real VLSP/UIT-VSFC/ViQuAD datasets (out of scope — the stand-ins exist for this).
- Call a network API (offline-only tests).

### The one hard requirement: dataset card completeness
`validate_dataset_card()` checks for exactly four sections: `register_taxonomy`, `normalization`,
`license`, `known_limitations`. The `normalization` section must specifically state **NFC normalization**
and that the original input-method form is preserved upstream (CLAUDE.md's Vietnamese-specific notes) —
a generic "text is UTF-8 encoded" line does not satisfy this; be specific about NFC.

**Grading note:** only the `export_rows` producer is checked by the mechanical schema step. Benchmark-scoring
correctness is exercised by the golden-file test instead.

### Completion criteria
- Gate reports `Overall: PASS` (scope, clean install, schema, provenance `source=="real"`,
  your unit tests, golden test, ≥6 own tests with all required input classes: `nfc`, `register`,
  `degenerate`, `adversarial`, no live-only fixtures).
- Golden invariant: row count matches source; required `BenchmarkReport` metric keys present with values
  in range; every `BenchmarkReport` scored against a stand-in carries a non-empty `stub_note`.
- `TESTING.md` documents your export format choice and your NFC handling.
- `git diff curriculum-base...student/09-hf-export-bench --stat` touches only your `owned_paths`.
- You can explain any line of your submission and why it is there.

## Contributing on GitHub

The repo lives at `git@github.com:phunghx/VietnamesModel.git`
(HTTPS: `https://github.com/phunghx/VietnamesModel.git`). Your branch,
`student/09-hf-export-bench`, is already pushed there, cut from tag
`curriculum-base`.

1. Clone and check out your branch:
   ```
   git clone git@github.com:phunghx/VietnamesModel.git
   cd VietnamesModel && git checkout student/09-hf-export-bench
   ```
   If you don't have push access to this repo, fork it on GitHub first, add
   your fork as a second remote, and push your commits there instead — open
   the PR in step 4 from your fork's `student/09-hf-export-bench` branch.
2. Commit early and often directly to `student/09-hf-export-bench` (or its
   copy on your fork). This branch's commit history is part of what gets
   reviewed, not just the final diff.
3. Periodically sync interface fixes: `git fetch origin && git merge origin/main`.
   The professor only ever changes `main` to republish a genuine
   `interfaces/**` defect fix (see "Interface change control" in the
   top-level `student-projects/README.md`) — this should be rare.
4. When `student-projects/_gate/run_gate.sh 09-hf-export-bench` reports
   `Overall: PASS` and `TESTING.md` is filled in, open a **Pull Request from
   `student/09-hf-export-bench` into `main`** on GitHub. That PR is your
   submission — it is what gets folded into the final concatenation of all 9
   projects. Do not merge it yourself; the professor merges after the gate
   plus the manual review pass described in the top-level README.
5. Never touch `src/vietnlp/interfaces/**` or `student-projects/_gate/**` in
   your PR (both are in every project's `forbidden_paths` — the gate's scope
   check fails on any diff there). Found a real defect in one? Open a GitHub
   Issue describing it instead of editing it.

## Optional: checking against a merged upstream project

Your export source (`gold_fixture.json`) and benchmark targets
(`tests/fixtures/benchmark/*_stub.jsonl`) are static and committed —
regenerating either from real upstream output is the professor's job (both
generators live under the frozen `tests/fixtures/**`, out of your
`owned_paths`). There is nothing for you to pull from another student's
branch directly; if you want richer export input, ask the professor whether
an updated fixture has been regenerated after an upstream project merged —
never regenerate it yourself.
