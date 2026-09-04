# Project 6: Semantics / FOL

## Target

Build a translator from a UD dependency parse to a neo-Davidsonian first-order logical form
(events reified as variables, thematic roles as binary predicates, serialized as an S-expression),
type-checked against the ontology's predicate signatures.

```
to_logical_form(parse: interfaces.ud.DependencyParse) -> interfaces.semantics.LogicalForm
```

Consumes Project 2's output (stub or real) and Project 5's ontology (the frozen seed, or its
extended real form once merged). `source` must be `"real"`.

## Independence

This project is self-contained and runs in parallel with all the others — you wait on no one.
You build, test, and grade against Project 2's deterministic, committed UD-parse stub **and** the
frozen seed ontology (Project 5) — both already committed, **never** any other student's real
output. At merge time the professor swaps the stubs for the real upstream modules and re-runs your
*unchanged* suite; that swap is the integration step, not your job.

## Required products

- `src/vietnlp/semantics/translator.py` — the `to_logical_form()` implementation (module: `vietnlp.semantics.translator`).
- Any other files under `src/vietnlp/semantics/**` you need (type-checker, signature derivation).
- `tests/test_semantics_*.py` — your own tests.
- `TESTING.md` (in this directory) — filled in with real design-decision rationale.
- A passing gate: `student-projects/_gate/run_gate.sh 06-semantics` → `Overall: PASS`.

## Requirements

### Before you start
1. Work on branch `student/06-semantics` (cut from tag `curriculum-base`).
2. Set up the env: `python3.11 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"`.
3. Confirm the inherited suite is green: `pytest tests -q`.
4. Read in this order: `spec.md` → `plan.md` → `README.md` → `src/vietnlp/interfaces/semantics.py` in full.

### You may use
- The **stub** UD parse (from Project 2) and the frozen seed ontology (Project 5) as your inputs.
- `interfaces.semantics.{LogicalForm, validate_logical_form, is_balanced}` — frozen contract.
- The ontology's property domains/ranges as your type-checking signatures.

### You must not
- Touch `src/vietnlp/interfaces/**`, `src/vietnlp/platform/**`, `src/vietnlp/acquisition/**`,
  `src/vietnlp/curation/**`, `src/vietnlp/linguistics/**`, `src/vietnlp/ontology/**`,
  `tests/fixtures/**`, or `student-projects/_gate/**`.
- Do UD parsing (Project 2) or ontology modelling (Project 5) — you consume both, redesign neither.
- Widen a signature to `owl:Thing` to make a type failure go away (that disables the check for everything).

### Approach — Vietnamese-specific problems (handle, don't paper over)
- **No inflectional tense.** Tense comes from particles (`đã`, `đang`, `sẽ`) or context, often absent.
  Emit an underspecified temporal constraint, not a defaulted `(present e)`.
- **Classifiers are not quantifiers.** `một cuốn sách` = `một` + `cuốn` (classifier) + `sách`.
  The classifier constrains the sort; it does not bind a variable.
- **Bare nouns are number/definiteness-neutral.** `Tôi mua sách` may be one book or many — do not
  silently insert a cardinality-one existential.
- **Scope is underspecified by design.** Store the scope-neutral form plus the constraint set.
- **Topic-comment fronting:** the fronted topic is not automatically the agent.
Every form is type-checked; a type failure means the parse is wrong, the ontology lacks the
predicate, or the signature is wrong — diagnose which. `is_balanced()` checks parens only;
semantic/type correctness is your type-checker's job, reflected in `LogicalForm.type_checked`.

### Completion criteria
- Gate reports `Overall: PASS` (scope, clean install, schema, provenance `source=="real"`,
  your unit tests, golden test, ≥6 own tests with all required input classes: `quantifier`,
  `tense`, `degenerate`, `adversarial`, no live-only fixtures).
- Golden invariant: balanced-parens + type-check pass rate over a threshold.
- `TESTING.md` documents exactly what sentence types are in scope and what is out.
- `git diff curriculum-base...student/06-semantics --stat` touches only your `owned_paths`.
- You can explain any line of your submission and why it is there.

## Contributing on GitHub

The repo lives at `git@github.com:phunghx/VietnamesModel.git`
(HTTPS: `https://github.com/phunghx/VietnamesModel.git`). Your branch,
`student/06-semantics`, is already pushed there, cut from tag
`curriculum-base`.

1. Clone and check out your branch:
   ```
   git clone git@github.com:phunghx/VietnamesModel.git
   cd VietnamesModel && git checkout student/06-semantics
   ```
   If you don't have push access to this repo, fork it on GitHub first, add
   your fork as a second remote, and push your commits there instead — open
   the PR in step 4 from your fork's `student/06-semantics` branch.
2. Commit early and often directly to `student/06-semantics` (or its copy on
   your fork). This branch's commit history is part of what gets reviewed,
   not just the final diff.
3. Periodically sync interface fixes: `git fetch origin && git merge origin/main`.
   The professor only ever changes `main` to republish a genuine
   `interfaces/**` defect fix (see "Interface change control" in the
   top-level `student-projects/README.md`) — this should be rare.
4. When `student-projects/_gate/run_gate.sh 06-semantics` reports
   `Overall: PASS` and `TESTING.md` is filled in, open a **Pull Request from
   `student/06-semantics` into `main`** on GitHub. That PR is your
   submission — it is what gets folded into the final concatenation of all 9
   projects. Do not merge it yourself; the professor merges after the gate
   plus the manual review pass described in the top-level README.
5. Never touch `src/vietnlp/interfaces/**` or `student-projects/_gate/**` in
   your PR (both are in every project's `forbidden_paths` — the gate's scope
   check fails on any diff there). Found a real defect in one? Open a GitHub
   Issue describing it instead of editing it.

## Optional: checking against a merged upstream project

You are graded entirely against the frozen UD-parse stub and the frozen
seed ontology — neither requires Project 2 or Project 5 to be finished. If
either student has already pushed real, `source="real"` commits to
`student/02-ud-parsing` and/or `student/05-ontology` and you want an extra
sanity check:

1. `git fetch origin student/02-ud-parsing` and/or
   `git fetch origin student/05-ontology`.
2. In a throwaway script (never inside your committed test suite), import
   their real `parse()` / `induce_individual()` and feed real output into
   your `to_logical_form()` instead of the stub's.
3. Note anything you learn in `TESTING.md` — it's a bonus observation. Your
   gate submission must still work, and be graded, using only the committed
   stubs and the frozen seed ontology.

Never merge either branch into yours, and never make your submission depend
on their branches existing.
