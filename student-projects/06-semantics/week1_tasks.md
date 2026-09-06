# Week 1 Tasks — Project 6: Semantics / FOL

**Branch:** `student/06-semantics`
**This week's scope:** the first half of `plan.md`'s "Weeks 1-2 — Research &
design" task. Reading + research + a first-pass S-expression grammar,
finalized in Week 2 before Weeks 3-4's skeleton translator. **No code under
`src/vietnlp/...` yet.**

## Day 1 — Environment setup

1. Clone and check out your branch (fork first if you lack push access — see
   `project.md`'s "Contributing on GitHub"):
   ```
   git clone git@github.com:phunghx/VietnamesModel.git
   cd VietnamesModel && git checkout student/06-semantics
   ```
2. Set up your environment:
   ```
   python3.11 -m venv .venv && source .venv/bin/activate
   pip install -e ".[dev]"
   ```
3. Confirm the inherited suite is green: `pytest tests -q`. Fails on a clean
   checkout → flag it to the professor.

## Day 1-2 — Required reading, in this exact order

1. `student-projects/06-semantics/spec.md` — your goal, the worked
   `(exists (e x) ...)` target example, and the Vietnamese-specific problems
   folded in from the semantics-engineer persona.
2. `student-projects/06-semantics/plan.md` — the 15-week breakdown.
3. `student-projects/06-semantics/README.md` — quickstart + checklist.
4. `student-projects/06-semantics/project.md` — your exact contract: target
   signature, owned/forbidden paths, completion criteria. Read "You must
   not" twice — the gate checks scope mechanically.
5. `src/vietnlp/interfaces/semantics.py` — **in full.** This is the frozen
   `LogicalForm` contract. Note that `is_balanced()` only checks matched
   parens — semantic/type correctness is entirely your own type-checker's
   job, reflected in `LogicalForm.type_checked`.
6. `src/vietnlp/interfaces/ud.py` — skim `DependencyParse`, your actual
   input shape.
7. `tests/fixtures/corpus/seed_upper_ontology.ttl` — skim it. Its property
   domains/ranges (e.g. `locatedIn`, `affiliatedWith`) are your starting
   type-checking signatures for Weeks 7-8.
8. `.claude/agents/semantics-engineer.md` — the full persona file. `spec.md`
   folds in the core standard, but read the whole file, including the worked
   example.
9. `tests/fixtures/corpus/fixture_sentences.jsonl` — read 15-20 rows looking
   specifically for: a classifier phrase (`một cuốn sách`), a tense particle
   (`đã`/`đang`/`sẽ`), a bare noun with ambiguous number, and anything that
   looks like topic-comment fronting. You'll hand-translate one or two of
   these for Day 3-5.

## Day 2-4 — Research task

1. **Neo-Davidsonian event semantics basics** — events reified as a variable
   `e`, thematic roles as binary predicates (`agent(e,x)`, `theme(e,x)`,
   `location(e,x)`), existential closure over the event and its arguments.
   Read enough to be comfortable constructing one by hand.
2. **Vietnamese tense particles** (`đã`, `đang`, `sẽ`) — how they mark
   aspect/tense when present, and how often they're simply absent with tense
   left to context. Per the persona: you must emit an *underspecified*
   temporal constraint when tense is unmarked, never default to
   `(present e)`.
3. **Classifiers as sort constraints, not quantifiers** — `một cuốn sách` is
   `một` (one) + `cuốn` (classifier) + `sách` (book); the classifier
   constrains the *sort* of the noun, it does not bind a quantifier variable
   the way `một` alone might suggest.
4. **Bare nouns and number-neutrality** — `Tôi mua sách` may be one book or
   many; research how to represent this without silently inserting a
   cardinality-one existential.

## Day 3-5 — Draft your S-expression grammar

Decide, precisely enough to write code against later:

- **Predicate naming convention** — how you'll name event predicates (verb
  lemma? Something else?) and thematic-role predicates (`agent`, `theme`,
  `location`, ... — pick your full initial set).
- **Predicate arity table** — for every predicate you plan to emit, its
  arity and what each argument position means.
- **Underspecified-tense representation** — what a `LogicalForm` looks like
  for a sentence with a tense particle vs. one without. (Per the persona:
  store the scope-neutral form plus the constraint set — don't commit to a
  reading you can't recover from.)
- **Classifier representation** — how a classifier phrase becomes a sort
  constraint in your grammar, distinct from how a bare quantifier would be
  represented.

Then hand-translate one sentence from the fixture corpus containing a
classifier phrase, and one containing a tense particle (or explain why
neither exists in your corpus and what you'll do instead) — writing out the
full S-expression by hand, the same way `spec.md`'s worked example does for
"Nam mua một cuốn sách ở Hà Nội."

## Deliverable: `student-projects/06-semantics/DESIGN.md`

Create this file. It must contain:

- Your predicate-arity table.
- Your underspecified-tense representation, with a worked example of a
  sentence with a tense particle and one without.
- Your classifier-phrase representation, with a worked example.
- Your two hand-translated fixture sentences (classifier example, tense
  example), shown as full S-expressions.
- A note on how you'll read Project 5's ontology property domains/ranges as
  type-checking signatures once you get to Weeks 7-8.

## Self-check before you call Week 1 done

- [ ] My two hand-translated examples are internally consistent with my own
      predicate-arity table (no predicate used with a different arity than
      I declared).
- [ ] I can explain, without notes, why a missing tense marker should
      produce an underspecified constraint, not a defaulted `(present e)`.
- [ ] I can explain why `một cuốn sách`'s classifier isn't a quantifier.
- [ ] I have **not** written any code under `src/vietnlp/semantics/` yet.

## What NOT to do this week

- Don't start `translator.py` yet — Task 2 (skeleton translator) is Weeks
  3-4.
- Don't touch `src/vietnlp/interfaces/**`, `src/vietnlp/platform/**`,
  `src/vietnlp/acquisition/**`, `src/vietnlp/curation/**`,
  `src/vietnlp/linguistics/**`, `src/vietnlp/ontology/**`,
  `tests/fixtures/**`, or `student-projects/_gate/**`.
- Don't design UD parsing (Project 2) or ontology modelling (Project 5) —
  you consume both, you redesign neither.
- Don't plan to widen a type signature to `owl:Thing` to sidestep a
  type-check failure later — that disables the check for everything; if a
  type failure comes up in Weeks 7-8, the fix is to diagnose whether the
  parse, the ontology, or the signature is wrong.
- Don't pull Project 2's or Project 5's real branches this week — you build
  and are graded against the frozen stub/seed ontology only.

## Commit & push your Week 1 work

```
git add student-projects/06-semantics/DESIGN.md
git commit -m "Week 1: S-expression grammar and worked examples (draft)"
git push origin student/06-semantics   # or your fork, if you lack push access
```

Not a Pull Request yet — that's Week 15 (see `project.md`'s "Contributing on
GitHub"). This commit just keeps your progress visible and backed up.

## Looking ahead

Week 2 finishes this research/design task: lock in your grammar and confirm
it handles the sentence types your fixture corpus actually needs. Weeks 3-4
(Task 2) then TDD a skeleton `to_logical_form()` against
`interfaces.stubs.ud_stub.stub_parse` output on simple SVO sentences first:
one event predicate, one agent, one theme.
