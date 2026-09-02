# Project 4: Treebank Curation & Adjudication — 15-Week Implementation Plan

Compact skeleton — see `student-projects/01-word-seg-pos/plan.md` for the
full worked-example depth this compresses.

**Gate:** `student-projects/_gate/run_gate.sh 04-treebank-adjudication`

## Global Constraints

Same as Project 1's. Your code: `src/vietnlp/treebank/adjudicator.py`.
Depends on Projects 1, 2, 3 (stub or real) per the plan's dependency graph
(`{1,2,3} -> 4`) — but your gate input is the frozen CoNLL-U fixture, not
a live upstream call.

## Task breakdown

- [ ] **Weeks 1-2 — Research & design.** Read the PROVISIONAL treebank
  fixture end to end, including its perturbation notes. Read UD v2's
  guidelines for every relation that appears in it. Write `DESIGN.md`
  covering your adjudication policy for each perturbation type (see the
  fixture's own table).
- [ ] **Weeks 3-5 — Skeleton adjudicator.** TDD `adjudicate()` against the
  10 unperturbed sentences first (trivial: zero decisions expected, both
  systems agree), then the 10 perturbed ones — write a real, principled
  ruling for each, following the standard above.
- [ ] **Weeks 6-7 — IAA computation.** Implement Cohen's kappa (POS
  agreement) and LAS agreement over the gold/system-B pair; produce an
  `IAAReport`.
- [ ] **Weeks 8-9 — Golden test.**
  `tests/golden/test_treebank_adjudication_golden.py` once authored —
  likely checks your kappa/LAS numbers against precomputed values on this
  fixed fixture.
- [ ] **Weeks 10-11 — Precedent consistency.** Re-read your own rulings:
  do any two decisions apply inconsistent principles to similar cases? If
  so, which is right, and what does that mean for the other?
- [ ] **Weeks 12-13 — Robustness & adversarial cases.** A case where the
  two systems disagree on something your policy doesn't yet cover.
- [ ] **Week 14 — `TESTING.md` + full gate pass.**
- [ ] **Week 15 — Submission.**
