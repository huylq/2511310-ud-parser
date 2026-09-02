# Project 3: NER & Coreference Resolution — 15-Week Implementation Plan

Compact skeleton — see `student-projects/01-word-seg-pos/plan.md` for the
full worked-example depth this compresses.

**Gate:** `student-projects/_gate/run_gate.sh 03-ner-coref`

## Global Constraints

Same as Project 1's. Your code: `src/vietnlp/linguistics/ner.py` and
`src/vietnlp/linguistics/coref.py`.

## Task breakdown

- [ ] **Weeks 1-2 — Research & design.** Decide your NER approach
  (gazetteer + rules is a reasonable, defensible choice for a fixed-scale
  corpus; a trained sequence tagger if you have the background). Write
  `DESIGN.md`.
- [ ] **Weeks 3-4 — Skeleton NER.** TDD span extraction against
  `interfaces.stubs.linguistics_stub.stub_segment` output on hand-written
  sentences: one full name, one honorific+name, zero entities.
- [ ] **Weeks 5-6 — Full fixture corpus + span verification.** Run over
  all 151 sentences; assert every span's text matches the source
  verbatim (never trust a claimed offset — locate it yourself).
- [ ] **Weeks 7-8 — Coreference within a document.** Build
  `resolve_coref()`: start with exact-match + honorific-stripped matching
  (a clear improvement over the stub's exact-match-only baseline), extend
  as time allows.
- [ ] **Weeks 9-10 — Golden test + adversarial cases.**
  `tests/golden/test_ner_coref_golden.py` once authored.
- [ ] **Weeks 11-12 — Robustness.** Sentences with zero entities (must
  return an empty list, not an error), adjacent same-label entities.
- [ ] **Weeks 13-14 — `TESTING.md` + full gate pass.**
- [ ] **Week 15 — Submission.**
