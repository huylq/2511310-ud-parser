# Week 1 Tasks — Project 9: HF Export & Benchmark Harness

**Branch:** `student/09-hf-export-bench`
**This week's scope:** the first half of `plan.md`'s "Weeks 1-2 — Research &
design" task. Reading + research + an export-format decision, finalized in
Week 2 before Weeks 3-5's `export_document()` skeleton. **No code under
`src/vietnlp/...` yet.**

## Day 1 — Environment setup

1. Clone and check out your branch (fork first if you lack push access — see
   `project.md`'s "Contributing on GitHub"):
   ```
   git clone git@github.com:phunghx/VietnamesModel.git
   cd VietnamesModel && git checkout student/09-hf-export-bench
   ```
2. Set up your environment:
   ```
   python3.11 -m venv .venv && source .venv/bin/activate
   pip install -e ".[dev]"
   ```
3. Confirm the inherited suite is green: `pytest tests -q`. Fails on a clean
   checkout → flag it to the professor.

## Day 1-2 — Required reading, in this exact order

1. `student-projects/09-hf-export-bench/spec.md` — your goal (export +
   benchmark harness), and the one hard requirement (dataset card
   completeness — read this section twice, it's the single most-checked
   thing about your submission).
2. `student-projects/09-hf-export-bench/plan.md` — the 15-week breakdown.
3. `student-projects/09-hf-export-bench/README.md` — quickstart + checklist.
4. `student-projects/09-hf-export-bench/project.md` — your exact contract:
   target signature, owned/forbidden paths, completion criteria. Read
   "You must not" twice — the gate checks scope mechanically.
5. `src/vietnlp/interfaces/export.py` — **in full.** This is the frozen
   `ExportRow`/`BenchmarkReport`/`REQUIRED_CARD_SECTIONS`/
   `validate_export_rows`/`validate_dataset_card` contract. Note exactly
   which four sections `validate_dataset_card()` checks for:
   `register_taxonomy`, `normalization`, `license`, `known_limitations`.
6. `tests/fixtures/serving/gold_fixture.json` — open it and study its
   shape end to end: this is your entire export source, and it's nested
   (documents → sentences → tokens/entities). Your job is denormalizing this
   into flat, one-row-per-sentence `ExportRow`s.
7. `tests/fixtures/benchmark/README.md` and all three stand-ins
   (`vlsp_ner_stub.jsonl`, `uit_vsfc_stub.jsonl`, `viquad_stub.jsonl`) — read
   the README first (it explains why these are explicitly **not** the real
   VLSP/UIT-VSFC/ViQuAD shared-task data), then skim each file's shape.

## Day 2-4 — Research task

1. **Export format options** — research the `datasets.Dataset`-loadable
   directory structure (Arrow/Parquet-backed, loadable via
   `datasets.load_dataset`) versus a hand-rolled JSONL-per-split layout.
   Understand the trade-off: `datasets` gives you a standard, tool-compatible
   structure but adds a dependency; JSONL-per-split has zero extra
   dependencies but nothing loads it "for free."
2. **Dataset card conventions** — read a couple of real HuggingFace dataset
   cards for structure/tone (outside the required four sections, which are
   fixed by `interfaces.export.REQUIRED_CARD_SECTIONS` and non-negotiable).
3. **NFC normalization, specifically** — re-read CLAUDE.md's Vietnamese-
   specific notes on this. Your dataset card's `normalization` section must
   **state NFC normalization explicitly** and that the original input-method
   form is preserved upstream — a generic "text is UTF-8 encoded" line fails
   `validate_dataset_card()`. Draft the actual sentence you'll use now, not
   later.
4. **Benchmark metrics** — for each of the three stand-ins, note what metric
   is natural for its task shape (e.g. token-level F1/accuracy for the NER
   stand-in) — you don't need to implement anything yet, just know what
   you're aiming for when Weeks 8-11 arrive.

## Day 3-5 — Decide your export format and sketch the mapping

- Pick `datasets`-loadable vs. JSONL-per-split, and write down why —
  this is a required `TESTING.md` topic later, so start the reasoning now.
- Take one real document from `gold_fixture.json` and hand-map it into the
  `ExportRow`(s) it should produce — every field, filled in with real
  values from that document, not placeholders.
- Draft your dataset card's four required sections in outline form,
  especially the exact `normalization` wording.
- Decide which of the three benchmark stand-ins you'll implement first in
  Weeks 8-9 (per `plan.md`, `vlsp_ner_stub.jsonl` is suggested as the
  simplest).

## Deliverable: `student-projects/09-hf-export-bench/DESIGN.md`

Create this file. It must contain:

- Your export-format decision (`datasets`-loadable vs. JSONL-per-split) and
  why.
- Your worked mapping of one real `gold_fixture.json` document into its
  resulting `ExportRow`(s).
- A draft of your dataset card's four sections, with the exact
  NFC-normalization sentence you plan to use.
- Your plan for which benchmark stand-in you'll implement first and the
  metric you'll use for it.

## Self-check before you call Week 1 done

- [ ] My worked `ExportRow` mapping uses real field values from
      `gold_fixture.json`, not placeholders.
- [ ] My draft `normalization` section explicitly says "NFC" and mentions
      the original input-method form being preserved upstream — not a
      generic "UTF-8 encoded" line.
- [ ] I can state, from `tests/fixtures/benchmark/README.md`, exactly why
      these three stand-ins are not the real shared-task datasets.
- [ ] I have **not** written any code under `src/vietnlp/export/` yet.

## What NOT to do this week

- Don't start `exporter.py`/`benchmark.py` yet — Task 2 (export skeleton) is
  Weeks 3-5.
- Don't touch `src/vietnlp/interfaces/**`, `src/vietnlp/platform/**`,
  `src/vietnlp/acquisition/**`, `src/vietnlp/curation/**`, any other
  project's module, `tests/fixtures/**`, or `student-projects/_gate/**`.
- Don't plan to source or license the real VLSP/UIT-VSFC/ViQuAD datasets —
  explicitly out of scope; the stand-ins exist exactly so you don't need to.
- Don't write a generic "text is UTF-8 encoded" placeholder for the
  normalization section and plan to fix it later — draft the real,
  NFC-specific wording now, since it's the one hard requirement this project
  is graded on.
- Don't wait on any other project — your export source and benchmark
  targets are the committed fixtures; there's nothing to pull from another
  student's branch (see `project.md`'s "Optional: checking against a merged
  upstream project").

## Commit & push your Week 1 work

```
git add student-projects/09-hf-export-bench/DESIGN.md
git commit -m "Week 1: export format decision and dataset-card draft"
git push origin student/09-hf-export-bench   # or your fork
```

Not a Pull Request yet — that's Week 14/15 (see `project.md`'s "Contributing
on GitHub"). This commit just keeps your progress visible and backed up.

## Looking ahead

Week 2 finishes this research/design task: lock in your export format and
finalize your dataset-card draft. Weeks 3-5 (Task 2) then TDD
`export_document()` against real `gold_fixture.json` rows: one document in,
its `ExportRow`s out.
