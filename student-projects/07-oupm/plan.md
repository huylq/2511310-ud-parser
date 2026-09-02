# Project 7: OUPM Entity Resolution — 15-Week Implementation Plan

Compact skeleton — see `student-projects/01-word-seg-pos/plan.md` for the
full worked-example depth this compresses.

**Gate:** `student-projects/_gate/run_gate.sh 07-oupm`

## Global Constraints

Same as Project 1's. Your code: `src/vietnlp/oupm/resolver.py`.

## Task breakdown

- [ ] **Weeks 1-2 — Research & design.** Read the PROVISIONAL coref probe
  fixture's full trap table. Decide your approach (MCMC vs. a
  well-justified simpler clustering — see spec.md's Non-Goals framing).
  Write `DESIGN.md`, explicitly scoping which traps you will handle.
- [ ] **Weeks 3-4 — Vietnamese name-similarity function.** Build and unit
  test your name-comparison logic in isolation: honorific stripping,
  diacritic normalization, given-name-vs-surname weighting — before
  wiring it into any clustering algorithm.
- [ ] **Weeks 5-7 — Clustering skeleton.** TDD `cluster()` against the
  easy baseline (`probe-12-easy-baseline-exact-repeats`) first, then the
  surname-collision and same-name-different-people traps (these test
  your ability to NOT over-merge, the harder and more important
  direction per the persona above).
- [ ] **Weeks 8-9 — Diacritic & honorific traps.** The remaining probe
  documents.
- [ ] **Weeks 10-11 — Evaluation.** Implement B³/CEAF/MUC (or your scoped-
  down metric) against the gold clustering.
- [ ] **Weeks 12-13 — Golden test + leakage check.**
  `tests/golden/test_oupm_clustering_golden.py` once authored. Per the
  persona: if a result looks too good, check for leakage from the
  canonical name into your features before believing it.
- [ ] **Week 14 — `TESTING.md` + full gate pass.**
- [ ] **Week 15 — Submission.**
