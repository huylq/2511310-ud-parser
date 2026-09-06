# Week 1 Tasks — Project 3: NER & Coreference Resolution

**Branch:** `student/03-ner-coref`
**This week's scope:** the first half of `plan.md`'s "Weeks 1-2 — Research &
design" task. Reading + research + a leaning design decision, finalized in
Week 2 before Week 3-4's skeleton NER. **No code under `src/vietnlp/...`
yet.**

## Day 1 — Environment setup

1. Clone and check out your branch (fork first if you lack push access — see
   `project.md`'s "Contributing on GitHub"):
   ```
   git clone git@github.com:phunghx/VietnamesModel.git
   cd VietnamesModel && git checkout student/03-ner-coref
   ```
2. Set up your environment:
   ```
   python3.11 -m venv .venv && source .venv/bin/activate
   pip install -e ".[dev]"
   ```
3. Confirm the inherited suite is green: `pytest tests -q`. Fails on a clean
   checkout → flag it to the professor.

## Day 1-2 — Required reading, in this exact order

1. `student-projects/03-ner-coref/spec.md` — your goal and the linguistic
   grounding (Vietnamese name structure, given-name reference norm).
2. `student-projects/03-ner-coref/plan.md` — the 15-week breakdown.
3. `student-projects/03-ner-coref/README.md` — quickstart + checklist.
4. `student-projects/03-ner-coref/project.md` — your exact contract: target
   signatures, owned/forbidden paths, completion criteria. Read
   "You must not" twice — the gate checks scope mechanically.
5. `src/vietnlp/interfaces/ner.py` — **in full.** This is the frozen
   `NamedEntity`/`CorefChain` contract, and it has an explicit
   anti-hallucination note: locate spans against the source yourself, never
   trust a claimed offset. Read that note twice.
6. `src/vietnlp/interfaces/linguistics.py` — skim `SegmentedSentence`/`Token`,
   your actual input shape.
7. `src/vietnlp/interfaces/stubs/linguistics_stub.py` and
   `src/vietnlp/interfaces/stubs/ner_stub.py` — read both stubs' actual
   implementations. `ner_stub`'s naive approach (e.g. flagging capitalized
   tokens) is exactly the floor you need to clear, and knowing its blind
   spots tells you where your real NER needs to do better.
8. `tests/fixtures/corpus/fixture_sentences.jsonl` — read 15-20 rows and note
   every person/place/organization name you spot, plus every honorific
   attached to one, across all four registers.

## Day 2-4 — Research task

1. **NER approach:** compare a gazetteer + hand-written rules approach
   against a trained sequence tagger. Per `plan.md`, gazetteer + rules is a
   reasonable, defensible choice for a fixed-scale corpus (~151 sentences) —
   a trained tagger needs labeled training data you don't have, so only
   choose it if you're prepared to hand-label enough of the fixture corpus
   yourself to train on.
2. **Vietnamese naming structure:** confirm for yourself, with real examples
   from the fixture corpus, that Vietnamese personal names are
   Family + Middle + Given (e.g. `Nguyễn Văn Nam` = family `Nguyễn`, middle
   `Văn`, given `Nam`), and that a full name is **one** `PER` span — never
   split at a name-part boundary.
3. **Honorifics:** build a first-pass list of Vietnamese honorifics that
   attach to given names and must be **excluded** from the entity span:
   `anh`, `chị`, `ông`, `bà`, `em`, `cô`, plus any others you find in the
   fixture corpus (e.g. `chú`, `bác`, `thầy`). These are not part of the
   name.
4. **Given-name reference:** find or construct an example where a person is
   introduced with a full name and later referred to by given name alone
   (`Nguyễn Văn Nam` → later just `Nam`, never `Nguyễn`) — this is the
   opposite of English convention and is exactly what your coreference logic
   (Weeks 7-8) needs to get right.

## Day 3-5 — Make your leaning design decision

Write down:

- Your NER approach (gazetteer+rules vs. trained tagger) and why.
- Your honorific list (first-pass — you'll extend it as you find more).
- Your name-span boundary rule, stated precisely enough that you could apply
  it by hand to a sentence you haven't seen yet.
- Your initial coreference direction for Weeks 7-8: start with exact-string
  match plus honorific-stripped matching (a clear, documented improvement
  over the stub's exact-match-only baseline) — you don't have to design the
  full algorithm this week, just commit to this as your starting point.

## Deliverable: `student-projects/03-ner-coref/DESIGN.md`

Create this file. It must contain:

- Your NER approach and why.
- Your first-pass honorific list.
- Your name-span boundary rule (Family+Middle+Given as one span; honorifics
  excluded), with one worked example sentence showing exactly which tokens
  are in vs. out of the span.
- Your planned starting point for coreference (exact + honorific-stripped
  matching), and one worked example of two mentions of the same person that
  it correctly links.
- A note on how you'll handle a sentence with **zero** entities — this is a
  valid, common case per `spec.md`, not an error; your design should make
  clear `extract_entities()` returns an empty list, not raises.

## Self-check before you call Week 1 done

- [ ] I can point to a real sentence in the fixture corpus and correctly
      identify the `PER` span, excluding any honorific.
- [ ] I have a concrete honorific list, not just "I'll handle honorifics."
- [ ] I understand `interfaces/ner.py`'s anti-hallucination note: I will
      locate spans myself, never trust an offset a model reports.
- [ ] I have **not** written any code under `src/vietnlp/linguistics/` yet.

## What NOT to do this week

- Don't start `ner.py`/`coref.py` yet — Task 2 (skeleton NER) is Weeks 3-4.
- Don't touch `src/vietnlp/interfaces/**`, `src/vietnlp/platform/**`,
  `src/vietnlp/acquisition/**`, `src/vietnlp/curation/**`, Project 1/2's
  files, `tests/fixtures/**`, or `student-projects/_gate/**`.
- Don't design entity clustering across documents or open-universe entity
  counting — that's Project 7's job; you produce within-document chains only.
- Don't design ontology class assignment (`PER` → `Person`, etc.) — that's
  Project 5's job; you emit the coarse NER label only.
- Don't pull Project 1's real branch this week — you build and are graded
  against the frozen stub only.

## Commit & push your Week 1 work

```
git add student-projects/03-ner-coref/DESIGN.md
git commit -m "Week 1: NER/coref approach and naming-rule design (draft)"
git push origin student/03-ner-coref   # or your fork, if you lack push access
```

Not a Pull Request yet — that's Week 15 (see `project.md`'s "Contributing on
GitHub"). This commit just keeps your progress visible and backed up.

## Looking ahead

Week 2 finishes this research/design task: lock in your NER approach and
finalize your honorific list and span rule. Weeks 3-4 (Task 2) then TDD a
skeleton NER against hand-written sentences (one full name, one
honorific+name, zero entities) before running it over the full fixture
corpus in Weeks 5-6.
