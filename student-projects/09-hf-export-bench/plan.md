# Project 9: HF Export & Benchmark Harness — 15-Week Implementation Plan

Compact skeleton — see `student-projects/01-word-seg-pos/plan.md` for the
full worked-example depth this compresses.

**Gate:** `student-projects/_gate/run_gate.sh 09-hf-export-bench`

## Global Constraints

Same as Project 1's. Your code: `src/vietnlp/export/exporter.py` and
`src/vietnlp/export/benchmark.py`.

## Task breakdown

- [ ] **Weeks 1-2 — Research & design.** Read `interfaces/export.py` and
  the three benchmark stand-ins in full. Decide your export directory
  layout and whether you'll take the `datasets` dependency. Write
  `DESIGN.md`.
- [ ] **Weeks 3-5 — `export_document()` skeleton.** TDD against
  `gold_fixture.json` rows: one document -> its `ExportRow`s.
- [ ] **Weeks 6-7 — Full export + dataset card.** Run over all 100
  documents; write the dataset card, satisfying all 4 required sections.
- [ ] **Weeks 8-9 — Benchmark harness skeleton.** Score against
  `vlsp_ner_stub.jsonl` first (simplest metric — token-level F1 or
  accuracy).
- [ ] **Weeks 10-11 — Remaining benchmarks.** `uit_vsfc_stub.jsonl`,
  `viquad_stub.jsonl`.
- [ ] **Weeks 12-13 — Golden test.**
  `tests/golden/test_hf_export_benchmark_golden.py` once authored.
- [ ] **Week 14 — `TESTING.md` + full gate pass.**
- [ ] **Week 15 — Submission.**
