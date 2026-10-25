# Week 3 Report on Data Preparation and the Static Oracle

**Student:** Lê Quốc Huy — **Student ID:** 2511310

**Project:** 02 — Vietnamese UD Dependency Parsing

**Updated:** 25 October 2026

## 1. Week 3 outcomes

Implemented the CoNLL-U reader, dependency-label mapping, word-to-syllable
projection, arc-standard transitions with structural guards, and static oracle
in [ud_parser.py](../../src/vietnlp/linguistics/ud_parser.py), following
[week3_tasks.md](week3_tasks.md). Each component has a failing-test commit before
its implementation commit.

All **275 Project 2 tests pass**. The full repository suite reports **464 passed,
14 skipped, 1 warning**. Oracle replay reconstructs every gold head and label in
all 20 projected annotation sentences and in **1,395 retained VTB train
sentences, with 0 failures**.

Corpus-wide projection measurements are committed in
[PROJECTION_COUNTS.md](analysis/PROJECTION_COUNTS.md) and
[PROJECTION_COUNTS.json](analysis/PROJECTION_COUNTS.json). Features, the
perceptron, training, model files and the public `parse()` function remain
Week 4 work. No model UAS/LAS or inference-speed results are reported.

## 2. Implemented behavior and component tests

| Component | Verified behavior | Passing cases |
|---|---|---:|
| [CoNLL-U reader](../../tests/test_linguistics_ud_parser_conllu.py) | Metadata and exact token fields for two supplied sentences; final sentence at EOF; skip range/decimal IDs; malformed columns, HEAD and IDs raise with source line numbers; load all 20 annotations | 14 |
| [Label mapping](../../tests/test_linguistics_ud_parser_labels.py) | All 84 source labels match the documented mapping to 34 observed base labels; valid interface labels are preserved; unknown labels raise | 125 |
| [Projection](../../tests/test_linguistics_ud_parser_projection.py) | First-syllable anchors, internal dep stars, directional punctuation gluing, original-head-chain reattachment, root preservation, ID mappings and projectivity including ROOT | 38 |
| [Transitions and guards](../../tests/test_linguistics_ud_parser_transitions.py) | State updates, exact legal-action sets, atomic refusal of illegal actions, cycle prevention, final-only ROOT and exactly 2n actions | 34 |
| [Static oracle](../../tests/test_linguistics_ud_parser_oracle.py) | Exact gold replay; both child heads and labels required before reduction; chains, branching, clf, empty/single-token cases, non-projective rejection and all 20 annotations | 40 |
| [Annotation contract](../../tests/test_linguistics_ud_parser_hand_annotated.py) | Existing format, metadata, alignment, label, tree and coverage checks | 24 |
| **Total** | | **275** |

The reader raises `ValueError` and stops on malformed input rather than
returning a partial result. Projection preserves source trees, resets projected
UPOS to `X`, and reports non-projectivity without dropping valid trees.

Opening brackets and typographic opening quotes glue forward; closing marks
and other punctuation glue backward. Standalone straight double quotes
alternate opening/closing within each sentence. A punctuation root is retained,
as is a mark without a target on its selected side. The projection version is
`v2-first-dep-directional-glue`.

`ParserState` starts with stack `[0]`, buffer position 1 and unassigned heads
and labels. An invalid action leaves the state unchanged. ROOT attachment is
legal only as the final `RIGHT_ARC(root)` with an exhausted buffer and stack
`[0, j]`.

`StaticOracle` chooses LEFT_ARC, then RIGHT_ARC, then SHIFT when the preceding
gold reduction conditions do not hold. A dependent is ready only when every
direct gold child has both the correct head and label; leaves are immediately
ready. The oracle rejects empty or non-projective gold input and reports
sentence IDs on errors. It supplies training targets; new-sentence prediction
will use the trained model.

## 3. Test-first commit evidence

