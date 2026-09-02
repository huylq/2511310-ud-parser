# Project 6: Semantics / FOL — 15-Week Implementation Plan

Compact skeleton — see `student-projects/01-word-seg-pos/plan.md` for the
full worked-example depth this compresses.

**Gate:** `student-projects/_gate/run_gate.sh 06-semantics`

## Global Constraints

Same as Project 1's. Your code: `src/vietnlp/semantics/translator.py`
(and a separate type-checker module if you split it out).

## Task breakdown

- [ ] **Weeks 1-2 — Research & design.** Study neo-Davidsonian event
  semantics. Decide your S-expression grammar precisely (predicate
  arities, how thematic roles are named). Write `DESIGN.md`.
- [ ] **Weeks 3-4 — Skeleton translator.** TDD against
  `interfaces.stubs.ud_stub.stub_parse` output on simple SVO sentences
  first: one event predicate, agent, theme.
- [ ] **Weeks 5-6 — Tense & classifiers.** Handle particle-based tense as
  underspecified constraints; handle classifier phrases as sort
  constraints, not quantifiers.
- [ ] **Weeks 7-8 — Type checking.** Build the type-checker against
  Project 5's ontology predicate signatures (the frozen seed's
  `locatedIn`/`affiliatedWith` properties are your starting signatures).
- [ ] **Weeks 9-10 — Golden test.**
  `tests/golden/test_semantics_type_check_golden.py` once authored.
- [ ] **Weeks 11-12 — Scope & topic-comment.** Handle at least one
  genuinely scope-ambiguous or topic-fronted sentence from the fixture
  corpus; document your underspecification choice.
- [ ] **Weeks 13-14 — `TESTING.md` + full gate pass.**
- [ ] **Week 15 — Submission.**
