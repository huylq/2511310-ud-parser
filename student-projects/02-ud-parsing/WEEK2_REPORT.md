# Week 2 Report on the VTB-trained Parser Design

**Student:** Lê Quốc Huy — **Student ID:** 2511310

**Project:** 02 — Vietnamese UD Dependency Parsing

**Updated:** 17 October 2026

## 1. Week 2 outcomes

Week 2 completes the initial design of a statistical dependency parser trained
on UD_Vietnamese-VTB, inventories the source corpus and prepares an out-of-domain
evaluation set. The selected architecture is **arc-standard with an averaged
multiclass perceptron**, implemented in Python and NumPy. Projection, parser
state/actions, oracle, features, training, weight storage and structural
validation are specified in [DESIGN.md](DESIGN.md) for implementation in Weeks 3–4.

The annotation set contains **20 sentences, 254 whitespace tokens and 10
construction tags**. Its contract test is implemented. The full current suite
reports **213 passed, 14 skipped, 1 warning in 109.78s (0:01:49)**. Five sentences with unresolved
attachment conventions remain in the set with uncertain=true.

No parser, trainer or model weights have been implemented this week. The results
below concern design, corpus analysis and data validation. There are no model
UAS/LAS scores, training times or parsing-speed measurements yet.

| Task item | Deliverable | Current status |
|---|---|---|
| 0. Environment | Working environment and literal pytest summary | Verified; full test log saved |
| 1. English DESIGN | Replace the Week 1 rule-based decision and translate the design | Consolidated English design prepared, with the superseded decision identified |
| 2. VTB-trained parser | Architecture, features, training, weights and safety net | Design specified in DESIGN.md |
| 3. Projection | Word-to-syllable conversion and Project 1 input | Specified; corpus-wide projection validation follows implementation |
| 4. Six constructions | VTB evidence, mapping and evaluation coverage | Counts and decisions documented; existing sentence IDs and coverage gaps listed below |
| 5. Annotation set | At least 20 sentences, 10 tags and a passing contract test | Count, coverage, format and structural checks pass |
| 6. Tree guarantee | Decoder/guard/validation/fallback and a test plan | Specified in DESIGN.md and TESTING.md; parser tests follow implementation |
| 7. Word lists if needed | Sources for feature/override lists | No handwritten feature lexicon; the initial :)) override comes directly from the task |

The scope follows [week2_tasks.md](week2_tasks.md). Parser/training code starts
in Weeks 3–4 rather than the Week 2 design phase.

## 2. Environment and validation results

The development environment is Windows PowerShell with a Python 3.11 project
virtual environment. The final run used a clean worktree based on
origin/student/02-ud-parsing, with only the Week 2 deliverables added. The
existing virtual environment was reused with PYTHONPATH pointing to that
worktree's src directory, so imports and tests used the submission tree.

| Component | Verified version |
|---|---|
| Python | 3.11.0 |
| NumPy | 2.4.6 |
| pytest | 9.1.1 |
| Pandera | 0.33.1 |

To reproduce in a checkout with the project installed in .venv, run from the
repository root:

```powershell
.venv\Scripts\python.exe -m pytest tests -q -o "addopts="
```

Literal summary from the recorded full run:

```text
213 passed, 14 skipped, 1 warning in 109.78s (0:01:49)
```

The passing cases comprise **189 inherited tests and 24 annotation-contract
cases**: 20 per-sentence cases and four file-level checks. The 14 skips cover
11 live-Postgres tests, two live-MinIO tests and the Project 1 golden-test
module, whose segmentation implementation is not present. The addopts override
removes the configured extra -q so the summary remains visible. The warning is
Pandera's import-related FutureWarning, not a failed test. See
[PYTEST_HAND_ANNOTATED.txt](analysis/PYTEST_HAND_ANNOTATED.txt).

These checks validate data contracts and tree structure. They do not establish
the accuracy of a trained parser.

## 3. VTB data and measured statistics