| Component | Test commit | Implementation commit |
|---|---|---|
| CoNLL-U reader | [1e609a7](https://github.com/phunghx/VietnamesModel/commit/1e609a76b46848d7ae181dd4473c0310802a3c90) | [c2504fb](https://github.com/phunghx/VietnamesModel/commit/c2504fb237c64d5548d43fa2b69bc137827fb956) |
| Label mapping | [6fb79f1](https://github.com/phunghx/VietnamesModel/commit/6fb79f1816c58404fdd971cf99d0a228cf2d9e78) | [efb184f](https://github.com/phunghx/VietnamesModel/commit/efb184f1d5abe9c3389fa8854f214597a7794956) |
| Projection | [cf2677c](https://github.com/phunghx/VietnamesModel/commit/cf2677c92ae288b98e28abc06ee31762f7a8f810) | [227aee9](https://github.com/phunghx/VietnamesModel/commit/227aee97dc7bc8cfbd867c8911276e5d89fa326c) |
| Transitions and guards | [2cb8b63](https://github.com/phunghx/VietnamesModel/commit/2cb8b63bd5610fc320392ac405e76b5e6bea0637) | [8342d4b](https://github.com/phunghx/VietnamesModel/commit/8342d4be2278260bca16b7de3f1d72e5c34d3b70) |
| Static oracle | [2a04c83](https://github.com/phunghx/VietnamesModel/commit/2a04c8346dc017c366fe4fdce50c7542d66ad8de) | [9fb9ed0](https://github.com/phunghx/VietnamesModel/commit/9fb9ed06f460cf242082ef5a3e2bfd357ffd8c91) |

Additional reader validation tests were committed in
[90310a5](https://github.com/phunghx/VietnamesModel/commit/90310a506461e907b18e94f3358d9465d4f079ab).
The VTB measurement script, outputs and updated design/testing documents were
committed in
[ba5ef2c](https://github.com/phunghx/VietnamesModel/commit/ba5ef2c78625892d0b67ae5e3e57f67d68884115).
These commits are pushed to
[student/02-ud-parsing](https://github.com/phunghx/VietnamesModel/tree/student/02-ud-parsing).

## 4. VTB projection measurements

The corpus is UD_Vietnamese-VTB at commit
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

The following train sentences are excluded because their projected trees are
non-projective: `train-s414`, `train-s435`, `train-s498`, `train-s518` and
`train-s955`. The remaining **1,395 sentences contain 22,000 syllable tokens**.
Oracle replay passes on all of them, reproducing every head and label in
**44,000 legal actions**, exactly n SHIFTs and n ARCs per sentence. There are
**0 oracle failures**. Oracle failures would be bugs to fix, not exclusions.

All dev/test sentences are retained for later evaluation, including
non-projective trees. These measurements do not train, tune or evaluate a
prediction model.

## 5. Reproduction and full-suite results

From the repository root, with dependencies installed and `src` on
`PYTHONPATH`, run:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) "src"
python -m pytest tests -q -o "addopts=" --disable-warnings
```

Literal summary of the recorded full-suite run:

```text
464 passed, 14 skipped, 1 warning in 125.58s (0:02:05)
```

This comprises 275 Project 2 cases and 189 inherited tests. The 14 skips cover
11 live-Postgres tests, two live-MinIO tests and the unimplemented Project 1
golden-test module. The warning is Pandera's import-related `FutureWarning`.
The suite runs offline; its unit tests do not read VTB. Test names include
`cycle`, `clf`, `adversarial` and `degenerate`.

Run the corpus measurement separately:

```text
python student-projects/02-ud-parsing/scripts/project_vtb.py --data-dir <VTB_DIR> --output-dir student-projects/02-ud-parsing/analysis
```

The script exits successfully for the recorded measurements. It returns a
nonzero status if any projected tree is invalid or any retained train tree
fails oracle replay. Token/punctuation totals reconcile with the source
inventory, and report regeneration produces identical bytes.

## 6. Deliverables and Week 4 work

- [Parser components](../../src/vietnlp/linguistics/ud_parser.py) and the six test files linked in Section 2.
- [VTB measurement script](scripts/project_vtb.py), [Markdown results](analysis/PROJECTION_COUNTS.md) and [JSON results](analysis/PROJECTION_COUNTS.json).
- Updated [DESIGN.md](DESIGN.md) and [TESTING.md](TESTING.md).
- Reused [20-sentence annotation set](data/hand_annotated.conllu).

Week 4 will implement the 54 feature slots, averaged perceptron, a small
training run, weight saving/loading and `parse()` while preserving input
tokens. It also includes the `:))` override, loading weights once per process,
fixture integration and the required gate run. No Week 4 gate PASS is claimed.

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
| Codex in ChatGPT (OpenAI) | Exact model/version not recorded | Explain component behavior and the task requirements; implement reader, label mapping, projection, transitions and static oracle; write tests and VTB measurements; draft and update documentation and this report | Implementation and test code, including malformed-input variants, additional CoNLL-U test snippets, structural trees and expected results; measurement script and generated statistics; document/report drafts and explanations | Supplied the two reader examples; specified forward gluing for opening punctuation, backward gluing for closing punctuation and alternating straight quotes; selected incremental implementation and test-first commits |
