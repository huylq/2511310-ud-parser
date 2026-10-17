# Project 2 Testing Plan

**Student:** Lê Quốc Huy — **Student ID:** 2511310

**Updated:** 17 October 2026

## 1. Objectives and scope

Testing covers evaluation-data contracts, parser components and linguistic
accuracy. The selected parser uses arc-standard with an averaged perceptron
trained on projected VTB data.

Structural correctness requires unchanged input tokens and a connected tree
with one head per token, exactly one root, valid head references and no cycles.
Linguistic quality is assessed separately with UAS/LAS and errors on the six
construction groups required by the task.

| Scope | Status on 17 October 2026 |
|---|---|
| Annotation contract | Implemented; 24 cases pass |
| Full submission-tree suite | 213 passed, 14 skipped, 1 warning |
| Parser/oracle/features/trainer/loader unit tests | Implement alongside the components in Weeks 3–4 |
| Parser integration over 151 fixture sentences | Run once the parse pipeline and model files exist |
| Dev and annotation-set UAS/LAS | Measure once a trained model exists |

Tests of arc creation must exercise the project's transitions, legality filter
or guard and then validate output. Merely constructing a bad tree and calling
the frozen is_single_rooted_tree function does not test parser behavior.

## 2. Organization and commands

Project tests belong in tests/test_linguistics_ud_parser*.py, matching
own_test_glob in [gate.yaml](gate.yaml). Tests run offline in .venv, without API
calls or changes to fixtures, interfaces or gate code.

From the repository root, run all tests:

```powershell
.venv\Scripts\python.exe -m pytest tests -q -o "addopts="
```

