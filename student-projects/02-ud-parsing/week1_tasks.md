# Week 1 Tasks — Project 2: UD Dependency Parsing

**Branch:** `student/02-ud-parsing`
**This week's scope:** the first half of `plan.md`'s "Weeks 1-2 — Research &
design" task. Reading + research + a **leaning** design decision. Your
`DESIGN.md` doesn't have to be final this week — it has to exist, state your
current direction, and name exactly what's still open. You finalize it in
Week 2, before Week 3-4's skeleton parser. **No code under `src/vietnlp/...`
yet.**

## Day 1 — Environment setup

1. Clone and check out your branch (fork first if you lack push access — see
   `project.md`'s "Contributing on GitHub"):
   ```
   git clone git@github.com:phunghx/VietnamesModel.git
   cd VietnamesModel && git checkout student/02-ud-parsing
   ```
2. Set up your environment:
   ```
   python3.11 -m venv .venv && source .venv/bin/activate
   pip install -e ".[dev]"
   ```
3. Confirm the inherited suite is green:
   ```
   pytest tests -q
   ```
   Fails on a clean checkout → flag it to the professor, don't debug someone
   else's branch state.

## Day 1-2 — Required reading, in this exact order

1. `student-projects/02-ud-parsing/spec.md` — your goal, the folded-in
   linguistic grounding, and your Non-Goals.
2. `student-projects/02-ud-parsing/plan.md` — the 15-week breakdown (compact;
   this week is the first half of the first bullet).
3. `student-projects/02-ud-parsing/README.md` — quickstart + checklist.
4. `student-projects/02-ud-parsing/project.md` — your exact contract: target
   signature, owned/forbidden paths, completion criteria. Read "You must not"
   twice — it's checked mechanically (gate scope step).
5. `src/vietnlp/interfaces/ud.py` — **in full.** This is the frozen
   `DependencyParse` contract and `is_single_rooted_tree`/
   `validate_dependency_parse` you'll TDD against starting Week 3.
6. `src/vietnlp/interfaces/linguistics.py` — skim `SegmentedSentence`/`Token`,
   your actual input shape.
7. `src/vietnlp/interfaces/_common.py` — find `UD_DEPREL`, the frozen set of
   dependency relation labels every `deprel` you emit must come from.
8. `src/vietnlp/interfaces/stubs/linguistics_stub.py` — read
   `stub_segment()`'s actual implementation so you know precisely what
   you're building against (it's deliberately naive — don't copy its
   approach, just know its shape and limits).
9. `.claude/agents/vietnamese-linguist.md` — the full persona file. `spec.md`
   already folds in the relevant excerpt, but reading the whole file gives
   you the standard your parser is held to.
10. `tests/fixtures/corpus/fixture_sentences.jsonl` — read 15-20 rows,
    specifically looking for classifier phrases, coordination, and anything
    that looks like a serial verb construction, so Day 2-4's research has
    real examples to test against.

## Day 2-4 — Research task

Read the UD v2 dependency relation inventory
(universaldependencies.org/u/dep/index.html) at least once end to end so you
know what exists, then research these six Vietnamese-specific points
specifically — for each, write down what you find, even if incomplete:

1. **Classifier attachment** (`cái`, `con`, `chiếc`, `cuốn`) — does
   UD_Vietnamese-VTB attach these as `det` or `clf`? Find the convention;
   don't invent one.
2. **Coordination** — how `cc`/`conj` apply to Vietnamese coordinate
   structures.
3. **Serial verb constructions** (`đi mua`, `chạy ra`) — which verb is head?
   Per the linguist persona: inconsistency here destroys tree comparability
   more than any single tag error, so this needs a firm, written rule.
4. **`của`-possessive attachment.**
5. **Topic-comment fronting** — does the fronted topic get analyzed as
   subject, or does UD have a better-fitting relation?
6. **Final particles** (`à`, `nhé`, `đấy`) — how are these attached?

