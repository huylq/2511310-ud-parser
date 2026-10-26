# Week 3 Report on Data Preparation and the Static Oracle

**Student:** Lê Quốc Huy — **Student ID:** 2511310

**Project:** 02 — Vietnamese UD Dependency Parsing

## 1. Work completed this week

This week, I completed the core data-preparation and transition components
for the parser and tested them using TDD. For each component, I committed
failing tests before implementing the code that made them pass.

The implementation is in
[ud_parser.py](../../src/vietnlp/linguistics/ud_parser.py), following
[week3_tasks.md](week3_tasks.md). It covers the CoNLL-U reader, label mapping,
sentence projection, arc-standard transitions and guards, and static oracle.
The commit pairs are listed in Section 3.

I also ran projection on all VTB splits and checked oracle replay on the
retained projective train trees. The measured results are in
[PROJECTION_COUNTS.md](analysis/PROJECTION_COUNTS.md) and
[PROJECTION_COUNTS.json](analysis/PROJECTION_COUNTS.json).

## 2. Implemented components

### 2.1. CoNLL-U reader

- I implemented `read_conllu()` to convert CoNLL-U text into sentences and tokens, preserving metadata, FORM, UPOS, HEAD and DEPREL.
- The reader checks formatting and tree structure, reports invalid input with its source line number, and skips range and decimal IDs.
- I tested the two supplied examples containing 28 tokens, malformed-input cases and the annotation set of 20 sentences and 254 tokens. All [14 reader tests](../../tests/test_linguistics_ud_parser_conllu.py) pass.

### 2.2. Dependency-label mapping

- I defined `VTB_LABEL_MAPPING` and `map_deprel()` to map the 84 source labels in UD_Vietnamese-VTB to 34 observed base labels.
- Valid base labels are preserved, including interface labels absent from the corpus. Invalid labels raise an error.
- All [125 label-mapping tests](../../tests/test_linguistics_ud_parser_labels.py) pass.

### 2.3. Word-to-syllable projection

- I implemented `project_sentence()` according to `DESIGN.md` and `TESTING.md`, using version `v2-first-dep-directional-glue`.
- Opening punctuation glues onto the following token; closing punctuation glues onto the preceding token. Straight double quotes alternate opening/closing within each sentence.
- The function splits words into syllables, updates heads and labels, and returns mappings in both directions together with `is_projective`, without changing the source tree. Later syllables attach to the first-syllable anchor with `dep`.
- All [38 projection tests](../../tests/test_linguistics_ud_parser_projection.py) pass, including 35 initial cases and three projectivity checks that include the ROOT arc.

### 2.4. Transition system and guards

- I implemented `Action` and `ParserState` for arc-standard, with SHIFT, LEFT_ARC and RIGHT_ARC.
- Guards reject illegal actions before changing the state, including repeated head assignment, self-loops and cycle-closing arcs. ROOT attachment is allowed only at the final step.
- All [34 transition and guard tests](../../tests/test_linguistics_ud_parser_transitions.py) pass.

### 2.5. Static oracle

- I implemented `StaticOracle` to select the correct actions from a gold tree.
- It checks that all gold children have been attached with the correct heads and labels, rejects non-projective gold trees and reports errors with the sentence ID.
- All [40 oracle tests](../../tests/test_linguistics_ud_parser_oracle.py) pass, including exact reconstruction of the 20 projected annotation trees and the boundary cases.

Together with the existing [24 annotation-contract tests](../../tests/test_linguistics_ud_parser_hand_annotated.py), the five components give **275 passing Project 2 cases**.

## 3. Test-first commit evidence