The source is [UD_Vietnamese-VTB](https://github.com/UniversalDependencies/UD_Vietnamese-VTB/tree/3c971fd1c5d03561e00b267d3d0057b81a9bea84),
commit 3c971fd1c5d03561e00b267d3d0057b81a9bea84, licensed CC BY-SA 4.0.
The corpus remains outside the repository.

[analyze_vtb.py](scripts/analyze_vtb.py) verifies SHA-256 values, reads integer-ID
basic-tree nodes, checks structure and counts forms/labels without running a
model or changing source annotations.

| Split | Sentences | Word tokens | Multisyllabic tokens | Multisyllabic share | Invalid source trees | Nonprojective source trees |
|---|---:|---:|---:|---:|---:|---:|
| Train | 1,400 | 20,215 | 4,535 | 22.43% | 0 | 5 |
| Dev | 1,123 | 26,162 | 5,497 | 21.01% | 0 | 9 |
| Test | 800 | 11,692 | 2,079 | 17.78% | 0 | 1 |

Two projectivity definitions agree on these trees: crossing arcs including
artificial ROOT, and the descendant condition for tokens spanned by an arc.
The inventory contains 84 observed VTB labels mapping to 34 observed valid
base labels. The mapping takes the part before the first colon and preserves
source attachments. It does not change the frozen interface label set.

Reproducible outputs are [VTB_COUNTS.md](analysis/VTB_COUNTS.md),
[VTB_COUNTS.json](analysis/VTB_COUNTS.json) and
[LABEL_MAPPING.md](analysis/LABEL_MAPPING.md). They provide split-level counts,
nonprojective sentence IDs, hashes and the complete mapping table.

To reproduce the inventory, set VTB_DATA_DIR to the local directory containing
the pinned corpus files and SOURCE.json:

```powershell
$VTB_DATA_DIR = "<VTB_DATA_DIR>"
.venv\Scripts\python.exe student-projects/02-ud-parsing/scripts/analyze_vtb.py --data-dir "$VTB_DATA_DIR" --output-dir student-projects/02-ud-parsing/analysis
```

Replace the placeholder with the actual corpus directory. Corpus inventory of
the test split is required by the task; it is not evaluation or tuning of a
model. Model test evaluation is reserved for one final run.

## 4. Parser and training design

### 4.1. Change from Week 1

The professor's 9 October 2026 decision supersedes the Week 1 rule-based
preference: the main parser must learn from VTB. Handwritten rules are limited
to documented overrides with evidence, while fallback provides structural
safety. Arc-standard plus averaged perceptron fits the Python/NumPy constraint
and exposes each tree-building decision for testing.

### 4.2. State, actions and oracle

The state holds an immutable token sequence, a stack initially [0], a next-token
buffer position initially 1, and heads/labels arrays. ROOT is artificial ID 0;
real internal token IDs are 1…n.

With stack suffix [...,i,j], SHIFT reads the next buffer token; LEFT_ARC(r)
creates j→i and removes i; RIGHT_ARC(r) creates i→j and removes j. The model
predicts direction and relation together. Every successful decode uses n SHIFTs
and n ARCs, including the final ROOT attachment.

Only legal actions are scored. A dependent must be unassigned; self-loops,
invalid references and cycles are rejected before mutation. ROOT can be used
as a head only for the final RIGHT_ARC(root), with an exhausted buffer and
stack [0,j]. This prevents multiple roots. ROOT is never a dependent.

The static oracle derives targets from projected VTB heads/labels and removes
a dependent only after its gold children have been attached. Training predicts
and updates, then follows the oracle action. New-sentence decoding has no gold
tree or oracle. Invalid oracle replay on a valid projective tree is an error,
not a reason to silently substitute fallback gold.

Basic arc-standard is projective. Exclude nonprojective training trees after
projection and record their IDs/reasons; retain all dev/test sentences. The
post-projection exclusion count has not yet been measured.

### 4.3. Features

A training record is one parser state before an action, not an entire sentence.
Its oracle target is separate from the 54 input slots. S0/S1/S2 are the top
three stack positions; B0/B1 are the next two buffer positions.

| Group | Information | Slots |
|---|---|---:|
| Token content | Lowercased forms at S0/S1/S2/B0/B1 | 5 |
| Combinations | Three form pairs and one triple | 4 |
| Token shape | Case/digit/punctuation flags and prefix/suffix lengths 1–3 at S0/S1/B0 | 27 |
| State | Distance, stack/buffer sizes and ROOT flags | 5 |
| Built arcs | Child counts and outermost-child forms/labels at S0/S1 | 12 |
| Bias | Constant 1 | 1 |
| **Total** | | **54** |

Categorical values become sparse indicator keys, so the encoded dimensionality
can exceed 54. Build the key vocabulary from train only; unseen keys contribute
zero. Do not use UPOS, gold heads/labels/children, original VTB word boundaries,
group metadata or source/split metadata as features. Built child labels are
available state information. Lowercasing never changes output FORM.

### 4.4. Training configuration

| Item | Initial choice |
|---|---|
| Initialization | All weights zero |
| Scoring | Linear score over legal actions |
| Ties | SHIFT, LEFT_ARC, RIGHT_ARC; lexicographic labels |
| Update | Add x to the oracle class and subtract x from the wrong prediction; learning rate 1 |
| Averaging | Post-record weights over every record from the start, including unchanged steps |
| Schedule | At most 20 epochs; sentence shuffle with one continuing seed-42 generator |
| Dev | After each epoch, decode with averaged weights without updating |
| Model selection | Greatest LAS, then UAS, then earliest epoch |
| Early stopping | Three consecutive epochs without improvement under that order |
| Train+dev retraining | Not used in the initial plan |
| Test | One model evaluation after fixing the pipeline |

The values 20/42/3 are design choices, not empirically optimized results.
UAS/LAS are micro-averaged over projected tokens, including internal dep and
retained punctuation, excluding artificial ROOT. They are not directly
comparable to word-level VTB scores under a different tokenization.

### 4.5. Weight files and loading

Store sparse nonzero averaged weights in JSON under
src/vietnlp/linguistics/ud_model/, with metadata and VTB attribution. The model
and metadata together must fit 10,000,000 bytes. If necessary, prune rare
train-derived feature keys while retaining bias, using the first increasing
frequency threshold that meets the budget. Reload the exported file and
report dev scores before/after pruning.

Load on the first valid parse request and cache read-only per process. Do not
train at import or parse time. Missing/corrupt model files are configuration
errors, not grounds for fallback on every sentence. Do not use pickle. A cold
loading target of one second will be measured once actual weights exist.

## 5. Projection and Project 1 compatibility

The deterministic source-tree conversion is:

1. Read and validate the basic tree.
2. Glue punct tokens to the previous retained token without a space, retaining
   leading punctuation without a predecessor and any source root.
3. Reattach dependents of deleted punctuation through original head chains to
   the first retained ancestor, preserving their labels.
4. Split retained word FORMs on whitespace. Use the first syllable as anchor
   and attach every other syllable directly to it with dep.
5. Route external arcs through anchors, map subtypes to base labels and update IDs/heads.
6. Check labels, heads, root equivalence, cycles and projectivity.

The anchor convention is reproducible and does not assert a linguistic head
for every word. Goeswith is inappropriate for normal Vietnamese syllable
spacing. Punctuation gluing will be compared with separate punctuation on dev
in Weeks 3–4; post-projection error/projectivity counts are not yet available.

At runtime, use supplied Token.syllables and retain original token groups.
Do not split form on underscores or merge punctuation supplied as a separate
input token. After decoding, select the minimum-depth syllable in each group,
breaking ties by internal ID, and map its parent to the parent group. Parent
group depths strictly decrease, preventing cycles. The root-containing group
alone gets head 0. Validate again after grouping and reinserting emoticons.

Output retains sent_id, count/order, idx, form and valid input UPOS, with None
mapped to X. Project 2 predicts head/deprel and does not retag UPOS. Index is
zero-based; nonzero heads are one-based positions in the complete input.

## 6. Six constructions and evidence

The following totals cover all three VTB splits; the inventory reports also
provide separate train/dev/test counts. Word senses cannot be inferred from
label counts alone.

| Construction | Evidence and chosen convention | Current evaluation coverage |
|---|---|---|
| Classifiers | 250 clf and 887 clf:det; map both to clf but preserve source heads. Con has 53 clf/clf:det versus 67 nsubj/obj uses | hc-015: numeral+classifier+noun; hc-002/hc-005: bare classifiers; hc-004/hc-015: ordinary-noun uses |
| Coordination | Preserve cc/conj. Hay is cc in 43/51 occurrences, 14/16 in train; do not force evaluative hay to cc | hc-002/hc-004/hc-015/hc-020 contain và; hay_or and hay_good are absent |
| Serial/directional verbs | Adjacent đi+VERB: 55 xcomp, 47 compound:svc, 10 compound:dir. Preserve head and compound/xcomp distinction after mapping | hc-019 covers svc_di but is uncertain; dir is absent. Tạo ra in hc-003 expresses a result, not directed motion |
| Possessives | 587 nmod:poss; 533 have a direct của case marker. Preserve case, map possessive relation to nmod, insert no marker in bare possession | hc-020 has của; hc-015/hc-016 have bare possession, with hc-016 uncertain |
| Topic/comment | 37 dislocated; 15 preverbal obj arcs are only a positional query. Distinguish nsubj/obj/dislocated by role | No topic-tagged sentence yet |
| Particles/emoticons | Discourse: à 10/10, nhé 5/5, đấy 10/17; nha absent; đó has 171 det:pmod and 5 discourse. Initial override limited to :)) | Particle: hc-008/009/017/018; demonstrative đó: hc-006; emoticon: hc-016/017, both uncertain. Degenerate is absent |

