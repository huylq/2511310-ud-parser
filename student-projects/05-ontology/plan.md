# Project 5: Ontology Engineering — 15-Week Implementation Plan

Compact skeleton — see `student-projects/01-word-seg-pos/plan.md` for the
full worked-example depth this compresses.

**Gate:** `student-projects/_gate/run_gate.sh 05-ontology`

## Global Constraints

Same as Project 1's. Your code: `src/vietnlp/ontology/induction.py` (plus
any OWL/Turtle files you author under your own project directory or a new
`src/vietnlp/ontology/` data path — check `gate.yaml`'s `owned_paths`
before adding a new file location and ask if it's not covered).
`tests/fixtures/corpus/seed_upper_ontology.ttl` is read-only.

## Task breakdown

- [ ] **Weeks 1-2 — Research & design.** Read the seed ontology and OWL 2
  DL fundamentals (stay in DL — full OWL costs decidable reasoning).
  Decide your domain-class extension plan. Write `DESIGN.md`.
- [ ] **Weeks 3-4 — Reasoner setup.** Get a reasoner (e.g. `owlrl`,
  already a dev dependency — see `tests/test_fixture_seed_ontology.py`
  for the exact idiom) running over the seed ontology alone; confirm it
  reports CONSISTENT before adding anything.
- [ ] **Weeks 5-6 — `induce_individual()` skeleton.** TDD against
  `interfaces.stubs.ner_stub` output: PER -> Person, LOC -> Place, etc.,
  extending the stub's naive lookup with real judgment calls.
- [ ] **Weeks 7-8 — Domain class extensions + alignment.** Add classes
  under the frozen upper set; write `AlignmentRecord`s, applying the
  `owl:sameAs` vs `skos:closeMatch` distinction correctly.
- [ ] **Weeks 9-10 — Golden test.**
  `tests/golden/test_ontology_reasoner_golden.py` once authored.
- [ ] **Weeks 11-12 — Inconsistency diagnosis practice.** Deliberately
  introduce a wrong disjointness axiom, get the reasoner's justification,
  identify which axiom is actually wrong (not just which one silences the
  error) — document this exercise in `TESTING.md`.
- [ ] **Weeks 13-14 — `TESTING.md` + full gate pass.**
- [ ] **Week 15 — Submission.**
