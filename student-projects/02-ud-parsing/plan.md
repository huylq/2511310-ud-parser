# Project 2: UD Dependency Parsing — 15-Week Implementation Plan

Compact skeleton — see `student-projects/01-word-seg-pos/plan.md` for the
full worked-example depth this compresses.

**Gate:** `student-projects/_gate/run_gate.sh 02-ud-parsing`

## Global Constraints

Same as Project 1's plan.md Global Constraints section (Python 3.11,
`source="real"`, `interfaces/**` read-only, offline-only tests, TDD).
Your code: `src/vietnlp/linguistics/ud_parser.py`.

## Task breakdown

- [ ] **Weeks 1-2 — Research & design.** Read UD v2's dependency relation
  inventory and UD_Vietnamese-VTB's published conventions. Decide your
  parsing approach (rule-based/transition-based over your own grammar, or
  a trained statistical parser if you have the background). Write
  `DESIGN.md`.
- [ ] **Weeks 3-4 — Skeleton parser + tree-shape invariant.** Build
  `parse()` against `interfaces.stubs.linguistics_stub.stub_segment`
  output first (simple sentences). TDD against
  `interfaces.ud.is_single_rooted_tree` from day one — a parser that
  produces a malformed tree is worse than one that produces a
  linguistically imperfect but valid one.
- [ ] **Weeks 5-6 — Full fixture corpus.** Run over all 151 fixture
  sentences (via the stub segmenter). Fix crashes and malformed trees.
- [ ] **Weeks 7-8 — Vietnamese-specific constructions.** Classifier
  attachment (`clf` vs `det` — cite your convention), coordination
  (`cc`/`conj`), serial verb constructions (consistent head choice, per
  the linguist persona above), `của`-possessive if your fixture data has
  an example (else document the gap).
- [ ] **Weeks 9-10 — Golden test + adversarial cases.** Run
  `tests/golden/test_ud_parsing_golden.py` once authored (check with the
  professor if it isn't yet on your branch); build your own adversarial
  case (a genuinely ambiguous attachment).
- [ ] **Weeks 11-12 — Robustness & degenerate cases.** Empty sentence,
  single-token sentence, sentence with only punctuation.
- [ ] **Weeks 13-14 — `TESTING.md` + full gate pass.**
- [ ] **Week 15 — Submission.**
