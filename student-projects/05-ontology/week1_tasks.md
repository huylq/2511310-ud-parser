# Week 1 Tasks — Project 5: Ontology Engineering

**Branch:** `student/05-ontology`
**This week's scope:** the first half of `plan.md`'s "Weeks 1-2 — Research &
design" task. Reading + research + a first-pass domain-class extension plan,
finalized in Week 2 before Weeks 3-4's reasoner setup. **No code / no TTL
edits yet.**

## Day 1 — Environment setup

1. Clone and check out your branch (fork first if you lack push access — see
   `project.md`'s "Contributing on GitHub"):
   ```
   git clone git@github.com:phunghx/VietnamesModel.git
   cd VietnamesModel && git checkout student/05-ontology
   ```
2. Set up your environment:
   ```
   python3.11 -m venv .venv && source .venv/bin/activate
   pip install -e ".[dev]"
   ```
3. Confirm the inherited suite is green: `pytest tests -q`. Fails on a clean
   checkout → flag it to the professor.

## Day 1-2 — Required reading, in this exact order

1. `student-projects/05-ontology/spec.md` — your goal and the full modelling
   discipline folded in from the ontology-engineer persona.
2. `student-projects/05-ontology/plan.md` — the 15-week breakdown.
3. `student-projects/05-ontology/README.md` — quickstart + checklist.
4. `student-projects/05-ontology/project.md` — your exact contract: target
   signature, owned/forbidden paths, completion criteria. Read "You must
   not" twice — the gate checks scope mechanically.
5. `src/vietnlp/interfaces/ontology.py` — read the module docstring **in
   full** before opening the TTL file. This is the frozen
   `OntologyIndividual`/`AlignmentRecord` contract.
6. `tests/fixtures/corpus/seed_upper_ontology.ttl` — **the whole file.** This
   is frozen: 8 upper classes (`Entity`, `Person`, `Organization`, `Place`,
   `Event`, `Artifact`, `Concept`, `TemporalEntity`). Every class you add
   later must attach under one of these. Note how the seed already encodes
   kinship-as-property (not as sibling classes) and `skos:closeMatch` for
   administrative units — you extend this pattern, you don't invent your
   own.
7. `tests/test_fixture_seed_ontology.py` — the test that already checks the
   seed's own consistency; your additions will eventually be checked the
   same way.
8. `.claude/agents/ontology-engineer.md` — the full persona file. `spec.md`
   folds in the core discipline, but read the whole file.
9. `tests/fixtures/corpus/fixture_sentences.jsonl` — read 15-20 rows and note
   every entity that would plausibly need an ontology individual: people,
   places, organizations. This is your source for Day 2-4's domain-class
   brainstorm — don't invent classes in the abstract, ground them in what
   the actual fixture corpus contains.

## Day 2-4 — Research task

1. **OWL 2 DL fundamentals** — read enough to know why staying in the DL
   profile matters (full OWL costs decidable reasoning) and what a reasoner
   consistency check actually verifies.
2. **The seed's 8 upper classes** — for each one, find at least one entity in
   the fixture corpus that would plausibly instantiate it (or a subclass of
   it you'll propose).
3. **`owl:sameAs` vs. `skos:closeMatch`** — read the seed file's own usage of
   these to understand the working distinction: `owl:sameAs` only for
   genuine identity; `skos:closeMatch` for the common case where a
   Vietnamese concept and a Wikidata item overlap but don't coincide
   (administrative divisions — `xã`, `huyện`, `tỉnh` — are the standing
   example).
4. **Property characteristics** (functional, transitive, symmetric) — read
   what each one commits you to, since these are exactly where a reasoner
   finds contradictions if you're not careful.

## Day 3-5 — Draft your domain-class extension plan

Working from the entities you found in Day 2-4, Step 2, list candidate new
domain classes — each attached under one of the 8 frozen upper classes, each
with:

- A parent class from the frozen 8.
- A Vietnamese label and an English label.
- A definition specific enough that an annotator could use it to decide
  membership (per the persona: "a class nobody can apply consistently is
  worse than an absent class").

Then apply the modelling discipline to your own list, deliberately:

- **Classes are not lexemes.** If any candidate class is really a property
  in disguise — Vietnamese kinship terms (`anh`, `chị`, `em`, `cô`, `chú`,
  `bác`) are the canonical trap, since they encode relative age/lineage, not
  a distinct kind of person — model it as a property on `Person`, not a
  sibling class.
- **Disjointness is an assertion, not decoration.** For each pair of
  sibling classes you propose, decide whether you actually mean "no
  individual can be both" before writing the axiom.
- **Alignment plan.** For each candidate class, note whether you expect its
  Wikidata alignment to be `owl:sameAs` or `skos:closeMatch`, and why.

## Deliverable: `student-projects/05-ontology/DESIGN.md`

Create this file. It must contain:

- The seed ontology's 8 upper classes, in your own words, each with one
  example individual from the fixture corpus you'd file under it.
- Your candidate domain-class list: parent class, Vietnamese label, English
  label, definition, for each.
- An explicit check that no candidate class is secretly a property (apply
  the kinship-term test to your own list, even if none of your classes are
  kinship-related — show you understand why the distinction matters).
- Your Wikidata-alignment plan per candidate class (`owl:sameAs` vs.
  `skos:closeMatch`), with the reasoning for each.
- Your `induce_individual()` mapping sketch: how NER labels
  (`PER`/`LOC`/`ORG`/`MISC`) map to your candidate classes.

## Self-check before you call Week 1 done

- [ ] I can explain the difference between `owl:sameAs` and
      `skos:closeMatch` using the `tỉnh` example, without looking it up.
- [ ] I can explain why Vietnamese kinship terms are modelled as properties,
      not classes, and I've checked my own candidate list against that
      pattern.
- [ ] Every candidate class I've proposed attaches under one of the 8 frozen
      upper classes — none of them are freestanding.
- [ ] I have **not** edited `seed_upper_ontology.ttl` or written any code
      under `src/vietnlp/ontology/` yet.

## What NOT to do this week

- Don't start `induction.py` or edit the TTL file yet — Task 2 (reasoner
  setup) is Weeks 3-4; TTL extension is Weeks 7-8.
- Don't touch `src/vietnlp/interfaces/**`, `src/vietnlp/platform/**`,
  `src/vietnlp/acquisition/**`, `src/vietnlp/curation/**`,
  `src/vietnlp/linguistics/**`, `tests/fixtures/**`, or
  `student-projects/_gate/**`.
- Don't propose a class that duplicates or contradicts one of the 8 frozen
  upper classes — extend them, never replace or shadow them.
- Don't design entity resolution/clustering (Project 7) or FOL predicate
  signatures (Project 6) — you consume neither and produce neither.
- Don't pull Project 3's real branch this week — you build and are graded
  against the frozen NER stub only.

## Commit & push your Week 1 work

```
git add student-projects/05-ontology/DESIGN.md
git commit -m "Week 1: domain-class candidates and alignment plan (draft)"
git push origin student/05-ontology   # or your fork, if you lack push access
```

Not a Pull Request yet — that's Week 15 (see `project.md`'s "Contributing on
GitHub"). This commit just keeps your progress visible and backed up.

## Looking ahead

Week 2 finishes this research/design task: lock in your candidate class list
and alignment plan. Weeks 3-4 (Task 2) then get a reasoner (e.g. `owlrl`)
running over the seed ontology alone, confirming it reports CONSISTENT
before you add anything of your own.
