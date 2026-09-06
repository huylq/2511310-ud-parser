# Week 1 Tasks — Project 7: OUPM Entity Resolution

**Branch:** `student/07-oupm`
**This week's scope:** the first half of `plan.md`'s "Weeks 1-2 — Research &
design" task. Reading + research + an honestly-scoped approach decision,
finalized in Week 2 before Weeks 3-4's name-similarity function. **No code
under `src/vietnlp/...` yet.**

## Day 1 — Environment setup

1. Clone and check out your branch (fork first if you lack push access — see
   `project.md`'s "Contributing on GitHub"):
   ```
   git clone git@github.com:phunghx/VietnamesModel.git
   cd VietnamesModel && git checkout student/07-oupm
   ```
2. Set up your environment:
   ```
   python3.11 -m venv .venv && source .venv/bin/activate
   pip install -e ".[dev]"
   ```
3. Confirm the inherited suite is green: `pytest tests -q`. Fails on a clean
   checkout → flag it to the professor.

## Day 1-2 — Required reading, in this exact order

1. `student-projects/07-oupm/spec.md` — your goal, the generative structure,
   and the Vietnamese name channel folded in from the oupm-modeler persona.
2. `student-projects/07-oupm/plan.md` — the 15-week breakdown.
3. `student-projects/07-oupm/README.md` — quickstart + checklist.
4. `student-projects/07-oupm/project.md` — your exact contract: target
   signature, owned/forbidden paths, completion criteria. Read "You must
   not" twice — the gate checks scope mechanically.
5. `src/vietnlp/interfaces/oupm.py` — **in full.** This is the frozen
   `EntityCluster` contract.
6. `src/vietnlp/interfaces/ner.py` — skim `NamedEntity`/`CorefChain`, your
   actual input shape.
7. `tests/fixtures/oupm/PROVISIONAL.md` — **in full.** This names all 12
   entity-resolution traps in the probe fixture (surname collision,
   diacritic variant, honorific stripping, same-name-different-people, and
   more) and is provisional (pending professor sign-off), but you build
   against it regardless.
8. `tests/fixtures/oupm/oupm_coref_probe.jsonl` and
   `oupm_coref_probe_gold_clusters.jsonl` — open both, read every document,
   and match each one against its trap in `PROVISIONAL.md`'s table.
9. `.claude/agents/oupm-modeler.md` — the full persona file. `spec.md` folds
   in the core standard, but read the whole file, including the generative
   structure and sampler-discipline sections.

## Day 2-4 — Research task

1. **The Vietnamese name channel** — confirm each of these against the probe
   documents themselves, with real examples:
   - Surnames carry almost no information (~40% of the population is
     `Nguyễn`) — a surname match is close to worthless as evidence.
   - Given-name reference is the norm (`Nguyễn Văn Nam` → later `Nam`, not
     `Nguyễn`).
   - Middle names (`Văn`, `Thị`) are near-deterministic gender markers and
     weak identity evidence.
   - Honorifics attach to given names and are not part of the name.
   - Diacritic-stripped variants must map to the same canonical form
     (`Nguyen Van Nam` == `Nguyễn Văn Nam`).
2. **Approach options** — research **either**:
   - Chinese Restaurant Process (CRP) priors and Metropolis-Hastings with
     split-merge moves, if you're attempting a real MCMC sampler (ambitious
     for 15 weeks alongside coursework, per `spec.md` — attempt only with
     the background for it); **or**
   - Agglomerative clustering over a hand-designed similarity function, the
     explicitly-acceptable simpler alternative, provided the similarity
     function correctly encodes the name-channel facts above and you report
     `posterior` as a similarity-derived confidence rather than a true MCMC
     posterior.
3. **Evaluation metrics** — read what B-cubed, CEAF, and MUC each measure,
   and why the persona insists on reporting all three ("B-cubed alone hides
   systematic over-merging"). Also note the honest fallback: a simpler,
   documented precision/recall on cluster membership if you scope evaluation
   down — you must say which you used and why.

## Day 3-5 — Make your honestly-scoped approach decision

Pick your approach (MCMC or agglomerative) and write down, explicitly:

- Why you picked it, including the 15-week/coursework-load trade-off if
  that's part of your reasoning (per `spec.md`, this is a legitimate,
  expected argument, not a shortcut to hide).
- Which of the 12 probe traps you intend to handle well, and which you
  expect to handle only partially or not at all — an honestly-scoped
  omission, documented now, is worth more than a silently-broken attempt at
  full coverage discovered in Week 12.
- Your planned similarity-function features (if agglomerative) — specify the
  actual weight or near-zero weight you'll give surname evidence
  specifically, since over-weighting it is the single most common failure
  mode per the persona.
- Your planned evaluation metric(s) and why.

## Deliverable: `student-projects/07-oupm/DESIGN.md`

Create this file. It must contain:

- Your approach decision (MCMC vs. agglomerative) and the reasoning,
  including any honest scope trade-off.
- A walkthrough of all 12 probe traps from `PROVISIONAL.md`, each with your
  intended handling (or an honest "out of scope, here's why" for any you're
  deliberately not tackling).
- Your similarity-function feature list or generative-model sketch, with
  explicit treatment of surname weighting.
- Your evaluation-metric choice (B³/CEAF/MUC, or your scoped-down
  precision/recall) and why.

## Self-check before you call Week 1 done

- [ ] I can explain, using the probe's own examples, why a bare surname
      match must not drive a merge decision on its own.
- [ ] I've named which of the 12 traps I'm confident I'll handle and which
      I'm not — not a blanket "I'll handle everything."
- [ ] I know which evaluation metric(s) I'm implementing and why.
- [ ] I have **not** written any code under `src/vietnlp/oupm/` yet.

## What NOT to do this week

- Don't start `resolver.py` yet — Task 2 (name-similarity function) is
  Weeks 3-4.
- Don't touch `src/vietnlp/interfaces/**`, `src/vietnlp/platform/**`,
  `src/vietnlp/acquisition/**`, `src/vietnlp/curation/**`,
  `src/vietnlp/linguistics/**`, `src/vietnlp/ontology/**`,
  `tests/fixtures/**`, or `student-projects/_gate/**`.
- Don't design ontology modelling (Project 5) or within-document NER/coref
  (Project 3) — you consume both, you build neither.
- Don't pick "handle every trap perfectly" as your Week 1 plan without
  naming a fallback — an honestly-scoped subset beats a silently-broken
  attempt at everything.
- Don't pull Project 3's or Project 5's real branches this week — you build
  and are graded against the frozen stub/seed ontology and the PROVISIONAL
  probe only.

## Commit & push your Week 1 work

```
git add student-projects/07-oupm/DESIGN.md
git commit -m "Week 1: approach decision and trap-by-trap scoping (draft)"
git push origin student/07-oupm   # or your fork, if you lack push access
```

Not a Pull Request yet — that's Week 15 (see `project.md`'s "Contributing on
GitHub"). This commit just keeps your progress visible and backed up.

## Looking ahead

Week 2 finishes this research/design task: lock in your approach and your
per-trap scoping. Weeks 3-4 (Task 2) then build and unit-test your Vietnamese
name-similarity function in isolation — honorific stripping, diacritic
normalization, given-name-vs-surname weighting — before wiring it into any
clustering algorithm.
