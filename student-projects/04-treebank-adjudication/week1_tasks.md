# Week 1 Tasks — Project 4: Treebank Curation & Adjudication

**Branch:** `student/04-treebank-adjudication`
**This week's scope:** the first half of `plan.md`'s "Weeks 1-2 — Research &
design" task. Reading + research + a per-perturbation-type adjudication
stance, finalized in Week 2 before Weeks 3-5's skeleton adjudicator. **No code
under `src/vietnlp/...` yet.**

## Day 1 — Environment setup

1. Clone and check out your branch (fork first if you lack push access — see
   `project.md`'s "Contributing on GitHub"):
   ```
   git clone git@github.com:phunghx/VietnamesModel.git
   cd VietnamesModel && git checkout student/04-treebank-adjudication
   ```
2. Set up your environment:
   ```
   python3.11 -m venv .venv && source .venv/bin/activate
   pip install -e ".[dev]"
   ```
3. Confirm the inherited suite is green: `pytest tests -q`. Fails on a clean
   checkout → flag it to the professor.

## Day 1-2 — Required reading, in this exact order

1. `student-projects/04-treebank-adjudication/spec.md` — your goal and the
   full adjudication standard folded in from the treebank-adjudicator
   persona.
2. `student-projects/04-treebank-adjudication/plan.md` — the 15-week
   breakdown.
3. `student-projects/04-treebank-adjudication/README.md` — quickstart +
   checklist.
4. `student-projects/04-treebank-adjudication/project.md` — your exact
   contract: target signature, owned/forbidden paths, completion criteria.
   Read "You must not" twice — the gate checks scope mechanically.
5. `src/vietnlp/interfaces/treebank.py` — **in full.** This is the frozen
   `AdjudicatedSentence`/`AdjudicationDecision`/`IAAReport` contract.
   `validate_adjudicated_sentence` rejects an empty `rationale` — note why
   before you design anything.
6. `tests/fixtures/treebank/PROVISIONAL.md` — **in full.** This names every
   perturbation type in the test fixture and is provisional (pending
   professor sign-off), but you build against it regardless — it's your
   entire input for Weeks 3-5.
7. `tests/fixtures/treebank/gold_treebank_seed.conllu` and
   `system_b_perturbed.conllu` — open both. Pick 3-4 sentence IDs and
   compare the two files' analysis of the same sentence side by side, so a
   "perturbation" is a concrete thing you've seen, not an abstract term.
8. `.claude/agents/treebank-adjudicator.md` — the full persona file.
   `spec.md` folds in the core standard, but read the whole file.

## Day 2-4 — Research task

1. **Catalogue the perturbation types.** `PROVISIONAL.md`'s table names every
   perturbation deliberately introduced into `system_b_perturbed.conllu`
   relative to the seed. List each one in your own words.
2. **For each perturbation type, find the relevant UD v2 guideline or
   UD_Vietnamese-VTB precedent** that would settle a real disagreement of
   that kind. If you can't find one, that's a legitimate finding — Project 4
   spec.md is explicit: "if the honest answer is that a needed convention
   does not yet exist, say so and draft it. Do not manufacture a confident
   ruling."
3. **Read up on the two metrics you'll implement in Weeks 6-7:** Cohen's
   kappa (for POS agreement) and Labeled Attachment Score / LAS agreement.
   You don't need to implement them this week — just understand what each
   one measures and why the gate requires kappa ≥ 0.80 and LAS ≥ 90% (per
   `spec.md`: "if your rulings are what is holding agreement up, the
   guidelines are the problem" — i.e., these thresholds are a check on the
   fixture's own quality, not just your adjudicator).

## Day 3-5 — Draft your adjudication stance per perturbation type

For each perturbation type from Day 2-4, Step 1, write a provisional ruling
principle — not the final ruling on every sentence yet, but your general
policy for that *class* of disagreement. Structure each one using the
five-part standard from `spec.md` (fold it in, it's binding):

1. The competing analyses, stated fairly (steelman the one you'll likely
   reject).
2. The deciding principle — a UD v2 guideline, a VTB precedent, or a stated
   consistency argument. ("It reads better" is never a principle.)
3. (Left for Weeks 3-5, once you're ruling on actual sentences) the ruling
   itself, in CoNLL-U.
4. The generalization this establishes, phrased so a future annotator could
   apply it without re-deriving your reasoning.
5. Any precedent conflicts you can already anticipate between two
   perturbation types.

## Deliverable: `student-projects/04-treebank-adjudication/DESIGN.md`

Create this file. It must contain:

- Your catalogue of perturbation types from `PROVISIONAL.md`, in your own
  words.
- Your provisional deciding principle for each type (parts 1-2-4 of the
  standard above), with a citation or an honest "no existing convention
  covers this — here's my proposed one" where relevant.
- Your understanding of Cohen's kappa and LAS agreement, in your own words,
  and what the ≥ 0.80 / ≥ 90% thresholds actually mean for this fixture.
- Any perturbation-type pairs you already suspect might create a precedent
  conflict — you don't have to resolve it yet, just flag it for Weeks 10-11
  ("Precedent consistency").

## Self-check before you call Week 1 done

- [ ] I can list every perturbation type in `PROVISIONAL.md`'s table from
      memory, in my own words.
- [ ] For at least half of them, I have a real deciding principle written
      down — not just "I'll decide when I see it."
- [ ] I can explain Cohen's kappa and LAS agreement to someone who hasn't
      read this project's spec.
- [ ] I understand why `validate_adjudicated_sentence` rejects an empty
      `rationale` — a bare pick with no reasoning is not an adjudication.
- [ ] I have **not** written any code under `src/vietnlp/treebank/` yet.

## What NOT to do this week

- Don't start `adjudicator.py` yet — Task 2 (skeleton adjudicator) is Weeks
  3-5.
- Don't touch `src/vietnlp/interfaces/**`, `src/vietnlp/platform/**`,
  `src/vietnlp/acquisition/**`, `src/vietnlp/curation/**`,
  `src/vietnlp/linguistics/**`, `tests/fixtures/**`, or
  `student-projects/_gate/**`.
- Don't try to build the two candidate systems yourself — they're given
  (the PROVISIONAL fixtures); your job is the adjudication function and IAA
  computation, not a corpus-wide CoNLL-U pipeline.
- Don't treat `gold_treebank_seed.conllu` as ground truth you copy from —
  per `spec.md`, it's "system A," and your ruling must be independently
  justified even when it happens to agree with it.
- Don't pull Project 2's real branch this week — your candidate systems this
  week are the two committed PROVISIONAL fixtures, nothing else.

## Commit & push your Week 1 work

```
git add student-projects/04-treebank-adjudication/DESIGN.md
git commit -m "Week 1: perturbation catalogue and adjudication stance (draft)"
git push origin student/04-treebank-adjudication   # or your fork
```

Not a Pull Request yet — that's Week 14/15 (see `project.md`'s "Contributing
on GitHub"). This commit just keeps your progress visible and backed up.

## Looking ahead

Week 2 finishes this research/design task: lock in your deciding principle
for every perturbation type, with citations. Weeks 3-5 (Task 2) then TDD
`adjudicate()` against the 10 unperturbed sentences first (trivial: both
systems agree, zero decisions expected), then the 10 perturbed ones, where
you write a real, principled ruling for each using the standard above.