The adjacent-verb query also contains one compound:vmod and two obj arcs.
Restricting directional forms to source UPOS VERB reproduces 155 compound:dir,
86 xcomp and 64 compound:svc arcs. Source UPOS is analysis metadata, not a model
feature. Across all forms, the head precedes its dependent in 277/277
compound:dir cases and 509/511 compound:svc cases; the two exceptions are
identified in the JSON report.

The initial :)) override removes recognized tokens before decoding and
reinserts them as discourse dependents of the sentence root. An emoticon-only
sentence uses its first token as root. Root attachment is an approximation
for multiclause sentences. Other emoticons and teencode are not automatically
normalized or covered by this override.

Monitor errors involving evaluative hay, ordinary-noun classifier forms, nha
and the roles of đó. Add broader rules only after evidence justifies them.

## 7. Annotation set

### 7.1. Format and size

[hand_annotated.conllu](data/hand_annotated.conllu) contains hc-001 through
hc-020. Each sentence records its text, source URL/name, access date, register,
synthetic flag, construction tags, uncertain flag and attachment notes. Source
URLs identify news and forum pages; forum usernames/handles are not recorded.

| Measure | Count |
|---|---:|
| Sentences | 20 |
| Whitespace tokens | 254 |
| Source-based sentences, synthetic=false | 20 |
| Synthetic sentences | 0 |
| Formal | 10 |
| Informal | 5 |
| Teencode | 5 |
| Uncertain sentences | 5 |
| Sentences eligible for scoring | 15 |
| Tokens in those sentences | 207 |
| Structurally invalid trees | 0 |
| Nonprojective trees in this set | 0 |

