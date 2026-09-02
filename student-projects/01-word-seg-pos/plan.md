# Project 1: Word Segmentation & POS Tagging — 15-Week Implementation Plan

> **For the student, working with Claude Code or a GPT-based assistant:**
> Work task-by-task, in order. Each task ends with a checkpoint you can
> verify yourself before moving on — don't start the next task until the
> current one's checkpoint passes. This plan tells you WHAT to build and
> WHAT it must satisfy (the interfaces, the gate, the golden test); it
> deliberately does not tell you HOW to segment Vietnamese words or which
> POS-tagging rules to write — that design work is the point of this
> project, and it is what `TESTING.md` (Task 10) asks you to explain.

**Goal:** see `spec.md`. **Read `spec.md` and
`src/vietnlp/interfaces/linguistics.py` in full before starting Task 1.**

**Gate:** `student-projects/_gate/run_gate.sh 01-word-seg-pos` — run it
after every task from Task 4 onward to see where you stand. See
`student-projects/_gate/README.md` for what each of its 8 steps checks.

## Global Constraints

- Python 3.11. Your code lives at `src/vietnlp/linguistics/segmentation.py`
  (and `pos.py` if you split tagging into its own module — both are in
  your `owned_paths`, see `gate.yaml`).
- Every object you return must set `source="real"` — never leave the
  default `source="stub"` on your own output (gate step 4 checks this).
