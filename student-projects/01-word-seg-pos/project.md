# Project 1: Word Segmentation & POS Tagging

## Target

Build a word segmenter and POS tagger for Vietnamese, one of the syllable-segmented,
not word-segmented, languages (e.g., `"sinh viên học bài"` is 4 syllables / 3 words).
Every downstream project (UD parsing, NER, treebank, ontology, semantics) depends on
this one.

```
segment(sent_id: str, register: str, text: str) -> interfaces.linguistics.SegmentedSentence
```

Given one raw sentence, produce an ordered sequence of word tokens (each possibly
spanning several syllables), each tagged with a UD v2 part of speech.
`source` on the returned object must be `"real"`.

## Independence

This project is self-contained and runs in parallel with all the others — you wait on no one.
It is the root project: you consume raw sentences, not any other student's output. Everything you
need is already committed to your branch — the frozen output contract
(`src/vietnlp/interfaces/linguistics.py`), the shared offline fixtures, the golden test, and the
gate. At merge time the professor swaps the downstream stub for your real module and re-runs *their*
unchanged suites — that is the integration step, and it is not your job.

## Required products

- `src/vietnlp/linguistics/segmentation.py` — the `segment()` implementation.
- `src/vietnlp/linguistics/pos.py` — POS tagging (optional separate module).
- `src/vietnlp/linguistics/__init__.py` — exports.
- `tests/test_linguistics_segmentation*.py`, `tests/test_linguistics_pos*.py` — your own tests.
- `TESTING.md` (in this directory) — filled in with real design-decision rationale.
- A passing gate: `student-projects/_gate/run_gate.sh 01-word-seg-pos` → `Overall: PASS`.

## Requirements

### Before you start
1. Work on branch `student/01-word-seg-pos` (cut from tag `curriculum-base`).
2. Set up the env: `python3.11 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"`.
3. Confirm the inherited suite is green: `pytest tests -q`.
4. Read in this order: `spec.md` (what/why) → `plan.md` (15-week breakdown) →
   `README.md` quickstart → `src/vietnlp/interfaces/linguistics.py` in full.
5. Read the golden test `tests/golden/test_word_seg_pos_golden.py` now — it is not a secret.

### You may use
- `tests/fixtures/corpus/fixture_sentences.jsonl` (151 sentences, 4 registers) — your entire offline corpus.
- `tests/fixtures/corpus/known_compounds.txt` (~48 compounds your segmenter must never split).
- `interfaces.linguistics.{Token, SegmentedSentence, SEGPOS_SCHEMA, validate_segmented_sentence}` — frozen output contract.
- `platform.agents.registry.UPOS_TAGSET` — the 17-tag UD v2 POS set.

### You must not
- Touch `src/vietnlp/interfaces/**`, `src/vietnlp/platform/**`, `src/vietnlp/acquisition/**`,
  `src/vietnlp/curation/**`, `tests/fixtures/**`, or `student-projects/_gate/**`.
- Call a network API (offline-only tests).
- Wrap `underthesea` / `VnCoreNLP` as the submitted `segment()` — allowed only as a
  comparison baseline reported in `TESTING.md`.
- "Fix" teencode / non-diacritic spelling in `Token.form` (preserve the register).

### Approach
Pick ONE primary method and implement it for real: an original rule/dictionary-based
segmenter (maximum/longest-match over a compound dictionary you build) or a statistical
model (e.g. CRF/n-gram) if you have the background. Handle compound ambiguity,
reduplication, and register-specific spelling deliberately (document each in `TESTING.md`).
An optional DeepSeek refinement pass is a bonus, not a requirement.

### Completion criteria
- Gate reports `Overall: PASS` (8 steps: scope, clean install, schema, provenance `source=="real"`,
  your unit tests, golden test, ≥6 own tests with all required input classes, no live-only fixtures).
- `TESTING.md` explains every design decision (dictionary source, ambiguity tie-breaking, reduplication).
- `git diff curriculum-base...student/01-word-seg-pos --stat` touches only your `owned_paths`.
- You can explain any line of your submission and why it is there.

## Contributing on GitHub

The repo lives at `git@github.com:phunghx/VietnamesModel.git`
(HTTPS: `https://github.com/phunghx/VietnamesModel.git`). Your branch,
`student/01-word-seg-pos`, is already pushed there, cut from tag
`curriculum-base`.

1. Clone and check out your branch:
   ```
   git clone git@github.com:phunghx/VietnamesModel.git
   cd VietnamesModel && git checkout student/01-word-seg-pos
   ```
   If you don't have push access to this repo, fork it on GitHub first, add
   your fork as a second remote, and push your commits there instead — open
   the PR in step 4 from your fork's `student/01-word-seg-pos` branch.
2. Commit early and often directly to `student/01-word-seg-pos` (or its copy
   on your fork). This branch's commit history is part of what gets
   reviewed, not just the final diff.
3. Periodically sync interface fixes: `git fetch origin && git merge origin/main`.
   The professor only ever changes `main` to republish a genuine
   `interfaces/**` defect fix (see "Interface change control" in the
   top-level `student-projects/README.md`) — this should be rare.
4. When `student-projects/_gate/run_gate.sh 01-word-seg-pos` reports
   `Overall: PASS` and `TESTING.md` is filled in, open a **Pull Request from
   `student/01-word-seg-pos` into `main`** on GitHub. That PR is your
   submission — it is what gets folded into the final concatenation of all 9
   projects. Do not merge it yourself; the professor merges after the gate
   plus the manual review pass described in the top-level README.
5. Never touch `src/vietnlp/interfaces/**` or `student-projects/_gate/**` in
   your PR (both are in every project's `forbidden_paths` — the gate's scope
   check fails on any diff there). Found a real defect in one? Open a GitHub
   Issue describing it instead of editing it.

## Your output feeding forward (informational)

You have no upstream project — you consume only the raw fixture corpus.
Once your PR is open, Projects 2 and 3 may optionally pull your branch to
sanity-check their own module against your real segmenter instead of the
stub (see their `project.md`, "Optional: checking against a merged upstream
project"). This is informational only: it never changes your own
requirements, your `owned_paths`, or your gate.