The file uses UTF-8/NFC, LF line endings, ten TAB-separated columns and blank
sentence separators. FORMs exactly match text.split(), UPOS is X and relations
are base labels. Glued punctuation remains inside FORM; an originally separate
hyphen remains its own token. Uncertain trees must still be structurally valid.

Nineteen sentences retain the confirmed access date 16 October 2026; the
replacement hc-015 source was verified on 17 October. The car-purchase sentence
replaces the marathon sentence under the same ID, adding clf_num. The other
19 sentences retain their heads/relations. Counts, coverage and checksums are
in [hand_annotated_check.json](analysis/hand_annotated_check.json).

### 7.2. Construction counts

The eligible column excludes uncertain sentences. A sentence may carry more
than one tag, so column sums are not dataset sizes.

| Tag | Source-based | Synthetic | Eligible sentences | Week 4 minimum |
|---|---:|---:|---:|---:|
| clf_num | 1 | 0 | 1 | 3 |
| clf_bare | 2 | 0 | 2 | 3 |
| clf_noun | 2 | 0 | 2 | 2 |
| coord | 4 | 0 | 4 | 3 |
| hay_or | 0 | 0 | 0 | 2 |
| hay_good | 0 | 0 | 0 | 2 |
| svc_di | 1 | 0 | 0 | 3 |
| dir | 0 | 0 | 0 | 3 |
| poss_cua | 1 | 0 | 1 | 3 |
| poss_bare | 2 | 0 | 1 | 2 |
| topic | 0 | 0 | 0 | 3 |
| particle | 4 | 0 | 3 | 5 |
| do_dem | 1 | 0 | 1 | 2 |
| emoticon | 2 | 0 | 0 | 1 |
| degenerate | 0 | 0 | 0 | 2 |

All retained sentences together cover 10/15 tags and meet Week 2's count/coverage
threshold. Eligible sentences cover eight tags; svc_di and emoticon occur only
in uncertain sentences. Missing tags are hay_or, hay_good, dir, topic and
degenerate. By the end of Week 4 the set must reach 30 sentences, every per-tag
minimum and at least three distinct final particles. Synthetic data must remain
below 20%; the current fraction is zero.

### 7.3. Unresolved annotations

| Sentence | Open decision |
|---|---|
| hc-010 | Rhetorical làm gì mà and the scope of the initial 20 triệu resource phrase |
| hc-011 | Rang→tôm attachment in a food title, provisionally obl |
| hc-016 | Representation of hèn j, especially the fixed relation |
| hc-017 | Representation of chứ sao and each particle's role |
| hc-019 | Role of có in ko có nghỉ, provisionally advmod |

Keep these sentences but exclude them entirely from UAS/LAS until the conventions
are resolved. Independent classmate annotation and agreement have not been
measured. Structural validity does not prove linguistic correctness.

## 8. Tests and structural guarantees

