# Student Projects — VietNLP P2-P5

P0 (platform) and P1 (acquisition + curation) are done on `main`. The 7
remaining CLAUDE.md modules (`linguistics/`, `treebank/`, `ontology/`,
`semantics/`, `oupm/`, `serving/`, `export/`) split into **9 independent
student projects**, one student per project, 15 weeks each, each student
using an AI coding assistant (Claude Code or a GPT-based tool) to
implement their own project and submit it for import back into this repo.

## The 9 projects

| # | Project | Directory | Produces |
|---|---|---|---|
| 1 | Word Segmentation & POS Tagging | [`01-word-seg-pos/`](01-word-seg-pos/) | `interfaces.linguistics.SegmentedSentence` |
| 2 | UD Dependency Parsing | [`02-ud-parsing/`](02-ud-parsing/) | `interfaces.ud.DependencyParse` |
| 3 | NER & Coreference Resolution | [`03-ner-coref/`](03-ner-coref/) | `interfaces.ner.NamedEntity`, `CorefChain` |
| 4 | Treebank Curation & Adjudication | [`04-treebank-adjudication/`](04-treebank-adjudication/) | `interfaces.treebank.AdjudicatedSentence` |
| 5 | Ontology Engineering | [`05-ontology/`](05-ontology/) | `interfaces.ontology.OntologyIndividual`, `AlignmentRecord` |
| 6 | Semantics / FOL | [`06-semantics/`](06-semantics/) | `interfaces.semantics.LogicalForm` |
| 7 | OUPM Entity Resolution | [`07-oupm/`](07-oupm/) | `interfaces.oupm.EntityCluster` |
| 8 | Serving API | [`08-serving/`](08-serving/) | FastAPI endpoints over `interfaces.serving` schemas |
| 9 | HF Export & Benchmark Harness | [`09-hf-export-bench/`](09-hf-export-bench/) | HF dataset dir + `interfaces.export.BenchmarkReport` |

Each project directory holds `spec.md` (design), `plan.md` (15-week task
breakdown), `gate.yaml` (mechanical grading config), `README.md`
(quickstart + submission checklist), and `TESTING.md` (a template the
student fills in with their own test-suite rationale). Project 1's
`spec.md`/`plan.md` are the full worked example; projects 2-9 are compact
skeletons at the time of writing — full task-by-task depth for them is a
follow-up authoring pass, not yet done.

## Topological integration order

```
1 ──► 2 ──┐
   └─► 3 ─┼──► 4
           │
           3 ──► 5
                 │
        {2,5} ──► 6
        {3,5} ──► 7
                     │
  {1,2,3,4,5,6,7} ──► 8
  {1,2,3,4,5,6,7} ──► 9
```

This is the order in which a REAL implementation should be swapped in for
its upstream stub after merge (see "The unblocking mechanism" below) —
**not a build-order constraint**. All 9 projects run in parallel from
week 1; nobody is blocked waiting on anyone else, by design.

## The unblocking mechanism: frozen `interfaces/` + stubs

`src/vietnlp/interfaces/` is a frozen contract package, one submodule per
hand-off boundary in the table above. Every submodule ships:

- A **frozen dataclass** shaped as a fixture-scale mirror of the real
  Postgres Gold columns (`platform/db/migrations/0001_core_schema.sql`).
- A **pandera schema** (same idiom as
  `acquisition/fixture_schema.py::FIXTURE_SCHEMA`).
- A `source: Literal["stub", "real"]` field on every dataclass. A stub
  generator (`interfaces.stubs.*`) always sets `"stub"`; your real
  implementation must set `"real"`. This is the field that lets a
  downstream project build against something real-shaped from week 1
  without anyone lying about what's actually finished, and lets the gate
  assert your own output is genuinely real while what you *consume* from
  upstream is allowed to still be a stub.
- A **stub generator** in `interfaces.stubs.*`: deterministic, cheap,
  schema-conformant, and explicitly linguistically naive (e.g. the
  segmentation stub splits on whitespace and tags everything `upos="X"`)
  — good enough to unblock you, never something to copy from.

Concretely: the Project 2 (UD parsing) student receives, already
committed, `interfaces.linguistics.SegmentedSentence`,
`interfaces.stubs.linguistics_stub.stub_segment()`, and the shared
fixture data. They build `parse(sentence) -> DependencyParse` against the
stub from day one. At merge time, the professor swaps in the real, merged
segmenter and re-runs Project 2's *unchanged* test suite — that swap is
the actual integration test, and it is not any student's job to perform.

`src/vietnlp/interfaces/**` and `student-projects/_gate/**` are frozen
and sit in every project's `forbidden_paths`. A genuine defect found
mid-course is fixed only by the professor, with a `SCHEMA_VERSION` bump
republished to all 9 branches — see "Interface change control" below.

## Repo layout: branches, not sandbox folders

