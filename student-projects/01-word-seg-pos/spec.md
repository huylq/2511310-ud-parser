# Project 1: Word Segmentation & POS Tagging — Design

Worked template for the student-projects curriculum. Every other project's
`spec.md` follows this same shape (see `student-projects/README.md`).

## Goal

Vietnamese orthography is **syllable-segmented, not word-segmented**
(CLAUDE.md). `"sinh viên học bài"` is four syllables but three words
(`sinh_viên`, `học`, `bài`) — a student, a study, a lesson. Every
downstream project in this curriculum (UD parsing, NER, treebank,
ontology, semantics) assumes words as its unit of analysis, so this is
the one project every other project transitively depends on
(`1 -> {2,3}`, `{1,2,3} -> 4`, `{1..7} -> 8/9` — see
`student-projects/README.md`'s dependency graph).

Build a **word segmenter and POS tagger**:

```
segment(sent_id: str, register: str, text: str) -> interfaces.linguistics.SegmentedSentence
```

Given one raw sentence, produce an ordered sequence of word tokens (each
possibly spanning several syllables), each tagged with a UD v2 part of
speech. `source` on the returned object must be `"real"`.

## What already exists (reused, not rebuilt)

- `interfaces.linguistics.{Token, SegmentedSentence, SEGPOS_SCHEMA,
  validate_segmented_sentence}` — the frozen output contract. Read
  `src/vietnlp/interfaces/linguistics.py` in full before writing any code;
  every field's meaning and every schema constraint is documented there.
- `platform.agents.registry.UPOS_TAGSET` — the 17-tag UD v2 set every
  `Token.upos` must come from. The same tagset DeepSeek-refined POS output
  is validated against (`registry.py::_validate_pos`) if this project
  later adds a model-assisted refinement pass — see "DeepSeek refinement
  (optional, Task 9)" below.
- `tests/fixtures/corpus/fixture_sentences.jsonl` — 151 sentences, 4
  registers (`formal`, `informal`, `teencode`, `non_diacritic`), your
  entire offline development and test corpus. Never call a network API.
- `tests/fixtures/corpus/known_compounds.txt` — ~48 hand-picked
  multi-syllable words your segmenter must never split.
- `tests/golden/test_word_seg_pos_golden.py` — the professor-authored
  golden-file test your submission is graded against (read it now; it is
  not a secret). It checks: lossless syllable recombination, valid UPOS
  tags, and that every occurring `known_compounds.txt` entry survives as
  one token.

## Architecture

Two responsibilities, one function boundary. You may implement them as
two internal functions (`_segment_words` then `_tag_pos`) or one combined
pass — `segment()`'s external contract is all the gate checks.

```
raw text ──► word segmentation ──► POS tagging ──► SegmentedSentence
             (syllable → word)      (word → UD tag)
```

### Word segmentation

Pick ONE primary approach and implement it for real — an original
rule/dictionary-based segmenter (maximum-matching or longest-match against
a compound dictionary you build, seeded from `known_compounds.txt` and
extended with your own research) or a statistical approach (e.g. a small
CRF/n-gram model you train, if you have the background) are both
acceptable. **Wrapping `underthesea` or `VnCoreNLP` is permitted only as
an optional comparison baseline you may report in `TESTING.md` — it must
never be the submitted `segment()` implementation.** The point of this
project is to build genuine understanding of Vietnamese word-formation,
not to import it.

Known hard cases to research and handle deliberately (document your
decision for each in `TESTING.md`):
- Compound ambiguity: `"học sinh"` (student, one word) vs. `"học"` +
  `"sinh"` in `"học sinh vật"` (studying biology — rare, but the general
  ambiguity class is real).
- Reduplication (`"xinh xinh"`, `"đo đỏ"`) — is this one word or two?
- Register-specific spelling: teencode (`"ko"`, `"j"`, `"z"`) and
  non-diacritic text (`"hoc sinh"`) must segment into the SAME logical
  words as their formal-register equivalents where recoverable — never
  silently "fix" the spelling in `Token.form` (CLAUDE.md: these are a
  distinct register, not noise to normalize away).

### POS tagging

Assign one of the 17 `UPOS_TAGSET` tags per token. A rule-based tagger
(suffix/context heuristics + a closed-class word list for
`DET`/`CCONJ`/`ADP`/`PART`/etc.) is sufficient and is what the golden test
checks against — sophistication here matters less than correctness on the
closed classes and defensible choices on the open classes (`NOUN` vs.
`VERB` ambiguity is common in Vietnamese, e.g. `"cái đẹp"` the-beautiful
[NOUN] vs. `"cô ấy đẹp"` she-is-beautiful [ADJ, not VERB — Vietnamese has
no copula for predicate adjectives]).

### DeepSeek refinement (optional, Task 9)

If you want to add a model-assisted refinement pass over your rule-based
tagger's low-confidence tags, you may extend
`platform.agents.registry.AGENTS["pos-tagger"]` (already defined, already
validated by `_validate_pos`) — but CLAUDE.md rule 2 is binding: DeepSeek
output must be validated (it already is, structurally, by
`_validate_pos`) and reconciled with your own tagger's output before it
can appear in a `SegmentedSentence` with `source="real"`. This is
optional and graded as a bonus, not a requirement — a purely rule-based
submission that passes the golden test is a complete Project 1.

## Non-Goals (explicitly out of scope for Project 1)

- UD dependency parsing (`head`/`deprel`) — Project 2.
- Named entity recognition — Project 3.
- "Fixing" non-diacritic or teencode spelling to formal Vietnamese —
  never do this; preserve the register as-is (CLAUDE.md).
- Achieving state-of-the-art segmentation accuracy against a published
  benchmark — there is no accuracy benchmark for this project; the gate
  and golden test check structural correctness and the specific compound/
  register traps above, not F1 against VLSP.
- Multi-sentence context (each `segment()` call is one sentence,
  independent of its document).

## Testing

TDD per CLAUDE.md's working agreements. Required test coverage (checked
by the gate's step 7 — see `gate.yaml`'s `required_input_classes`):
`formal`, `informal`, `teencode`, `non_diacritic` registers; at least one
`compound`-word case; a `degenerate` input (empty string, single syllable);
an `adversarial` input (you construct one — e.g. a genuinely ambiguous
compound boundary).

Write `TESTING.md` in this directory: for each of your segmentation
design decisions (compound dictionary source, ambiguity tie-breaking
rule, reduplication handling), state what you decided and why. This is
read by the professor during manual review — it is your demonstration of
understanding, independent of the mechanical gate.

## Open Risks Carried Into the Implementation Plan

- **Compound dictionary coverage.** `known_compounds.txt` (~48 entries)
  is a floor, not a target — your dictionary should be substantially
  larger. Under-coverage shows up as golden-test failures on real fixture
  sentences containing compounds outside that list; over-coverage (a
  dictionary entry that isn't really a fixed compound) can wrongly
  prevent a legitimate word-boundary split elsewhere. Document your
  dictionary's size and source in `TESTING.md`.
- **Teencode/non-diacritic segmentation quality is inherently lower.**
  These registers lose information a segmenter normally relies on
  (diacritics disambiguate many syllable boundaries). A reasonable,
  documented degradation is acceptable; silently discarding these
  registers is not (CLAUDE.md, and the gate's `required_input_classes`
  makes their presence in your test suite mandatory).