Run the annotation contract alone:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_linguistics_ud_parser_hand_annotated.py -q -o "addopts="
```

The addopts override removes the configured extra quiet option so the summary
remains visible. The recorded full-suite summary is:

```text
213 passed, 14 skipped, 1 warning in 109.78s (0:01:49)
```

This was run in a worktree based on origin/student/02-ud-parsing with the Week 2
files added, reusing the project virtual environment and pointing PYTHONPATH
at the submission tree's src directory. The passing cases include 189 inherited
tests and 24 annotation-contract cases. Eleven live-Postgres tests, two
live-MinIO tests and the unimplemented Project 1 golden-test module are skipped.
The warning is Pandera's import-related FutureWarning. The full log is saved in
[PYTEST_HAND_ANNOTATED.txt](analysis/PYTEST_HAND_ANNOTATED.txt).

## 3. Annotation contract

The data is [hand_annotated.conllu](data/hand_annotated.conllu). The implemented
[test file](../../tests/test_linguistics_ud_parser_hand_annotated.py) contains a
small CoNLL-U reader and adds no dependency.

| Implemented check | Acceptance criterion |
|---|---|
| Encoding/lines | UTF-8 without BOM, NFC, LF line endings and a final blank line |
| Size and IDs | At least 20 sentences; unique hc-xxx sentence IDs |
| Metadata | sent_id, text, source_url, source_name, accessed, register, synthetic, constructions, uncertain and notes present |
| Source/status fields | Source-based sentences have HTTP/HTTPS URLs; valid dates and allowed register/flag values |
| Tokens/columns | Ten TAB-separated columns, consecutive integer IDs, FORM=text.split(), UPOS X |
| Relations/heads | DEPREL in UD_DEPREL, HEAD in range, head 0 if and only if relation root |
| Schema/tree | Convert idx=ID−1 and keep HEAD; pass validate_dependency_parse and is_single_rooted_tree |
| Tags/coverage | Allowed tags without within-sentence duplicates; at least ten distinct tags overall |
| Synthetic fraction | Strictly below 20% of sentences |

Twenty per-sentence cases and four file-level checks pass. Uncertain sentences
must still satisfy all format and structural requirements.

The set has 20 sentences, 254 tokens, ten tags and no synthetic sentences.
Uncertain IDs are hc-010, hc-011, hc-016, hc-017 and hc-019. Keep them in the
file but exclude each whole sentence from model scoring. The remaining 15
sentences contain 207 tokens and eight tags. Detailed counts are in
[hand_annotated_check.json](analysis/hand_annotated_check.json). Structural
validation does not replace linguistic review.

## 4. Component tests for implementation

The following acceptance cases guide Weeks 3–4 implementation. Test algorithmic
state using IDs and abstract structures; use VTB, existing fixtures and the
annotation set for linguistic comparisons.

| Component | Test situation | Required result |
|---|---|---|
| VTB reader | Comments, blank lines, integer IDs, multiword rows, empty nodes | Read the basic tree; do not create nodes for range/decimal IDs; identify malformed rows |
| Projection | Single/multisyllabic words, repeated/leading punctuation, children of removed punct nodes | First-syllable anchor, dep internal arcs, correct original-chain reattachment, consecutive IDs and valid trees |
| Label mapping | Labels with/without subtypes and invalid interface labels | Match the complete mapping; never emit a label outside UD_DEPREL |
| Arc-standard | SHIFT/LEFT_ARC/RIGHT_ARC, short stack, exhausted buffer, assigned dependent | Correct state updates; reject invalid actions before mutation |
| Guard | Self-loop, out-of-range head, repeated head assignment, controlled cycle-closing arc | Reject without writing an invalid arc or partially changing state |
| Single root | Scorer prefers ROOT while input remains or more tokens remain stacked | Filter the action; allow RIGHT_ARC(root) only as the final action |
| Decoder | New-sentence prediction, including illegal high-scoring actions | Choose only legal actions; complete n internal tokens in 2n actions; never call oracle |
| Static oracle | Projective gold trees and dependents with unattached gold children | Reconstruct exact heads/labels with legal actions; report unexpected replay failures |
| Projectivity | Nonprojective training tree after projection | Exclude with ID/reason; retain nonprojective dev/test trees for scoring |
| Features | ROOT, absent positions, short forms, empty buffer, distance buckets and children on both sides | Exact 54 pre-encoding slots, deterministic keys, no UPOS/gold leakage |
| Perceptron | Correct/wrong actions, correct direction but wrong label, ties | Update the correct two classes only when wrong; use the specified tie order |
| Weight averaging | Updates interspersed with unchanged steps | Match explicit averaging over a short weight history, including unchanged steps |
| Model selection | LAS/UAS ties, best epoch before final epoch, three non-improving epochs | Correct priority, patience and snapshot; no dev updates |
| Export/pruning | JSON round-trip, rare features, bias, size threshold | Preserve scores on round-trip, retain bias, meet 10,000,000-byte model/metadata budget and re-evaluate dev |
| Loader | Missing file, invalid hash/version/IDs, duplicate keys, NaN/Infinity, repeated calls | Report model errors without fallback masking; cache read-only once per process |
| Original-token grouping | Root group, multiple external incoming arcs, equal-depth candidates | Minimum-depth/smallest-ID representative, correct head mapping, preserved original tokens and valid tree |
| Project 1 input | Word tokens, underscores in forms, valid/missing UPOS | Use syllables, not guessed form boundaries; preserve valid UPOS, None→X |
| Emoticons | :)) in ordinary text and one/multiple emoticons without ordinary tokens | Reinsert discourse arcs within override scope; emoticon-only input has one root |
| Empty/single token | Empty input and exactly one input token | Empty raises ValueError; single token gets head 0/root; emit no artificial ROOT node |
| Fallback | Controlled tree-construction failure | Valid star on original tokens and recorded reason; do not swallow input/model errors |
| State isolation | Consecutive sentences and repeated identical input | Reproducible output; no stack/head/sentence state leaks between calls |

After token conversion, verify output count, order, idx and form against the
original input. Test decoding, grouping and overrides separately before full
pipeline integration.

## 5. Six constructions and adversarial checks

[DESIGN.md](DESIGN.md) records VTB conventions and evidence. Compare predictions
with resolved annotation heads/labels, reporting head and label errors separately.

| Group | Current comparison data | Required behavior |
|---|---|---|
| Classifiers | hc-015 numeral+classifier+noun; hc-002/005 bare classifiers; hc-004/015 ordinary nouns | Preserve mapped VTB heads; do not force con/chiếc to clf solely from form |
| Coordination | hc-002/004/015/020 contain và | cc attaches to its conjunct, conj to the first conjunct; add hay_or/hay_good cases |
| Serial/directional verbs | hc-019 đi cày is uncertain; VTB provides source-tree comparisons | Preserve compound/xcomp and head conventions; add dir and resolve hc-019 before scoring |
| Possessives | hc-020 has của; hc-015 bare possession; hc-016 uncertain | Của is case on the possessor, external relation nmod; insert no marker in bare possession |
| Topic/comment | No topic-tagged manual sentence yet | Add resolved annotation; distinguish nsubj/obj/dislocated by role, not initial position |
| Particles/emoticons | Particle hc-008/009/017/018; demonstrative đó hc-006; emoticon hc-016/017 | Distinguish discourse/demonstrative roles; test :)) override; add degenerate and missing particles |

Prioritize evaluative hay wrongly predicted as cc and classifier forms used as
ordinary nouns. Track nha, the roles of đó and emoticons beyond :)) separately;
expand an override only with error evidence and a documented convention.

Uncertain sentences contribute to overall set coverage but not accuracy scores.
Currently svc_di and emoticon have no eligible scoring sentence because their
examples are uncertain.

## 6. Gate input classes

[gate.yaml](gate.yaml) requires the project's own test glob, at least six cases
and the input classes below. The existing contract-case count does not replace
these parser behavior checks.

| Class or invariant | Required parser check |
|---|---|
| cycle | Guard/decoder rejects a cycle-closing arc and preserves valid state |
| Single root | Prevent multiple ROOT attachments even when preferred by model scores |
| degenerate | Handle empty, single-token, punctuation-only and emoticon-only input |
| adversarial | Do not confuse evaluative hay with cc or an ordinary noun with a classifier |
| clf / classifier | Match resolved classifier heads and labels |

Once the pipeline/model exist, parse all 151 fixture sentences through the stub.
Each output must pass schema/tree checks, carry source="real" and preserve input
tokens. Do not modify fixtures. Provisional treebank annotations are reference
material for decisions that have not been confirmed.

## 7. Evaluation and recording

Evaluate dev after each epoch using averaged weights and the prediction pipeline.
Select LAS, then UAS, then the earliest epoch. Keep all dev trees, including
nonprojective ones. Evaluate the trained model on VTB test once after fixing it.

```text
UAS = tokens with correct head / scored tokens
LAS = tokens with correct head and relation / scored tokens
```

Micro-average across tokens, including internal dep and retained punctuation,
excluding artificial ROOT. Identify the projected syllable representation in
every score report. Exclude uncertain manual sentences and verify that scoring
does not mutate data or weights.

Record code/data/model hashes, configuration, seed/epoch, scored sentence/token
counts, correct counts, UAS/LAS, errors by tag, fallback count and runtime.
After pruning, load the exact release file for dev scoring and report feature/
weight counts and bytes before/after.

Measure cold loading separately against the one-second target. Verify that
151 calls in one process load the model only once. Save literal pytest summaries
and logs for test runs.

## 8. Implementation order and completion criteria

1. **Week 2 data:** keep the contract green; annotation changes update metadata,
   coverage and the corresponding decisions.
2. **Reader/projection/oracle:** verify source trees, mapping and exact gold
   replay; count invalid/nonprojective trees before and after projection.
3. **Transitions/features/training:** write behavior tests before implementation;
   verify updates, averaging and reproducibility.
4. **Loader/pipeline:** test round-trip, cache, original-token mapping, overrides,
   validation and fallback, then the full fixture.
5. **Linguistic evaluation:** score dev and eligible manual sentences; expand
   the set to at least 30 sentences and every per-tag minimum by Week 4's end.

Week 2 format, tree and coverage checks pass. Parser acceptance additionally
requires component/integration tests and real model evaluation. Basic
arc-standard is projective; fallback provides structure, while separate scores
must establish linguistic accuracy.

## 9. Related files

- [Week 2 task](week2_tasks.md), particularly Sections 5–6.
- [Specification](spec.md), [gate configuration](gate.yaml) and [design](DESIGN.md).
- [Week 2 report](WEEK2_REPORT.md): design decisions and measured results.
- [Annotation set](data/hand_annotated.conllu), [validation report](analysis/hand_annotated_check.json) and [test log](analysis/PYTEST_HAND_ANNOTATED.txt).
- [VTB statistics](analysis/VTB_COUNTS.md), [JSON inventory](analysis/VTB_COUNTS.json) and [label mapping](analysis/LABEL_MAPPING.md).
