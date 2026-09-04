# Project 7: OUPM Entity Resolution

## Target

Build an open-universe entity resolver that clusters mentions (possibly across documents) into
entities, **inferring the number of distinct entities rather than assuming it** (the "open-universe" part).

```
cluster(entities: list[interfaces.ner.NamedEntity], chains: list[interfaces.ner.CorefChain]) -> list[interfaces.oupm.EntityCluster]
```

Consumes Project 3's output (stub or real) and Project 5's ontology types. `source` must be `"real"`.

**Test data is PROVISIONAL:** `tests/fixtures/oupm/oupm_coref_probe.jsonl` + gold clustering
(see `tests/fixtures/oupm/PROVISIONAL.md`). 12 documents, each built around one entity-resolution
trap (surname collision, diacritic variant, honorific stripping, same-name-different-people, …).

## Independence

This project is self-contained and runs in parallel with all the others — you wait on no one.
You build, test, and grade against Project 3's deterministic, committed NER/coref stub **and** the
frozen seed ontology types (Project 5) — both already committed, **never** any other student's real
output. At merge time the professor swaps the stubs for the real upstream modules and re-runs your
*unchanged* suite; that swap is the integration step, not your job.

## Required products

- `src/vietnlp/oupm/resolver.py` — the `cluster()` implementation (module: `vietnlp.oupm.resolver`).
- Any other files under `src/vietnlp/oupm/**` you need (sampler / similarity / evaluation).
- `tests/test_oupm_*.py` — your own tests.
- `TESTING.md` (in this directory) — filled in with real design-decision rationale, **including which
  clustering approach you took and why** (a reasoned trade-off, not a hidden shortcut).
- A passing gate: `student-projects/_gate/run_gate.sh 07-oupm` → `Overall: PASS`.

## Requirements

### Before you start
1. Work on branch `student/07-oupm` (cut from tag `curriculum-base`).
2. Set up the env: `python3.11 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"`.
3. Confirm the inherited suite is green: `pytest tests -q`.
4. Read in this order: `spec.md` → `plan.md` → `README.md` → `src/vietnlp/interfaces/oupm.py` in full.

### You may use
- The **stub** NER/coref output (from Project 3) and the frozen seed ontology types (Project 5).
- `interfaces.oupm.{EntityCluster, validate_entity_cluster}` — frozen contract.
- The PROVISIONAL probe + gold clustering for evaluation.

### You must not
- Touch `src/vietnlp/interfaces/**`, `src/vietnlp/platform/**`, `src/vietnlp/acquisition/**`,
  `src/vietnlp/curation/**`, `src/vietnlp/linguistics/**`, `src/vietnlp/ontology/**`,
  `tests/fixtures/**`, or `student-projects/_gate/**`.
- Do ontology modelling (Project 5) or within-document NER/coref (Project 3) — you consume both.

### Approach — the Vietnamese name channel (binding)
Generic coreference gets these wrong:
- **Surnames carry almost no information** (~40% of the population is `Nguyễn`). A surname match is
  near-worthless as evidence; weighting it like an English surname over-merges catastrophically.
- **Given-name reference is the norm:** `Nguyễn Văn Nam` is referred to as `Nam`, not `Nguyễn`.
- **Middle names** (`Văn`, `Thị`) are near-deterministic gender markers and weak identity evidence.
- **Honorifics** (`anh`, `chị`, `ông`, `bà`, `em`, `cô`) attach to given names and are not part of the name.
- **Diacritic-stripped variants** must map to the same canonical form (`Nguyen Van Nam` == `Nguyễn Văn Nam`).

A full MCMC sampler (Metropolis-Hastings with split-merge moves; report R-hat + ESS; evaluate with
B-cubed, CEAF and MUC) is ambitious for 15 weeks. A well-justified simpler approach (e.g. agglomerative
clustering over a hand-designed similarity function that correctly encodes the facts above, with
`posterior` as a similarity-derived confidence rather than a true MCMC posterior) is an acceptable,
honestly-scoped submission. When a result looks too good, check for leakage from the canonical name
into the mention features before believing it.

### Completion criteria
- Gate reports `Overall: PASS` (scope, clean install, schema, provenance `source=="real"`,
  your unit tests, golden test, ≥6 own tests with all required input classes: `surname`,
  `diacritic`, `degenerate`, `adversarial`, no live-only fixtures).
- Golden invariant: B³/CEAF/MUC against the probe's gold clustering (or a simpler, documented
  precision/recall on cluster membership if you scope evaluation down — say which and why).
- A surname-collision case correctly NOT merged; a diacritic-variant case correctly merged.
- `git diff curriculum-base...student/07-oupm --stat` touches only your `owned_paths`.
- You can explain any line of your submission and why it is there.

## Contributing on GitHub

The repo lives at `git@github.com:phunghx/VietnamesModel.git`
(HTTPS: `https://github.com/phunghx/VietnamesModel.git`). Your branch,
`student/07-oupm`, is already pushed there, cut from tag `curriculum-base`.

1. Clone and check out your branch:
   ```
   git clone git@github.com:phunghx/VietnamesModel.git
   cd VietnamesModel && git checkout student/07-oupm
   ```
   If you don't have push access to this repo, fork it on GitHub first, add
   your fork as a second remote, and push your commits there instead — open
   the PR in step 4 from your fork's `student/07-oupm` branch.
2. Commit early and often directly to `student/07-oupm` (or its copy on your
   fork). This branch's commit history is part of what gets reviewed, not
   just the final diff.
3. Periodically sync interface fixes: `git fetch origin && git merge origin/main`.
   The professor only ever changes `main` to republish a genuine
   `interfaces/**` defect fix (see "Interface change control" in the
   top-level `student-projects/README.md`) — this should be rare.
4. When `student-projects/_gate/run_gate.sh 07-oupm` reports `Overall: PASS`
   and `TESTING.md` is filled in, open a **Pull Request from `student/07-oupm`
   into `main`** on GitHub. That PR is your submission — it is what gets
   folded into the final concatenation of all 9 projects. Do not merge it
   yourself; the professor merges after the gate plus the manual review pass
   described in the top-level README.
5. Never touch `src/vietnlp/interfaces/**` or `student-projects/_gate/**` in
   your PR (both are in every project's `forbidden_paths` — the gate's scope
   check fails on any diff there). Found a real defect in one? Open a GitHub
   Issue describing it instead of editing it.

## Optional: checking against a merged upstream project

You are graded entirely against the frozen NER/coref stub, the frozen seed
ontology types, and the PROVISIONAL probe — none of this requires Project 3
or Project 5 to be finished. If either student has already pushed real,
`source="real"` commits to `student/03-ner-coref` and/or `student/05-ontology`
and you want an extra sanity check:

1. `git fetch origin student/03-ner-coref` and/or
   `git fetch origin student/05-ontology`.
2. In a throwaway script (never inside your committed test suite), import
   their real functions and feed real output into your `cluster()` instead
   of the stub's.
3. Note anything you learn in `TESTING.md` — it's a bonus observation. Your
   gate submission must still work, and be graded, using only the committed
   stubs and the PROVISIONAL probe.

Never merge either branch into yours, and never make your submission depend
on their branches existing.