The [annotation contract test](../../tests/test_linguistics_ud_parser_hand_annotated.py)
uses its own CoNLL-U reader without a new dependency. It checks encoding,
metadata, dates, URL/flags, allowed registers/tags, text/FORM alignment, column
count, consecutive IDs, UPOS X, legal heads/labels and root-label equivalence.
It converts each sentence to DependencyParse using idx=ID−1 and HEAD unchanged,
then calls schema and single-rooted-tree validation. File-level checks enforce
unique sentence IDs, at least 20 sentences/10 tags and synthetic below 20%.

[TESTING.md](TESTING.md) specifies the implementation tests:

| Area | Required behavior |
|---|---|
| Projection/oracle | Correct token/head mapping and exact replay of projective gold trees |
| Decoder/guard | Reject cycles, duplicate heads and premature ROOT arcs before mutation |
| Features/training | Deterministic features; correct updates, averaging and model selection |
| Loader/grouping | Round-trip, invalid-file errors, caching and preserved original tokens/UPOS |
| Special cases | Empty/single-token/emoticon-only input and controlled fallback failures |
| Linguistic/adversarial | Classifiers, two hay senses, possession, verbs, topics and particles |
| Full fixture | Parse all 151 stub inputs without modifying fixtures |

The planned runtime pipeline validates input, loads weights, handles supported
emoticons, decodes, maps groups back, reinserts tokens and validates output.
Sentence-level construction failures use a validated star fallback on original
tokens. Invalid input/model files remain errors. Fallback guarantees structure,
not accurate linguistic analysis. Parser tests and gate execution follow
implementation; the current suite result is not a parser gate PASS.

## 9. Limitations and next steps

Current limitations are formal-news training data, five unresolved evaluation
sentences, five absent tags, no independent annotation check and no trained
model results. Grouping can discard predicted arcs; the emoticon override has
limited scope; fallback can produce structurally valid but inaccurate analyses.

The submission includes the consolidated English documents and the supporting
analysis, annotation and test files. VTB, study notes and Vietnamese reference
drafts remain local. No pull request is scheduled for Week 2.

Implementation proceeds by dependency: reader/projection → transitions/oracle
→ features/training → model loader/runtime pipeline → dev evaluation. Report
post-projection invalid/nonprojective counts before filtering train. Never use
fallback as training gold. Extend the evaluation set toward the Week 4 target
and resolve uncertain conventions before reporting per-construction accuracy.

Post-projection corpus counts, encoded vocabulary size, training/loading times,
pruning impact and UAS/LAS remain unmeasured. They will be reported from actual
runs when those components are implemented.

## 10. Deliverables and references

- [Week 2 task](week2_tasks.md), [DESIGN.md](DESIGN.md) and [TESTING.md](TESTING.md).
- [VTB analysis script](scripts/analyze_vtb.py), [statistics](analysis/VTB_COUNTS.md), [JSON inventory](analysis/VTB_COUNTS.json) and [label mapping](analysis/LABEL_MAPPING.md).
- [Annotation set](data/hand_annotated.conllu), [validation/coverage report](analysis/hand_annotated_check.json), [contract test](../../tests/test_linguistics_ud_parser_hand_annotated.py) and [pytest log](analysis/PYTEST_HAND_ANNOTATED.txt).
- [CoNLL-U](https://universaldependencies.org/format.html), [UD clf](https://universaldependencies.org/u/dep/clf.html) and [UD discourse](https://universaldependencies.org/u/dep/discourse.html).

## 11. Data provenance statement

The 20 submitted sentences were selected and processed by the student. The AI-assisted linguistic analyses focused on experimental examples for learning the annotation and design procedure.

AI assistance also covered deterministic conversion of the student's Word
annotation table to CoNLL-U, format and structural validation, and coverage
reporting. The submitted set contains 20 source-based sentences and no synthetic sentences;
the per-tag counts are reported in Section 7.2.


## 12. AI-use disclosure

| Tool | Version/model | Prompts, summarized by purpose | What the AI produced | What the student changed or decided |
|---|---|---|---|---|
| Codex in ChatGPT | Exact Week 2 model/version not recorded | Explain the Week 2 requirements and dependency parsing; compare parser, projection, oracle, feature and training designs; explain linguistic analysis using experimental examples; draft, consolidate, translate and review documents; implement VTB statistics, annotation conversion and contract checks | Design proposals and explanations; experimental linguistic analyses for learning; document and report drafts/translations; VTB analysis code and measured summaries; Word-to-CoNLL-U conversion; annotation format, tree-structure and coverage checks. Earlier local records describe AI suggestions for annotations in the submitted set; the student clarifies that this assistance concerned experimental learning examples. | Selected the architecture and design settings; required preservation of input UPOS and consistent terminology; retained five uncertain cases; reviewed document scope and requested removal of drafts and local-only links |
