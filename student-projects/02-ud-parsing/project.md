# Project 2: UD Dependency Parsing

## Target

Build a UD v2 dependency parser, aligned with UD_Vietnamese-VTB.

```
parse(sentence: interfaces.linguistics.SegmentedSentence) -> interfaces.ud.DependencyParse
```

Given a segmented sentence (from Project 1 — its **stub**,
`interfaces.stubs.linguistics_stub.stub_segment`, until Project 1 merges for real),
produce a full dependency tree per sentence: `head` (CoNLL-U convention, 0 = root)
and `deprel` (from `interfaces._common.UD_DEPREL`) for every token.
`source` must be `"real"`.

## Independence

This project is self-contained and runs in parallel with all the others — you wait on no one.
You build, test, and grade against the deterministic, committed stub
(`interfaces.stubs.linguistics_stub.stub_segment`) — **never** against Project 1's real output,
which you do not need and never wait for. At merge time the professor swaps the stub for the real
segmenter and re-runs your *unchanged* test suite; that swap is the integration step, not your job.

## Required products

- `src/vietnlp/linguistics/ud_parser.py` — the `parse()` implementation.
- `tests/test_linguistics_ud_parser*.py` — your own tests.
- `TESTING.md` (in this directory) — filled in with real design-decision rationale.
- A passing gate: `student-projects/_gate/run_gate.sh 02-ud-parsing` → `Overall: PASS`.

## Requirements

### Before you start
1. Work on branch `student/02-ud-parsing` (cut from tag `curriculum-base`).
2. Set up the env: `python3.11 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"`.
3. Confirm the inherited suite is green: `pytest tests -q`.
4. Read in this order: `spec.md` → `plan.md` → `README.md` → `src/vietnlp/interfaces/ud.py` in full.

### You may use
- The **stub** segmenter output (from Project 1) as your input source.
- `interfaces.ud.{DependencyParse, validate_dependency_parse, is_single_rooted_tree}` — frozen contract.
- `tests/fixtures/corpus/fixture_sentences.jsonl` for the sentences you parse (via the stub segmenter).
- UD v2 guidelines + UD_Vietnamese-VTB published conventions (cite them, don't reinvent).

### You must not
- Touch `src/vietnlp/interfaces/**`, `src/vietnlp/platform/**`, `src/vietnlp/acquisition/**`,
  `src/vietnlp/curation/**`, or Project 1's files (`segmentation.py`, `pos.py`), NER/coref files,
  `tests/fixtures/**`, or `student-projects/_gate/**`.
- Do word segmentation / POS (Project 1's job) or treebank adjudication (Project 4's job).
- Call a network API (offline-only tests).

### Approach
Decide your parsing approach (rule-based / transition-based over your own grammar, or a
trained statistical parser). TDD against `interfaces.ud.is_single_rooted_tree` from day one
(a malformed tree is worse than a linguistically imperfect but valid one). Handle the
Vietnamese-specific constructions deliberately and cite your convention for each:
classifier attachment (`clf` vs `det`), coordination (`cc`/`conj`), serial verb constructions
(consistent head choice), `của`-possessive, topic-comment fronting, final particles.

### Completion criteria
- Gate reports `Overall: PASS` (scope, clean install, schema + `is_single_rooted_tree`,
  provenance `source=="real"`, your unit tests, golden test, ≥6 own tests with all required
  input classes: `clf`, `classifier`, `cycle`, `degenerate`, `adversarial`, no live-only fixtures).
- `TESTING.md` explains each construction's head-choice / attachment decision.
- `git diff curriculum-base...student/02-ud-parsing --stat` touches only your `owned_paths`.
- You can explain any line of your submission and why it is there.

## Contributing on GitHub

The repo lives at `git@github.com:phunghx/VietnamesModel.git`
(HTTPS: `https://github.com/phunghx/VietnamesModel.git`). Your branch,
`student/02-ud-parsing`, is already pushed there, cut from tag
`curriculum-base`.

1. Clone and check out your branch:
   ```
   git clone git@github.com:phunghx/VietnamesModel.git
   cd VietnamesModel && git checkout student/02-ud-parsing
   ```
   If you don't have push access to this repo, fork it on GitHub first, add
   your fork as a second remote, and push your commits there instead — open
   the PR in step 4 from your fork's `student/02-ud-parsing` branch.
2. Commit early and often directly to `student/02-ud-parsing` (or its copy
   on your fork). This branch's commit history is part of what gets
   reviewed, not just the final diff.
3. Periodically sync interface fixes: `git fetch origin && git merge origin/main`.
   The professor only ever changes `main` to republish a genuine
   `interfaces/**` defect fix (see "Interface change control" in the
   top-level `student-projects/README.md`) — this should be rare.
4. When `student-projects/_gate/run_gate.sh 02-ud-parsing` reports
   `Overall: PASS` and `TESTING.md` is filled in, open a **Pull Request from
   `student/02-ud-parsing` into `main`** on GitHub. That PR is your
   submission — it is what gets folded into the final concatenation of all 9
   projects. Do not merge it yourself; the professor merges after the gate
   plus the manual review pass described in the top-level README.
5. Never touch `src/vietnlp/interfaces/**` or `student-projects/_gate/**` in
   your PR (both are in every project's `forbidden_paths` — the gate's scope
   check fails on any diff there). Found a real defect in one? Open a GitHub
   Issue describing it instead of editing it.

## Optional: checking against a merged upstream project

You are graded entirely against the frozen stub
(`interfaces.stubs.linguistics_stub.stub_segment`) — that never changes, and
you never have to wait on Project 1. If Project 1's student has already
pushed real, `source="real"` commits to `student/01-word-seg-pos` and you
want an extra sanity check:

1. `git fetch origin student/01-word-seg-pos`
2. In a throwaway script (never inside your committed test suite), import
   `vietnlp.linguistics.segmentation.segment` directly from that branch's
   checkout and feed its real output into your `parse()` instead of the
   stub's.
3. Note anything you learn in `TESTING.md` as a bonus observation — it does
   not change your contract: both stub and real output validate against the
   identical frozen `SegmentedSentence` schema, so your gate submission must
   still work, and be graded, using only the stub.

Never merge their branch into yours, and never make your submission depend
on their branch existing — it may land after yours, change after yours, or
not land in time at all.
