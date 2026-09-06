# Week 1 Tasks — Project 1: Word Segmentation & POS Tagging

**Branch:** `student/01-word-seg-pos`
**This week's scope:** exactly `plan.md`'s Task 1. Reading + research + one written
design decision. **No code under `src/vietnlp/...` yet** — Task 2 (compound
dictionary + skeleton segmenter) starts Week 2.

## Day 1 — Environment setup

1. Clone the repo and check out your branch (fork first if you don't have push
   access — see `project.md`'s "Contributing on GitHub" for the fork path):
   ```
   git clone git@github.com:phunghx/VietnamesModel.git
   cd VietnamesModel && git checkout student/01-word-seg-pos
   ```
2. Set up your environment:
   ```
   python3.11 -m venv .venv && source .venv/bin/activate
   pip install -e ".[dev]"
   ```
3. Confirm the inherited suite is green before you write anything:
   ```
   pytest tests -q
   ```
   If this fails on a clean checkout, stop and flag it to the professor —
   that's a branch problem, not something you did.

## Day 1-2 — Required reading, in this exact order

1. `student-projects/01-word-seg-pos/spec.md` — what you're building and why,
   including the "Known hard cases" list you'll need for Day 3-5.
2. `student-projects/01-word-seg-pos/plan.md` — the full 15-week breakdown.
   Task 1 (this week) is the first entry; skim the rest so you know where
   this week's decision is heading.
3. `student-projects/01-word-seg-pos/README.md` — quickstart + submission
   checklist.
4. `student-projects/01-word-seg-pos/project.md` — your exact contract:
   target signature, owned/forbidden paths, completion criteria. Read
   "You must not" twice — it's checked mechanically by the gate (scope step).
5. `src/vietnlp/interfaces/linguistics.py` — **in full, not skimmed.** This is
   the frozen `Token`/`SegmentedSentence` contract your output must satisfy.
   Every field's meaning and every validation rule lives here as
   docstrings/comments — you will refer back to this constantly.
6. `tests/golden/test_word_seg_pos_golden.py` — the test you're ultimately
   graded against. It is not a secret; read it now so you know the target,
   not just the destination described in prose.
7. `tests/fixtures/corpus/known_compounds.txt` — skim all ~48 entries.
8. `tests/fixtures/corpus/fixture_sentences.jsonl` — open it and read 15-20
   rows across all four `register` values (`formal`, `informal`, `teencode`,
   `non_diacritic`) so the register differences are concrete, not abstract.
9. Top-level `student-projects/README.md` — read "The unblocking mechanism"
   section once. You have no upstream stub to worry about (you're the root
   project), but this explains why Projects 2/3 will later build against
   *your* stub-shaped output, and why that matters for what "real" means.

## Day 2-4 — Research task

Find and read 2-3 sources on Vietnamese word segmentation. For background
only — per `spec.md`'s Non-Goals, none of this may end up wrapped as your
submitted `segment()`. Look specifically for:

- **How rule/dictionary-based segmenters handle compound ambiguity** — e.g.
  maximum-matching or longest-match algorithms over a compound dictionary.
  VLSP shared-task write-ups and academic papers on Vietnamese word
  segmentation are good sources.
- **How big a working compound dictionary typically needs to be** for
  reasonable coverage — this tells you whether 48 seed entries
  (`known_compounds.txt`) is anywhere near enough (it isn't; it's a floor).
- **What existing segmenters do differently on teencode / non-diacritic
  input** — you may look at `underthesea` or `VnCoreNLP`'s documented
  approach for ideas, but never at their code as something to wrap or copy.
- If you have the statistical-modeling background: what a small CRF or
  n-gram-based segmenter needs as training signal, and whether that's
  realistic against ~151 fixture sentences (it's a real constraint — say so
  in `DESIGN.md` if you go this route).

## Day 3-5 — Make your design decision

Pick **one** primary approach and commit to it in writing:

- **Dictionary-based maximum/longest matching** — build and grow a compound
  dictionary, seeded from `known_compounds.txt`, greedily matching the
  longest known compound at each position. This is the more tractable choice
  for most students in the time available.
- **A statistical approach** (small CRF/n-gram) — only if you have the
  background; you still need training data, which for this project means
  hand-labeling some or all of the 151 fixture sentences yourself, since
  there is no other labeled corpus available to you offline.

Then work through `spec.md`'s three named hard cases and write down your
handling plan for each — this is required `DESIGN.md` content, not optional:

1. **Compound ambiguity** — e.g. `"học sinh"` (student, one word) vs. `"học"`
   + `"sinh"` appearing separately elsewhere. What's your tie-breaking rule
   when a shorter and longer match both apply?
2. **Reduplication** (`"xinh xinh"`, `"đo đỏ"`) — one word or two? Pick a
   position and say why.
3. **Register-specific spelling** — teencode (`"ko"`, `"j"`, `"z"`) and
   non-diacritic text (`"hoc sinh"`) must segment into the *same logical
   words* as their formal equivalents where recoverable, and you must
   **never** rewrite `Token.form` to the formal spelling (CLAUDE.md: this is
   a distinct register, not noise). What's your strategy when diacritics are
   absent and a syllable boundary becomes genuinely ambiguous without them?

## Deliverable: `student-projects/01-word-seg-pos/DESIGN.md`

Create this file (it's referenced by name in `plan.md`'s Task 1). It must
contain:

- Your chosen segmentation approach and why you picked it over the
  alternative(s) you considered.
- Your compound-dictionary plan: source(s) beyond `known_compounds.txt`,
  and a rough target size (document the number once you have one — this
  becomes a `TESTING.md` topic in Week 13).
- Your written handling decision for each of the three hard cases above,
  with a concrete example sentence for each (real or constructed).

This file is not read by the mechanical gate — but `TESTING.md` (due Week
13-14) will reference back to it, and the professor's manual review checks
whether your finished implementation actually matches the reasoning you
wrote here. Write it like it will be read carefully, because it will be.

## Self-check before you call Week 1 done

- [ ] I can explain, out loud, to someone else, why I picked dictionary-based
      vs. statistical segmentation over the alternative.
- [ ] I have a concrete, written answer for compound ambiguity, reduplication,
      and register-specific spelling — not just "I'll figure it out later."
- [ ] I have read `tests/golden/test_word_seg_pos_golden.py` and understand,
      in general terms, what it checks (lossless syllable recombination,
      valid UPOS tags, known compounds surviving as one token).
- [ ] I have **not** written any code under `src/vietnlp/linguistics/` yet.

## What NOT to do this week

- Don't start `segmentation.py` yet — that's Week 2-3 (Task 2).
- Don't touch `src/vietnlp/interfaces/**`, `src/vietnlp/platform/**`,
  `src/vietnlp/acquisition/**`, `src/vietnlp/curation/**`,
  `tests/fixtures/**`, or `student-projects/_gate/**` — ever, for any
  reason. They're in your `forbidden_paths`; the gate's scope check fails on
  any diff there.
- Don't decide your submission will wrap `underthesea` or `VnCoreNLP` — that
  is permitted only as an optional *comparison baseline* reported in
  `TESTING.md`, never as the `segment()` you submit.
- Don't plan to "fix" teencode or non-diacritic spelling to formal Vietnamese
  anywhere in your design — preserve the register as-is.

## Commit & push your Week 1 work

```
git add student-projects/01-word-seg-pos/DESIGN.md
git commit -m "Week 1: research notes and segmentation approach decision"
git push origin student/01-word-seg-pos   # or your fork, if you lack push access
```

This is **not** a Pull Request yet — the PR happens once your gate passes, at
Week 15 (see `project.md`'s "Contributing on GitHub"). Pushing this commit now
just keeps your work backed up and visible if the professor wants to check
progress early.

## Looking ahead

Weeks 2-3 (Task 2) start real implementation: build your compound dictionary,
then TDD a skeleton `segment()` against hand-written sentences before running
it over the full fixture corpus in Week 4. Nothing here locks you in forever —
if further work changes your mind about part of the approach, update
`DESIGN.md` and explain the change in `TESTING.md` later.