If your fixture corpus (`fixture_sentences.jsonl`) doesn't happen to contain
an example of one of these constructions, say so in `DESIGN.md` — that's a
legitimate documented gap, not a thing to fake.

## Day 3-5 — Make your leaning design decision

Decide, at least provisionally, between:

- **A rule/transition-based parser over your own grammar** — you write
  explicit rules driven by POS sequences and the constructions above. More
  tractable for most students in 15 weeks alongside coursework.
- **A trained statistical parser** — only if you have the background; note
  what you'd train it on (there is no treebank to train against except what
  you hand-annotate yourself from the fixture corpus — say so if you go this
  route).

For each of the six constructions above, write either (a) the convention
you're following, with a citation, or (b) "still researching — decision by
end of Week 2" if you're not there yet. It's fine for some of these to stay
open at the end of Week 1; it is not fine for the approach decision itself
(rule-based vs. statistical) to stay open past Week 2.

## Deliverable: `student-projects/02-ud-parsing/DESIGN.md`

Create this file. By end of Week 1 it must contain:

- Your leaning on parsing approach (rule/transition-based vs. statistical)
  and why.
- For each of the six named constructions: your finding/convention, or an
  explicit "still open" note with what you still need to check.
- Your plan for TDD'ing against `is_single_rooted_tree` from day one of
  Task 2 (Week 3) — a malformed tree is worse than a linguistically
  imperfect but valid one; say what your parser will do to guarantee a
  single root and no cycles even on sentences it handles badly otherwise.

By end of Week 2, this file should be fully finalized (approach locked in,
every construction either cited or explicitly scoped out with a documented
reason) before Week 3's skeleton parser starts.

## Self-check before you call Week 1 done

- [ ] I've read the UD v2 relation inventory at least once, not just this
      project's spec.md excerpt.
- [ ] I have a leaning on rule-based vs. statistical, and can say why.
- [ ] For at least half of the six named constructions, I have a real finding
      written down (not "TBD" for all six).
- [ ] I understand what `is_single_rooted_tree` checks and why it matters
      more than perfect linguistic accuracy at this stage.
- [ ] I have **not** written any code under `src/vietnlp/linguistics/` yet.

## What NOT to do this week

- Don't start `ud_parser.py` yet — Task 2 (skeleton parser) is Weeks 3-4.
- Don't touch `src/vietnlp/interfaces/**`, `src/vietnlp/platform/**`,
  `src/vietnlp/acquisition/**`, `src/vietnlp/curation/**`, Project 1's files
  (`segmentation.py`, `pos.py`), NER/coref files, `tests/fixtures/**`, or
  `student-projects/_gate/**` — all forbidden, checked by the gate's scope
  step.
- Don't pull Project 1's real branch yet, even if it's already pushed — you
  build and are graded against the frozen stub only
  (`interfaces.stubs.linguistics_stub.stub_segment`); the optional real-output
  sanity check (see `project.md`'s last section) is for later, once you have
  a working parser to sanity-check, not for Week 1 research.
- Don't try to resolve all six Vietnamese constructions by Friday — a
  documented "still open" is a legitimate Week 1 outcome; a guessed
  convention with no citation is not.

## Commit & push your Week 1 work

```
git add student-projects/02-ud-parsing/DESIGN.md
git commit -m "Week 1: UD relation research and parsing approach (draft)"
git push origin student/02-ud-parsing   # or your fork, if you lack push access
```

Not a Pull Request yet — that's Week 15, once your gate passes (see
`project.md`'s "Contributing on GitHub"). This commit just keeps your
progress visible and backed up.

## Looking ahead

Week 2 finishes this same research/design task: lock in your approach and
close out any "still open" constructions in `DESIGN.md`. Weeks 3-4 (Task 2)
then build a skeleton `parse()` against the stub segmenter's output on simple
sentences, TDD'd against `is_single_rooted_tree` from the first line of code.