- `src/vietnlp/interfaces/**` is read-only. If you think you've found a
  genuine defect in the frozen contract, don't work around it — flag it
  to the professor (see `student-projects/README.md`'s "Interface change
  control").
- Offline only. Your test suite must never call a network API or require
  Docker/Postgres/MinIO. `tests/fixtures/corpus/` is your entire corpus.
- TDD (CLAUDE.md working agreement): write a failing test before the code
  that makes it pass, for every non-trivial piece of segmentation or
  tagging logic.

---

### Task 1 (Week 1): Research & design decisions

No code yet. Read `spec.md`'s Architecture section, then research
Vietnamese word segmentation approaches (maximum matching, longest-match
dictionary methods, or a statistical approach if you have the
background). Decide your primary approach.

**Files:**
- Create: `student-projects/01-word-seg-pos/DESIGN.md` (your own notes —
  not graded directly, but Task 10's `TESTING.md` will reference it)

- [ ] **Step 1:** Read 2-3 sources on Vietnamese word segmentation (academic
  papers, VLSP shared task descriptions, or documentation of an existing
  segmenter's approach — for background only, never to be wrapped as your
  submission per spec.md's Non-Goals).
- [ ] **Step 2:** Write `DESIGN.md`: your chosen approach, how you'll build
  and grow your compound dictionary (if dictionary-based), and your plan
  for the hard cases spec.md lists (compound ambiguity, reduplication,
  register-specific spelling).
- [ ] **Checkpoint:** You can explain, out loud, why you picked this
  approach over the alternatives.

---

### Task 2 (Weeks 2-3): Compound dictionary + skeleton segmenter

**Files:**
- Create: `src/vietnlp/linguistics/__init__.py` (if not already present)
- Create: `src/vietnlp/linguistics/segmentation.py`
- Create: `src/vietnlp/linguistics/compounds.txt` (or embed in Python — your choice)
- Create: `tests/test_linguistics_segmentation.py`

**Interfaces:**
- Consumes: raw `(sent_id, register, text)` — see `spec.md`'s function
  signature.
- Produces: `interfaces.linguistics.SegmentedSentence` with `upos=None`
  on every token for now (POS tagging is Task 5) and `source="real"`.

- [ ] **Step 1:** Build your compound dictionary, seeded from
  `tests/fixtures/corpus/known_compounds.txt`, extended with your own
  research (spec.md's Open Risks: bigger than 48 entries).
- [ ] **Step 2:** TDD your word-segmentation function against a handful of
  hand-written test sentences (not yet the full fixture corpus) covering:
  a sentence with no compounds, one compound, two adjacent compounds, and
  one degenerate case (empty string).
- [ ] **Step 3:** Wire `segment()` to call your segmentation function and
  return a `SegmentedSentence` (tokens with `upos=None`).
- [ ] **Checkpoint:** `pytest tests/test_linguistics_segmentation.py -q`
  passes locally with your hand-written tests.

---

### Task 3 (Week 4): Segment the full fixture corpus

**Files:**
- Modify: `tests/test_linguistics_segmentation.py`

- [ ] **Step 1:** Add a test that calls `segment()` over all 151 rows of
  `tests/fixtures/corpus/fixture_sentences.jsonl` and asserts lossless
  syllable recombination (see `tests/golden/test_word_seg_pos_golden.py`
  for exactly what this check looks like — you may adapt it).
- [ ] **Step 2:** Fix whatever real sentences break your Task 2 skeleton.
  This is normal — the hand-written test sentences from Task 2 are much
  smaller than the real fixture corpus's variety.
- [ ] **Checkpoint:** Every fixture sentence segments without losing or
  duplicating a syllable.

---

### Task 4 (Week 5): Register handling — teencode & non-diacritic

**Files:**
- Modify: `src/vietnlp/linguistics/segmentation.py`
- Modify: `tests/test_linguistics_segmentation.py`

- [ ] **Step 1:** Write failing tests against the `teencode` and
  `non_diacritic` rows in `fixture_sentences.jsonl` specifically.
- [ ] **Step 2:** Handle them — this may mean your dictionary needs
  register-aware entries, or your segmentation function needs a fallback
  strategy when diacritics are absent. Never silently rewrite the surface
  form to formal Vietnamese (CLAUDE.md, spec.md's Architecture section).
- [ ] **Checkpoint:** Run
  `student-projects/_gate/run_gate.sh 01-word-seg-pos --skip-venv` for
  the first time. Expect step 3 (schema conformance) to now PASS. Steps
  5-8 will likely still fail or skip — that's expected this early.

---

### Task 5 (Weeks 6-7): POS tagging

**Files:**
- Create: `src/vietnlp/linguistics/pos.py` (or extend `segmentation.py`)
- Modify: `tests/test_linguistics_segmentation.py` (or a new
  `tests/test_linguistics_pos.py` — either is fine, gate.yaml's
  `own_test_glob` covers both)

**Interfaces:**
- Consumes: your own `SegmentedSentence` (pre-tagging).
- Produces: the same `SegmentedSentence`, now with every `Token.upos` set
  from `platform.agents.registry.UPOS_TAGSET`.

- [ ] **Step 1:** Build your closed-class word lists (`DET`, `CCONJ`, `ADP`,
  `PART`, `PRON`, `SCONJ`) — these are finite and enumerable in
  Vietnamese; get them right first, they cover a large share of tokens.
- [ ] **Step 2:** TDD your open-class heuristics (`NOUN` vs. `VERB` vs.
  `ADJ`) against hand-built examples covering spec.md's worked ambiguity
  case (`"cái đẹp"` vs. `"đẹp"` as predicate).
- [ ] **Step 3:** Run POS tagging over the full fixture corpus; assert every
  tag is in `UPOS_TAGSET` (this is also part of the golden test, but
  verify it yourself first).
- [ ] **Checkpoint:** `test_every_upos_is_in_the_frozen_tagset` in the
  golden test passes (`pytest tests/golden/test_word_seg_pos_golden.py -k
  upos_is_in`).

---

### Task 6 (Week 8): Golden test — compounds

**Files:**
- Modify: `src/vietnlp/linguistics/segmentation.py`

- [ ] **Step 1:** Run the full golden test:
  `pytest tests/golden/test_word_seg_pos_golden.py -q`.
- [ ] **Step 2:** Fix every `test_known_compounds_are_never_split` failure
  — each one names the exact sentence and compound that broke.
- [ ] **Checkpoint:** The full golden test file is green.

---

### Task 7 (Weeks 9-10): Adversarial & degenerate cases

**Files:**
- Modify: `tests/test_linguistics_segmentation.py`

- [ ] **Step 1:** Construct at least one genuinely adversarial input
  yourself — a real ambiguous compound boundary you found during Task 1's
  research, or a sentence where your dictionary and your tagger disagree
  about a word boundary. Write it up in `TESTING.md` (Task 10) with your
  reasoning, not just as a bare test.
- [ ] **Step 2:** Add degenerate-input tests: empty string, a single
  syllable, a string of only punctuation.
- [ ] **Step 3:** Add a negative/exception-path test: what does `segment()`
  do with `None` or a non-`str` `text`? (Raising is fine — assert it
  raises something sensible, don't let it silently return garbage.)
- [ ] **Checkpoint:** `student-projects/_gate/run_gate.sh 01-word-seg-pos`
  step 7 (own-suite presence) passes — it checks for exactly this: all 4
  registers, a compound case, a degenerate case, an adversarial case, all
  mentioned somewhere in your test suite.

---

### Task 8 (Week 11): Optional — DeepSeek refinement pass

Optional, bonus-graded (see `spec.md`). Skip to Task 9 if you're not
attempting this.

**Files:**
- Modify: `src/vietnlp/linguistics/segmentation.py` or `pos.py`

- [ ] **Step 1:** Read `platform/agents/registry.py`'s `AGENTS["pos-tagger"]`
  entry and `_validate_pos` in full.
- [ ] **Step 2:** Design a reconciliation rule: when does a DeepSeek
  suggestion override your rule-based tag, and when does your own tagger
  win? Write the rule down in `TESTING.md` before implementing it.
- [ ] **Step 3:** Implement, budget-check via `platform/agents/budget.py`
  before any real call, and test with a mocked client (never a live API
  call in your test suite — see `tests/test_client_flow.py` for the
  existing mocking pattern).
- [ ] **Checkpoint:** Your test suite still runs fully offline (mocked
  DeepSeek client only).

---

### Task 9 (Week 12): Performance & robustness pass

**Files:**
- Modify: `src/vietnlp/linguistics/segmentation.py`

- [ ] **Step 1:** Run your segmenter over all 151 fixture sentences and
  measure wall-clock time. If your dictionary lookup is doing anything
  worse than O(sentence length) per sentence, fix it now before it's a
  problem at real corpus scale (P1's target is ~100K sentences).
- [ ] **Step 2:** Re-read your own code once, cold, as if reviewing someone
  else's PR. Simplify anything you can't explain in one sentence.
- [ ] **Checkpoint:** No change in golden-test or gate results — this task
  is about code quality, not new behavior.

---

### Task 10 (Weeks 13-14): `TESTING.md` + full gate pass

**Files:**
- Create: `student-projects/01-word-seg-pos/TESTING.md`

- [ ] **Step 1:** Write `TESTING.md`: for each design decision from Task 1's
  `DESIGN.md`, state what you actually built and why, referencing specific
  tests. This is your demonstration of understanding (see `spec.md`'s
  Testing section) — a professor reads this by hand, not mechanically.
- [ ] **Step 2:** Run the full gate for real (not `--skip-venv`):
  `student-projects/_gate/run_gate.sh 01-word-seg-pos`.
- [ ] **Step 3:** Fix everything the gate reports, in order (it halts at
  the first failing step — fix that one, re-run, repeat).
- [ ] **Checkpoint:** Gate reports `Overall: PASS`.

---

### Task 11 (Week 15): Submission

- [ ] **Step 1:** Final read-through of your diff against `curriculum-base`:
  `git diff curriculum-base...student/01-word-seg-pos --stat` — confirm
  it touches only your `owned_paths`.
- [ ] **Step 2:** Open your submission for professor review per
  `student-projects/README.md`'s submission checklist.
- [ ] **Step 3 (after professor sign-off):** Merge. Project 2's team can
  now (optionally) swap your real segmenter in for their stub and re-run
  their own unchanged test suite — this is the actual integration test
  for your work, and it is not your task to perform.
