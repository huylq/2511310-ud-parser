# Project 4: Treebank Curation & Adjudication

## Target

Build an adjudicator that reconciles two competing UD analyses of the same sentence into a
single final ruling, with a reasoned record of every decision, plus an inter-annotator-agreement
report.

```
adjudicate(sent_id: str, system_a: tuple[UDToken, ...], system_b: tuple[UDToken, ...]) -> interfaces.treebank.AdjudicatedSentence
```

Given two candidate UD analyses (e.g. Project 2's real parser vs. a perturbed alternate, or two
annotator passes), produce a final adjudicated analysis and a record of every decision — which
field disagreed, what the two candidates said, what you decided, and why. Also compute an
`IAAReport` (Cohen's kappa for POS, LAS agreement) over the gold seed set. `source` must be `"real"`.

**Test data is PROVISIONAL:** `tests/fixtures/treebank/gold_treebank_seed.conllu` +
`system_b_perturbed.conllu` (see `tests/fixtures/treebank/PROVISIONAL.md`). Treat
`gold_treebank_seed.conllu` as "system A" for your `adjudicate()` calls — it is itself a full UD
analysis, not the "truth". Adjudication means producing YOUR OWN ruling given two candidates,
independently justified (it often agrees with the seed, but must be derived, not copied).

## Independence

This project is self-contained and runs in parallel with all the others — you wait on no one.
Your two candidate analyses come from the committed PROVISIONAL fixtures
(`gold_treebank_seed.conllu` + `system_b_perturbed.conllu`), **not** from any other student's live
output, and you do not build the candidate systems yourself. At merge time the professor runs your
adjudicator against a real parser's output and re-runs your *unchanged* suite — that is the
integration step, not your job.

## Required products

- `src/vietnlp/treebank/adjudicator.py` — the `adjudicate()` implementation (module: `vietnlp.treebank.adjudicator`).
- Any other files under `src/vietnlp/treebank/**` you need (e.g. IAA computation).
- `tests/test_treebank_*.py` — your own tests.
- `TESTING.md` (in this directory) — filled in with real design-decision rationale.
- A passing gate: `student-projects/_gate/run_gate.sh 04-treebank-adjudication` → `Overall: PASS`.

## Requirements

### Before you start
1. Work on branch `student/04-treebank-adjudication` (cut from tag `curriculum-base`).
2. Set up the env: `python3.11 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"`.
3. Confirm the inherited suite is green: `pytest tests -q`.
4. Read in this order: `spec.md` → `plan.md` → `README.md` → `src/vietnlp/interfaces/treebank.py` in full.

### You may use
- The PROVISIONAL treebank fixtures listed above.
- `interfaces.treebank.{AdjudicatedSentence, AdjudicationDecision, IAAReport, validate_adjudicated_sentence}` — frozen contract.
- UD v2 guidelines + UD_Vietnamese-VTB precedent as your deciding principles.

### You must not
- Touch `src/vietnlp/interfaces/**`, `src/vietnlp/platform/**`, `src/vietnlp/acquisition/**`,
  `src/vietnlp/curation/**`, `src/vietnlp/linguistics/**`, `tests/fixtures/**`, or `student-projects/_gate/**`.
- Produce the two candidate systems yourself (they are given), or build a corpus-wide CoNLL-U export pipeline.

### Approach — the adjudication standard (binding)
Every ruling must contain: (1) the competing analyses stated fairly (steelman the rejected one);
(2) the deciding principle — a UD v2 guideline, a VTB precedent, or a stated consistency argument
("it reads better" is not a principle); (3) the ruling in CoNLL-U; (4) the generalisation (a rule
a future annotator can apply without re-deriving your reasoning); (5) any precedent conflicts, with
the proposed re-annotation scope. If the honest answer is that a needed convention does not yet
exist, say so and draft it — do not manufacture a confident ruling.
`AdjudicationDecision.rationale` is where (1)–(2) go in prose; `validate_adjudicated_sentence`
rejects an empty rationale. Agreement gates: Cohen's kappa ≥ 0.80 (POS), LAS ≥ 90%.

### Completion criteria
- Gate reports `Overall: PASS` (scope, clean install, schema, provenance `source=="real"`,
  your unit tests, golden test, ≥6 own tests with all required input classes: `rationale`,
  `kappa`, `degenerate`, `adversarial`, no live-only fixtures).
- `TESTING.md` shows at least one genuine, defensible `rationale` and an explainable kappa/agreement computation.
- `git diff curriculum-base...student/04-treebank-adjudication --stat` touches only your `owned_paths`.
- You can explain any line of your submission and why it is there.

## Contributing on GitHub

The repo lives at `git@github.com:phunghx/VietnamesModel.git`
(HTTPS: `https://github.com/phunghx/VietnamesModel.git`). Your branch,
`student/04-treebank-adjudication`, is already pushed there, cut from tag
`curriculum-base`.

1. Clone and check out your branch:
   ```
   git clone git@github.com:phunghx/VietnamesModel.git
   cd VietnamesModel && git checkout student/04-treebank-adjudication
   ```
   If you don't have push access to this repo, fork it on GitHub first, add
   your fork as a second remote, and push your commits there instead — open
   the PR in step 4 from your fork's `student/04-treebank-adjudication` branch.
2. Commit early and often directly to `student/04-treebank-adjudication` (or
   its copy on your fork). This branch's commit history is part of what
   gets reviewed, not just the final diff.
3. Periodically sync interface fixes: `git fetch origin && git merge origin/main`.
   The professor only ever changes `main` to republish a genuine
   `interfaces/**` defect fix (see "Interface change control" in the
   top-level `student-projects/README.md`) — this should be rare.
4. When `student-projects/_gate/run_gate.sh 04-treebank-adjudication` reports
   `Overall: PASS` and `TESTING.md` is filled in, open a **Pull Request from
   `student/04-treebank-adjudication` into `main`** on GitHub. That PR is
   your submission — it is what gets folded into the final concatenation of
   all 9 projects. Do not merge it yourself; the professor merges after the
   gate plus the manual review pass described in the top-level README.
5. Never touch `src/vietnlp/interfaces/**` or `student-projects/_gate/**` in
   your PR (both are in every project's `forbidden_paths` — the gate's scope
   check fails on any diff there). Found a real defect in one? Open a GitHub
   Issue describing it instead of editing it.

## Optional: checking against a merged upstream project

Your two candidate systems are the committed PROVISIONAL fixtures — that is
what you are graded and gated against, and it requires neither Project 2
nor Project 3 to exist. If you want an extra sanity check once Project 2's
student has pushed real, `source="real"` commits to `student/02-ud-parsing`:

1. `git fetch origin student/02-ud-parsing`
2. In a throwaway script (never inside your committed test suite), run their
   real `parse()` over a few fixture sentences and adjudicate its output
   against `gold_treebank_seed.conllu` as a third, informal comparison.
3. Note anything interesting in `TESTING.md` — it's a bonus observation, not
   a requirement. Your gate submission must still work, and be graded,
   using only the two committed fixture files.

Never merge their branch into yours, and never make your submission depend
on their branch existing.