Each project is a git branch (`student/01-word-seg-pos` …
`student/09-hf-export-bench`) cut from a frozen tag `curriculum-base`. A
student's code lives at its real final path from the first commit
(`src/vietnlp/linguistics/segmentation.py`, not a copy under a sandbox
directory) — this mirrors this repo's own worktree-based isolation idiom,
and it means merging a finished project back is a scoped
`git diff`/cherry-pick with zero path rewriting.

**Trade-off:** this polices "nothing outside your lane" via the gate's
scope diff after the fact, not a filesystem wall. Three students
(Projects 1/2/3) share the real `src/vietnlp/linguistics/` directory at
file granularity — each project's `gate.yaml` lists exactly which files
under it are theirs.

## The gate

One script, `student-projects/_gate/run_gate.sh <slug>`, parameterized by
each project's `gate.yaml`. Full details: `student-projects/_gate/README.md`.

**Automated PASS is the floor to merge, not the merge decision.** After a
PASS:

1. Read the golden-file test for gameability.
2. Spot-check the student's own tests against their `TESTING.md`
   rationale for genuine understanding vs. unreviewed assistant output.
3. Check Vietnamese-specific edge cases against the matching persona
   standard (folded into each project's `spec.md` already).
4. Confirm `interfaces/**` is untouched.
5. Merge, then re-run the full inherited suite (`pytest tests -q`) on
   `main`.

"Each student must use their own task, knowledge, test cases to verify"
is two independent bars: the gate (mechanical, identical script for all
9) is the floor to merge; the student's own test suite plus `TESTING.md`
is their demonstrated understanding — gated for presence (a required
minimum count and a fixed list of required input classes: all applicable
registers, one degenerate input, one adversarial input) but read by a
human for quality.

## Interface change control

A defect in `src/vietnlp/interfaces/**` is NOT fixed by any student
branch (it's in every `forbidden_paths` list). If you believe you've
found one:

1. Flag it to the professor with the specific dataclass/schema/validator
   and why it's wrong (not just "this doesn't work for my case").
2. The professor fixes it on `main`, bumps the affected module's
   `SCHEMA_VERSION`, and republishes the change to all 9
   `student/NN-*` branches (a merge or rebase from `main`).
3. Every affected project re-runs its own test suite against the updated
   contract before continuing.

This is rare and disruptive by design — that's why `interfaces/**` got
the most upfront review of anything in this curriculum, before any
student branch was cut.

## Fixture data status

| Artifact | Status |
|---|---|
| `tests/fixtures/corpus/fixture_sentences.jsonl`, `known_compounds.txt`, `seed_upper_ontology.ttl` | Frozen |
| `tests/fixtures/benchmark/*_stub.jsonl` | Frozen |
| `tests/fixtures/serving/gold_fixture.json` | Frozen (regenerate via `tests/fixtures/generate_gold_fixture.py` if an upstream stub changes) |
| `tests/fixtures/treebank/gold_treebank_seed.conllu`, `system_b_perturbed.conllu` | **PROVISIONAL** — see `tests/fixtures/treebank/PROVISIONAL.md`; pending professor sign-off |
| `tests/fixtures/oupm/oupm_coref_probe.jsonl` + gold clustering | **PROVISIONAL** — see `tests/fixtures/oupm/PROVISIONAL.md`; pending professor sign-off |

Projects 4 and 7 may build against their PROVISIONAL fixture immediately
— sign-off only affects whether it can later be treated as frozen ground
truth without revision.

## Submitting on GitHub

The repo is hosted at `git@github.com:phunghx/VietnamesModel.git`
(HTTPS: `https://github.com/phunghx/VietnamesModel.git`). `main`,
`curriculum-base`, and all 9 `student/NN-slug` branches are already pushed.
Each project's own `project.md` has the exact clone/branch/PR commands for
that project; the shared shape is:

1. Clone the repo (or fork it, if you don't have push access) and check out
   your assigned `student/NN-slug` branch.
2. Commit your work there directly (or to the same branch name on your
   fork).
3. Once your gate passes and `TESTING.md` is filled in, open a **Pull
   Request from `student/NN-slug` into `main`**. That PR is the unit the
   professor folds into the final concatenation of all 9 projects — do not
   merge it yourself.
4. Cross-project consumption is optional and one-directional only: a
   downstream project may pull an upstream project's already-pushed real
   branch for an *extra* sanity check (never a requirement, never merged
   into the downstream branch — see that project's "Optional: checking
   against a merged upstream project" section). Every project's gate always
   grades against the frozen stub/fixture, so nobody is blocked waiting on,
   or broken by, another student's pace.

## Submission checklist (every project)

- [ ] `student-projects/_gate/run_gate.sh <slug>` reports `Overall: PASS`.
- [ ] `TESTING.md` is filled in with real reasoning, not left as the
      template.
- [ ] `git diff curriculum-base...student/<slug> --stat` touches only
      files in your `owned_paths`.
- [ ] You can explain, unaided, any line of your own submission and why
      it's there.
- [ ] A Pull Request is open from `student/<slug>` into `main` on
      `github.com/phunghx/VietnamesModel`.
