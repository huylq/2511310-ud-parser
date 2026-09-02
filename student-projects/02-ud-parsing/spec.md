# Project 2: UD Dependency Parsing — Design

Compact skeleton — see `student-projects/01-word-seg-pos/spec.md` for the
full worked example this follows the same shape as.

## Goal

Build a UD v2 dependency parser:

```
parse(sentence: interfaces.linguistics.SegmentedSentence) -> interfaces.ud.DependencyParse
```

Consumes Project 1's output (its **stub**, `interfaces.stubs.linguistics_stub.stub_segment`,
until Project 1 merges for real — see `student-projects/README.md`).
Produces a full dependency tree per sentence: `head` (CoNLL-U convention,
0 = root) and `deprel` (from `interfaces._common.UD_DEPREL`) for every
token. `source` must be `"real"`.

## Linguistic grounding — from `.claude/agents/vietnamese-linguist.md`

Fold this in whole; it is your standard, not a suggestion:

> - Vietnamese is **syllable-segmented, not word-segmented**. Whitespace
>   separates syllables. `sinh viên`, `hợp tác xã`, `nghiên cứu sinh` are
>   single words. Any pipeline treating whitespace tokens as words is
>   wrong at the first step.
> - **Compounds vs. phrases** is the hardest recurring call. `nhà máy`
>   (factory) is a word; `nhà lớn` (big house) is a phrase. Argue from
>   substitutability and semantic compositionality, not intuition.
> - **Classifiers** (`cái`, `con`, `chiếc`, `cuốn`) attach as `det` or
>   `clf` depending on the analysis; VTB has a convention — follow it and
>   cite it rather than reinventing.
> - **Serial verb constructions** (`đi mua`, `chạy ra`) need a consistent
>   head choice. Inconsistency here destroys LAS comparability more than
>   any single tag error.
> - **`của` possessives**, **topic-comment fronting**, and **final
>   particles** (`à`, `nhé`, `đấy`) are the usual sources of parser
>   disagreement.
>
> Diacritics are load-bearing. `ma` / `má` / `mà` / `mả` / `mã` / `mạ` are
> six words. Never normalise them away in an example.

Follow UD v2, aligned with UD_Vietnamese-VTB (CLAUDE.md) — when a
construction's analysis is genuinely unclear from the UD guidelines, cite
the convention you're following rather than inventing one from scratch.

## Non-Goals

- Word segmentation / POS tagging (Project 1's job — you consume its
  output, real or stub, unchanged).
- Treebank adjudication or gold-standard curation (Project 4).
- Achieving a specific LAS/UAS against a published benchmark — the gate
  and golden test check tree well-formedness and specific Vietnamese
  construction handling (classifier attachment, `của`-possessive
  attachment, serial-verb head consistency — see the plan's I/O contract
  table), not benchmark parity.

## Testing

Required input classes (gate step 7): a sentence with a classifier
phrase, a `của`-possessive (or your closest available fixture analog —
flag the gap if `tests/fixtures/treebank/PROVISIONAL.md`'s known gap
applies to you too), a coordination structure, a cycle/degenerate case
your parser must reject or handle explicitly, plus `degenerate` and
`adversarial` cases generally.

Golden invariant (`tests/golden/test_ud_parsing_golden.py`, authored in a
later pass — see `student-projects/README.md`): one root, no cycles,
fully spanning, over every fixture sentence
(`interfaces.ud.is_single_rooted_tree`).
