# Project 5: Ontology Engineering

## Target

Build an ontology-induction module that maps a recognized named entity to an OWL 2 individual
in the upper ontology, extends the seed ontology with new domain classes/properties, and aligns
your classes to Wikidata.

```
induce_individual(entity: interfaces.ner.NamedEntity) -> interfaces.ontology.OntologyIndividual
```

Consumes Project 3's NER output (stub or real). The seed ontology
(`tests/fixtures/corpus/seed_upper_ontology.ttl`) is **frozen** at 8 upper classes
(`Entity`, `Person`, `Organization`, `Place`, `Event`, `Artifact`, `Concept`, `TemporalEntity`) —
every class you add must attach under one of these (see `tests/test_fixture_seed_ontology.py`).
Also produce `AlignmentRecord`s linking your classes to Wikidata. `source` must be `"real"`.

## Independence

This project is self-contained and runs in parallel with all the others — you wait on no one.
You build, test, and grade against Project 3's deterministic, committed NER stub **and** the frozen
seed ontology — **never** against any other student's real output, which you do not need and never
wait for. At merge time the professor swaps the stub for the real NER output and re-runs your
*unchanged* suite; that swap is the integration step, not your job.

## Required products

- `src/vietnlp/ontology/induction.py` — the `induce_individual()` implementation (module: `vietnlp.ontology.induction`).
- Any other files under `src/vietnlp/ontology/**` you need (reasoner checks, alignment).
- Your extension of `seed_upper_ontology.ttl` (new domain classes/properties, each with a
  Vietnamese label, an English label, and a definition that lets an annotator decide membership).
- `tests/test_ontology_*.py` — your own tests.
- `TESTING.md` (in this directory) — filled in with real design-decision rationale.
- A passing gate: `student-projects/_gate/run_gate.sh 05-ontology` → `Overall: PASS`.

## Requirements

### Before you start
1. Work on branch `student/05-ontology` (cut from tag `curriculum-base`).
2. Set up the env: `python3.11 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"`.
3. Confirm the inherited suite is green: `pytest tests -q`.
4. Read in this order: `spec.md` → `plan.md` → `README.md` → `src/vietnlp/interfaces/ontology.py`
   docstring + the seed TTL file itself, before adding anything.

### You may use
- The **stub** NER output (from Project 3) as your input source.
- `interfaces.ontology.{OntologyIndividual, AlignmentRecord, validate_ontology_individuals}` — frozen contract.
- An OWL 2 reasoner for consistency checking (the seed already encodes the correct patterns — extend, don't contradict).

### You must not
- Touch `src/vietnlp/interfaces/**`, `src/vietnlp/platform/**`, `src/vietnlp/acquisition/**`,
  `src/vietnlp/curation/**`, `src/vietnlp/linguistics/**`, `tests/fixtures/**`, or `student-projects/_gate/**`.
- Do entity resolution / clustering (Project 7) or FOL predicate signatures (Project 6).

### Approach — modelling discipline (binding)
- **Classes are not lexemes.** Vietnamese kinship terms (`anh`, `chị`, `em`, `cô`, `chú`, `bác`)
  encode relative age/lineage; model them as ONE class plus properties, not sixteen sibling classes.
- **Disjointness is an assertion, not decoration.** Add a disjointness axiom only when you mean it.
- **Wikidata alignment:** `owl:sameAs` only for genuine identity; `skos:closeMatch` for the common
  overlap-but-not-coincide case (administrative divisions `xã`/`huyện`/`tỉnh` are the usual trap).
- **Justify every property characteristic** (functional, transitive, symmetric) — that is where
  reasoners find contradictions. On an inconsistency: get the reasoner's justification set, find the
  minimal axiom set, and say which axiom is *wrong* (not merely which to remove to silence it).

### Completion criteria
- Gate reports `Overall: PASS` (scope, clean install, schema, provenance `source=="real"`,
  your unit tests, golden test, ≥6 own tests with all required input classes: `kinship`,
  `closematch`, `degenerate`, `adversarial`, no live-only fixtures).
- Golden invariant: the reasoner reports the ontology + your induced individuals CONSISTENT.
- `TESTING.md` explains your class/property choices and alignment decisions.
- `git diff curriculum-base...student/05-ontology --stat` touches only your `owned_paths`.
- You can explain any line of your submission and why it is there.

## Contributing on GitHub

The repo lives at `git@github.com:phunghx/VietnamesModel.git`
(HTTPS: `https://github.com/phunghx/VietnamesModel.git`). Your branch,
`student/05-ontology`, is already pushed there, cut from tag
`curriculum-base`.

1. Clone and check out your branch:
   ```
   git clone git@github.com:phunghx/VietnamesModel.git
   cd VietnamesModel && git checkout student/05-ontology
   ```
   If you don't have push access to this repo, fork it on GitHub first, add
   your fork as a second remote, and push your commits there instead — open
   the PR in step 4 from your fork's `student/05-ontology` branch.
2. Commit early and often directly to `student/05-ontology` (or its copy on
   your fork). This branch's commit history is part of what gets reviewed,
   not just the final diff.
3. Periodically sync interface fixes: `git fetch origin && git merge origin/main`.
   The professor only ever changes `main` to republish a genuine
   `interfaces/**` defect fix (see "Interface change control" in the
   top-level `student-projects/README.md`) — this should be rare.
4. When `student-projects/_gate/run_gate.sh 05-ontology` reports
   `Overall: PASS` and `TESTING.md` is filled in, open a **Pull Request from
   `student/05-ontology` into `main`** on GitHub. That PR is your
   submission — it is what gets folded into the final concatenation of all 9
   projects. Do not merge it yourself; the professor merges after the gate
   plus the manual review pass described in the top-level README.
5. Never touch `src/vietnlp/interfaces/**` or `student-projects/_gate/**` in
   your PR (both are in every project's `forbidden_paths` — the gate's scope
   check fails on any diff there). Found a real defect in one? Open a GitHub
   Issue describing it instead of editing it.

## Optional: checking against a merged upstream project

You are graded entirely against the frozen NER stub
(`interfaces.stubs.ner_stub.stub_extract_entities`) — that never changes,
and you never have to wait on Project 3. If Project 3's student has already
pushed real, `source="real"` commits to `student/03-ner-coref` and you want
an extra sanity check:

1. `git fetch origin student/03-ner-coref`
2. In a throwaway script (never inside your committed test suite), import
   `vietnlp.linguistics.ner.extract_entities` directly from that branch's
   checkout and feed its real output into your `induce_individual()` instead
   of the stub's.
3. Note anything you learn in `TESTING.md` — it's a bonus observation. Both
   stub and real output validate against the identical frozen `NamedEntity`
   schema, so your gate submission must still work, and be graded, using
   only the stub.

Never merge their branch into yours, and never make your submission depend
on their branch existing.