| Component | Test commit | Implementation commit |
|---|---|---|
| CoNLL-U reader | [2159d1e](https://github.com/huylq/2511310-ud-parser/commit/2159d1e95df80c8201341b5f216211c2dc13bfa1) | [4cf2f64](https://github.com/huylq/2511310-ud-parser/commit/4cf2f641ffba6a3d5d7a7e20fc0c3e91d84c5a39) |
| Label mapping | [0d8a623](https://github.com/huylq/2511310-ud-parser/commit/0d8a623804c228e127b548a3a7e019b6fd7837bc) | [7da8525](https://github.com/huylq/2511310-ud-parser/commit/7da85259fef3676abb1aaa6c5fd5f47df4f5c85a) |
| Projection | [c319d6c](https://github.com/huylq/2511310-ud-parser/commit/c319d6c66b7c43ba461866fba80b36fc70784ccf) | [3949108](https://github.com/huylq/2511310-ud-parser/commit/394910830dbfbfd22db73933dc9408548c9d9b6e) |
| Transitions and guards | [ff82e7e](https://github.com/huylq/2511310-ud-parser/commit/ff82e7e19f1d2d73a6e745bd44ff7270d080b1f0) | [b66170a](https://github.com/huylq/2511310-ud-parser/commit/b66170a2c2214211ba1322d0b5bf1afc1d98d699) |
| Static oracle | [a42ee32](https://github.com/huylq/2511310-ud-parser/commit/a42ee323cdf852885ba1a3f035164183181bc492) | [8bebf73](https://github.com/huylq/2511310-ud-parser/commit/8bebf73bb8ee2882a7fb0c6efd8c50bb44260caa) |

Additional reader validation tests were committed in
[583cb8d](https://github.com/huylq/2511310-ud-parser/commit/583cb8d0c3f0725e89f266516daa7e4034651282).
The VTB measurement script, outputs and updated design/testing documents were
committed in
[dd4b6d3](https://github.com/huylq/2511310-ud-parser/commit/dd4b6d391261d1ca6c27c98822e80744d1055316).
These commits are pushed to
[student/02-ud-parsing](https://github.com/huylq/2511310-ud-parser/tree/student/02-ud-parsing).

## 4. VTB projection measurements

I ran the reader, label mapping and projection on UD_Vietnamese-VTB at commit
`3c971fd1c5d03561e00b267d3d0057b81a9bea84`, as pinned in
[VTB_COUNTS.json](analysis/VTB_COUNTS.json). The script verifies the SHA-256
of each input split before processing it.

| Split | Sentences | Syllable tokens | Internal dep arcs added | Punctuation glued backward | Punctuation glued forward | Invalid trees | Non-projective trees |
|---|---:|---:|---:|---:|---:|---:|---:|
| Train | 1,400 | 22,099 | 4,758 | 2,644 | 230 | 0 | 5 |
| Dev | 1,123 | 28,432 | 5,765 | 3,279 | 216 | 0 | 9 |
| Test | 800 | 12,191 | 2,165 | 1,533 | 133 | 0 | 1 |

Counts include all projected trees before train filtering. Internal `dep` arcs
exclude source `dep` relations. Backward/forward punctuation counts include
alternating straight quotes. Retained punctuation totals are 57/22/37 for
train/dev/test. The exact source punctuation FORMs on train include **408
straight double quotes and 27 opening parentheses**, reproducing the requested
inventory.

Every projected tree passes the frozen schema and single-rooted-tree checks.
Projectivity is measured after projection and includes the artificial ROOT arc.

I excluded the following train sentences because their projected trees are
non-projective: `train-s414`, `train-s435`, `train-s498`, `train-s518` and
`train-s955`. The remaining **1,395 sentences contain 22,000 syllable tokens**.
Oracle replay passes on all of them, reproducing every head and label in
**44,000 legal actions**, exactly n SHIFTs and n ARCs per sentence. There are
**0 oracle failures**. Oracle failures would be bugs to fix, not exclusions.

I retained all dev/test sentences for later evaluation, including
non-projective trees. These measurements cover data preparation and oracle
replay. I have not trained a model or measured UAS/LAS yet.

## 5. Reproduction and full-suite results

I ran the full test suite from the repository root, with dependencies
installed and `src` on `PYTHONPATH`:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) "src"
python -m pytest tests -q -o "addopts=" --disable-warnings
```

Literal summary of the recorded full-suite run in the course repository:

```text
464 passed, 14 skipped, 1 warning in 125.58s (0:02:05)
```

The course suite comprises 275 Project 2 cases and 189 inherited tests. Its
14 skips cover 11 live-Postgres tests, two live-MinIO tests and the unimplemented
Project 1 golden-test module.

The public project repository contains the same 275 Project 2 cases and 29
inherited tests for the retained dependencies and fixtures. Running the same
pytest command there gives:

```text
304 passed, 1 warning in 3.95s
```

The warning is Pandera's import-related `FutureWarning`. Both suites run
offline; their unit tests do not read VTB. Test names include `cycle`, `clf`,
`adversarial` and `degenerate`.

Run the corpus measurement separately:

```text
python student-projects/02-ud-parsing/scripts/project_vtb.py --data-dir <VTB_DIR> --output-dir student-projects/02-ud-parsing/analysis
```

The measurement script completed successfully. It returns a
nonzero status if any projected tree is invalid or any retained train tree
fails oracle replay. Token/punctuation totals reconcile with the source
inventory, and report regeneration produces identical bytes.

## 6. Deliverables and Week 4 work

- [Parser components](../../src/vietnlp/linguistics/ud_parser.py) and the six test files linked in Section 2.
- [VTB measurement script](scripts/project_vtb.py), [Markdown results](analysis/PROJECTION_COUNTS.md) and [JSON results](analysis/PROJECTION_COUNTS.json).
- Updated [DESIGN.md](DESIGN.md) and [TESTING.md](TESTING.md).
- Reused [20-sentence annotation set](data/hand_annotated.conllu).

Next week, I plan to:

- Implement the 54 feature slots and averaged perceptron, run a small training experiment, and save and reload the weights.
- Implement `parse()` on all 151 fixture sentences while preserving the input tokens, add the `:))` override, and load weights once per process.
- Run the required gate and include its output in `WEEK4_REPORT.md`.
- Evaluate UAS and LAS on dev while developing the model. Keep test for one final evaluation after the model and pipeline are fixed.

## 7. Data provenance statement

VTB is the published human-annotated corpus pinned above. Its source files are
unchanged and remain outside the repository. The submitted VTB results are
aggregate measurements and sentence IDs from deterministic processing.

The 20-sentence annotation set is reused unchanged from Week 2. The two reader
examples were supplied by the student. AI assistance included drafting
additional unit-test cases, CoNLL-U snippets, structural trees and expected
results, as disclosed below.

## 8. AI-use disclosure

| Tool | Version/model | Prompts, summarized by purpose | What the AI produced | What the student changed or decided |
|---|---|---|---|---|
| Codex in ChatGPT (OpenAI) | Exact model/version not recorded | Implement the CoNLL-U reader, label mapping, projection, transitions and static oracle; write unit tests and a VTB measurement script | Implementation and test code, including malformed-input variants, additional CoNLL-U test snippets, structural trees and expected results; measurement script and generated statistics | Supplied the two reader examples; specified forward gluing for opening punctuation, backward gluing for closing punctuation and alternating straight quotes; selected incremental implementation and test-first commits |
