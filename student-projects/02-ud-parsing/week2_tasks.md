# Week 2 Tasks — Project 2: UD Dependency Parsing

**Professor's evaluation of your Week 1 submission (`DESIGN.md`, commit
`17bb1b1`) is below, followed by this week's tasks.**

> **Updated 9 October — professor's decision: the parser is now trained on
> UD_Vietnamese-VTB (required).** Everything from "Gaps to close this week"
> onward replaces the 7 October version; the evaluation above is unchanged.
> If you already started on the old tasks, keep that work. Your VTB counts,
> hand-annotated sentences and reworked test plan all carry over.

## Week 1 evaluation: PASS — real research; translate to English

### What I checked

- **Scope:** your diff against `main` touches only
  `student-projects/02-ud-parsing/DESIGN.md`. It is inside your
  `owned_paths`, and there is no code, as Week 1 required.
- **Your four UD_Vietnamese-VTB citations are exact.** I checked each one
  against the treebank's CoNLL-U files (train + dev + test, 3,323
  sentences):
  - `một con đường`: `con` → `một` as `clf`, `một` → `đường` as `nummod`;
  - `Con đường biển Đông…`: `Con` → `đường` as `clf:det`;
  - `Rồi chuyển về tỉnh.`: `về` → `chuyển` as `compound:svc`;
  - `…quyết tâm của nàng dâu…`: `nàng` → `quyết tâm` as `nmod:poss`, and
    `của` → `nàng` as `case`.

  This is real research, not plausible-looking text.
- **Your fixture claims are all correct.** The fixture has no `của`, no
  `à`/`nhé`/`đấy`, no `đi mua`/`chạy ra`, and no `cái`/`chiếc`/`cuốn`.
  `con` and `và` each occur in exactly one distinct sentence.
- **Mapping subtypes to base labels is necessary, and you do it
  correctly.** `UD_DEPREL` in `src/vietnlp/interfaces/_common.py` holds
  base labels only, so `clf:det` → `clf`, `compound:svc` → `compound` and
  `nmod:poss` → `nmod` is what the interface forces.
- **Your tree guarantee is solid.** The design builds exactly one root,
  never lets a rule create a second root, checks every head change for an
  invalid head, a self-loop or a cycle, and rebuilds a fallback tree if
  the result is invalid. Raising `ValueError` on an empty sentence matches
  `validate_dependency_parse`.
- **You read `tests/fixtures/treebank/PROVISIONAL.md` correctly,** both
  for the `của` gap and for `Bộ_phim` as `obj`. You also correctly treat
  that AI-drafted treebank as a reference point, not ground truth.

### What was done well

- Every construction has a citation, and every gap in the fixture is
  documented honestly instead of faked.
- You flagged real ambiguities without being asked:
  - a classifier word used as an ordinary noun;
  - a serial verb vs `xcomp` vs a directional construction;
  - a modal particle vs a demonstrative;
  - non-diacritic `a` not being evidence for `à`.
- You noticed that the stub splits `Giáo dục` / `Đào tạo` into several
  tokens, and that this affects head choice. That is the most important
  open problem in your design (gap 2).

### Required fix: English

`DESIGN.md` is written entirely in Vietnamese. CLAUDE.md's working
agreements are binding for the whole program: **"Docs and code comments
in English."** Project 7 was given the same fix in its Week 1 evaluation.
Translate the prose; Vietnamese example sentences of course stay in
Vietnamese. Do this first (§1).

### Gaps to close this week

1. **Approach: decided by the professor.** See the decision below. It
   replaces your rule-based leaning.
2. **Syllables vs words now matters even more.** You will train on VTB,
   which is annotated over *words*: 18-22% of VTB tokens span several
   syllables (`quyết tâm` is one token). The graded input is the stub's
   *syllables*. A model trained on one tokenization and run on the other is
   mismatched before it starts (§3).
3. **Punctuation differs between VTB and the fixture.**
   - VTB's text keeps punctuation as separate tokens (`đẹp .`).
   - The fixture glues it to the previous token: 88 tokens look like
     `nay.` or `ghê,`.
   - The only standalone non-word tokens in the fixture are ten `:))`
     emoticons. These never occur in VTB, and UD attaches them as
     `discourse` (§3).
4. **Serial verbs: a VTB-trained model inherits VTB's own split.**
   - `compound:dir` is VTB's most frequent label for the directional verbs
     `ra`/`về`/`vào`/`lên`/`xuống` (155 cases, against 86 `xcomp` and 64
     `compound:svc`). It is missing from your analysis.
   - When `đi` is followed by a verb, VTB always makes `đi` the head. But
     it splits the label: 55 `xcomp`, 47 `compound:svc`, 10
     `compound:dir`.

   Decide how the subtypes map to base labels, and whether the
   `compound`/`xcomp` split needs post-processing (§4).
5. **Final particles:**
   - VTB attaches `à` (10 of 10), `nhé` (5 of 5) and `đấy` (10 of 17) as
     `discourse`, so a trained model will learn these.
   - `nha` never occurs in VTB.
   - `đó` is mostly a *demonstrative* in VTB (171 `det:pmod`), but the
     fixture's sentence-final `đó` ("đừng trễ nữa đó") is a particle.

   Plan how you will check the model on all three (§4).
6. **`hay` is a trap.** VTB attaches `hay` ("or") as `cc` 43 times, but
   every occurrence of `hay` in the fixture means "good" (`hay ghê`,
   `hay v`). A model trained on VTB is likely to get this wrong, which
   makes it your first adversarial test (§4, §6).
7. **Your test plan tests the wrong thing.** It lists checks that a
   missing root, multiple roots, invalid heads, self-loops and cycles are
   detected. That is `is_single_rooted_tree`'s job: it is frozen and
   already tested in `tests/test_interfaces_contracts.py`. What *you* must
   test is that **your decoder and guard** never output a cycle or a
   second root (§6).

### Professor's decision: train on VTB (required)

`week1_tasks.md` said there is "no treebank to train against except what
you hand-annotate yourself". That was wrong. UD_Vietnamese-VTB is public:
CC BY-SA 4.0, on GitHub at `UniversalDependencies/UD_Vietnamese-VTB`, with
**1,400 train / 1,123 dev / 800 test** sentences.

**Decision: Project 2's parser is a statistical dependency parser trained
on UD_Vietnamese-VTB.**
- This replaces the rule-based leaning in your Week 1 `DESIGN.md`.
- Hand-written rules are allowed only as **documented overrides**, for
  things VTB cannot teach the model (emoticons, glued punctuation) or
  errors you can show on dev data or on your hand-annotated sentences.
- The six constructions still have to be handled deliberately, and your
  convention cited for each, as `project.md` requires. Now the evidence is
  what the trained model does, checked against VTB and your own sentences.

**Constraints:**
- **Where the weights go:** the trained weights go in
  `src/vietnlp/linguistics/ud_model/`. This commit adds that directory to
  your `owned_paths` in `gate.yaml`. The gate installs a fresh, editable
  copy of the repo and calls `parse()` on all 151 fixture sentences, so
  `parse()` must load committed weights. It cannot train at import time.
- **No new dependencies.** `pyproject.toml` is not in your owned paths.
  Write the parser and the trainer in pure Python, plus `numpy` (already
  installed because pandas needs it). No PyTorch and no scikit-learn.
- **Weights format:** JSON, or `.npz` loaded with `allow_pickle=False`.
  **Never use pickle**: loading a pickle runs arbitrary code, and it can't
  be reviewed. Keep the weights under about 10 MB, pruning rare or
  near-zero features if necessary, and say what you pruned.
- **Licence and attribution:** VTB is CC BY-SA 4.0, and your weights are
  derived from it. Add `ud_model/ATTRIBUTION.md` naming VTB, the version or
  commit you trained on, its licence, and that the weights are derived
  from it. **Don't commit the VTB files themselves.**
- **Reproducibility:** the training script lives under
  `student-projects/02-ud-parsing/` with a fixed random seed. Anyone with
  the same VTB commit can regenerate your weights and get the same dev
  scores.
- **Data splits:** train on `train`, tune on `dev`, and evaluate on `test`
  **once**, at the end, for the final report. Tuning on test is not
  allowed.

### Process notes

- **Schedule:** Week 1 was set on 7 September and you submitted it on
  5 October, so you are about four weeks behind the plan. This week is
  scoped to close the design phase so that Weeks 3-4 can start straight
  after.
- **Environment:** there is no evidence yet that you set it up (Week 1,
  Day 1). This week's report must include the literal `pytest tests -q`
  summary line.

## This week's scope

Finish the design phase (`plan.md` Weeks 1-2):
- translate `DESIGN.md` into English;
- **design the VTB-trained parser** precisely enough that Weeks 3-4 are
  implementation, not more design;
- measure VTB with your own scripts;
- start your hand-annotated evaluation set.

**Still no `ud_parser.py` and no training code**: those start in Weeks
3-4. Analysis scripts that read and count VTB are allowed now, under
`student-projects/02-ud-parsing/scripts/`.

### Data rule (binding from Week 2 on)

**Collect and annotate all data by hand. Do not use AI, an LLM, or any
generative or trained model to produce data.**

- **Training on VTB is the required method, not a breach of this rule.**
  VTB is published, human-annotated data. You may read it, count it,
  convert it with deterministic code you wrote, and train on it.
- **No model may produce or pre-annotate your data, including your own
  parser.** Never parse a sentence and then "correct" the result into your
  hand-annotated set. That is exactly how an evaluation set inherits a
  model's errors and then rewards them. No other parser (underthesea,
  VnCoreNLP, Stanza, UDPipe, trankit, PhoNLP, DeepSeek…) and no LLM may be
  used either.
- **Word lists** (§7) are data, so build them by hand and cite sources.

**You may use:**
- your own reading and judgment as a Vietnamese speaker;
- public pages you read yourself;
- grammars and dictionaries;
- VTB;
- plain deterministic code you wrote yourself.

If you're unsure whether a tool counts, ask before you use it.

**The VTB counts in this file came from an AI-assisted evaluation.
Reproduce them with your own script before you cite them** (§4). Any
example strings here illustrate a pattern; don't copy them into your data.

### 0. Environment (do first)

```
python3.11 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest tests -q
```

The suite must be green. Paste the summary line into your report.

### 1. Translate `DESIGN.md` to English

Keep the substance; this is a language change, not a rewrite. You may
keep a Vietnamese draft alongside it if that helps you write, but the
version that ships on your branch must be in English. Then mark the
Week 1 "rule-based" decision as superseded by the professor's decision,
and say why in one line.

### 2. Design the VTB-trained parser (new `DESIGN.md` section)

Specify each item precisely enough to implement in Weeks 3-4:

- **Parser family.**
  - **Transition-based** (arc-standard, arc-eager or arc-hybrid, scored by
    an averaged perceptron) is the usual choice in pure Python, and its
    transition system builds a tree by construction.
  - **Graph-based** scoring needs a maximum-spanning-tree decoder
    (Chu-Liu/Edmonds) to guarantee a tree.

  Pick one and justify it.
- **Projectivity.** VTB is almost entirely projective: 5 of 1,400 train
  trees are non-projective, 9 of 1,123 dev, 1 of 800 test. Reproduce
  these counts, and decide what to do with the non-projective training
  trees, e.g. skip them.
- **Single root.** UD requires exactly one token with `head = 0`. Some
  transition systems can finish with several tokens attached to ROOT, so
  say how yours prevents that.
- **Labels.** Either map VTB subtypes to base labels before training,
  which gives a smaller label set, or predict full labels and map them at
  output. Either way, every emitted `deprel` must be in `UD_DEPREL`. List
  the complete mapping as a table.
- **Features: only what `parse()` sees at test time.**
  - The input is token forms (with `upos="X"` from the stub) plus the
    structure built so far.
  - VTB has gold UPOS, but your input never will. Training on gold UPOS
    and testing on `X` gives a model that silently depends on a signal
    that is absent. Don't use UPOS features unless you train with what the
    input really carries.
  - List your feature templates.
- **Training regime:** number of epochs, shuffling with a fixed seed, and
  weight averaging. Which dev scores (UAS/LAS) decide when to stop, and
  whether you retrain on train + dev after tuning.
- **Weights:** the format, the size budget, and the pruning rule. How
  `parse()` loads them, and how long loading may take, given the gate
  parses 151 sentences.
- **Overrides:** list each hand-written rule you expect to need (e.g.
  emoticon → `discourse`). Each must be justified by evidence: VTB can't
  teach it, or dev or hand-annotated errors show it.
- **Safety net:** keep your Week 1 validation and fallback tree as a last
  resort after decoding (§6).

### 3. Make training input look like test input

Train and test inputs must match:
- **The graded input** is stub tokens: one whitespace syllable each,
  punctuation glued on, and `upos="X"`.
- **VTB** is word tokens, with punctuation as separate tokens.

Specify a **deterministic projection of every VTB tree onto stub-style
tokens:**
- **Syllables:** split each multi-syllable VTB word into its syllables.
  The word's arcs to and from the outside go through one syllable, and the
  other syllables attach to it with a fixed label. Choose that syllable
  and that label, and justify them. UD's `goeswith` is *not* the answer:
  UD reserves it for "text that is not well edited", and the space between
  Vietnamese syllables is correct orthography.
- **Punctuation:** decide whether to glue it onto the previous token, as
  the fixture does, and what happens to that punctuation token's arc.
  Justify the choice, ideally by comparing dev scores with and without
  gluing in Weeks 3-4.
- **Checks:** every projected tree must pass `is_single_rooted_tree`.
  Report how many fail before and after any fixes.
- **Real Project 1 input** (word tokens, possibly joined with `_`): decide
  how `parse()` will handle it. One option is to split into syllables
  internally and project the result back. **The output tokens must always
  be exactly the input tokens.** Design it now; implement it later.
- **Emoticons** (`:))`) never occur in VTB: override them to
  `discourse`. UD's `discourse` page lists "emojis/emoticons with an
  extra-syntactic expressive function".

### 4. The six constructions under a trained model

**Count VTB yourself first.** Download `vi_vtb-ud-{train,dev,test}.conllu`
from GitHub, keep them on your machine (don't commit them), and count
deprels with your own script. Cite the counts in `DESIGN.md` with the VTB
version or commit you used.

**For each construction, `DESIGN.md` must give:**
- VTB's convention, with your counts;
- your base-label mapping;
- what you expect the model to do on stub input;
- the hand-annotated sentences (§5) you will check it on;
- any override, and why.

**Specifically:**
- **Classifiers:**
  - `clf` attached to the numeral vs `clf:det` attached to the noun (both
    become `clf`);
  - a classifier word used as an ordinary noun: `con` in VTB is a noun
    (`nsubj`/`obj`) almost as often as a classifier.
- **Coordination:** `và` and `hoặc` as `cc`, and the `hay` trap (gap 6).
  How will you detect that the model gets `hay` = "good" wrong, and what
  do you do if it does?
- **Serial verbs and directional verbs:**
  - the head is the first verb, which VTB is consistent on;
  - the label inherits VTB's own split.
  - Decide: accept what the model predicts (after mapping to base labels),
    or post-process into a single written rule. Justify either choice.
- **`của` possessives:** `case` + `nmod`, which is settled. Also cover the
  fixture's bare possessive in `Con mèo nhà tao…`.
- **Topic-comment fronting:**
  - check how VTB analyses fronted objects (VTB uses `dislocated` only 37
    times);
  - say what you expect on the fixture's `Bộ phim tối qua coi hay ghê…`.
- **Final particles:**
  - `à`/`nhé`/`đấy` are learned from VTB;
  - `nha` is unseen in VTB: does it need an override?
  - `đó` as a particle vs as a demonstrative;
  - emoticons are handled by the override in §3.

### 5. Hand-annotated evaluation set

**Role:** VTB is formal news. Your hand-annotated sentences are the
**out-of-domain evaluation set**: informal text, teencode, and the
fixture's registers. It is the only measure of how your VTB-trained model
does on the kind of text this platform actually ingests.

Create `student-projects/02-ud-parsing/data/hand_annotated.conllu`. It is
in your owned paths; `tests/fixtures/**` is forbidden. **This week: at
least 20 sentences covering at least 10 of the tags below. By the end of
Week 4: at least 30 sentences, meeting every minimum.**

**Where to look.** Read the pages yourself:
- public news, government portals and Vietnamese Wikipedia;
- public forums and Q&A sites, for informal and teencode text.

**Not allowed:** social media, anything behind a login, scraping scripts,
and copying sentences out of VTB.

**Format: standard CoNLL-U, with these comment lines per sentence:**

```
# sent_id = hc-001
# text = <sentence verbatim, NFC>
# source_url = https://...
# source_name = ...
# accessed = YYYY-MM-DD
# register = formal | informal | non_diacritic | teencode | mixed
# synthetic = false
# constructions = clf_num, particle
# uncertain = false
# notes = which DESIGN.md conventions decided the hard attachments
```

**Columns:**
- `FORM`s must equal `text.split()`, exactly as `stub_segment` produces
  them. Glued punctuation stays inside the `FORM`.
- `UPOS` = `X`.
- `HEAD` and `DEPREL` follow your §3 projection convention, with base
  labels from `UD_DEPREL` only.
- Optional: record VTB's finer label in `MISC`, e.g. `VTB=compound:dir`.

**Coverage targets (end of Week 4).** The counts are real instances. If
you can't find a pattern in real text, write sentences yourself and mark
them `synthetic = true`. Keep synthetic sentences under 20% of the set and
list them in your report.

| Tag | What | Minimum |
|---|---|---|
| `clf_num` | numeral + classifier + noun | 3 |
| `clf_bare` | classifier directly before a noun | 3 |
| `clf_noun` | a classifier word used as an ordinary noun | 2 |
| `coord` | coordination with `và` / `hoặc` | 3 |
| `hay_or` | `hay` meaning "or" | 2 |
| `hay_good` | `hay` meaning "good" / "interesting" | 2 |
| `svc_di` | `đi` + verb | 3 |
| `dir` | motion verb + directional (`ra`, `vào`, `lên`, `xuống`, `về`) | 3 |
| `poss_cua` | `của` possessive | 3 |
| `poss_bare` | possessive without `của` | 2 |
| `topic` | fronted topic or object | 3 |
| `particle` | sentence-final particle, at least three different ones | 5 |
| `do_dem` | `đó` as a demonstrative | 2 |
| `emoticon` | an emoticon or emoji in running text | 1 |
| `degenerate` | a one-token sentence; an emoticon- or punctuation-only sentence | 2, synthetic allowed |

**Annotation protocol:**
- Annotate using your `DESIGN.md` conventions only, never your parser.
  If the conventions don't decide an attachment, fix the convention first
  and record it in a decisions log, then annotate.
- If you can't decide, set `uncertain = true`. The sentence stays in the
  set but is excluded from scoring.
- Recommended: ask a classmate to annotate 5 sentences using only your
  conventions, without seeing your trees. Report UAS/LAS agreement,
  computed by your own script. That agreement is the ceiling against
  which your model's scores on this set should be read.

**Privacy and licensing:** public content only, single sentences with the
URL, never whole articles. Prefer public figures, and never record forum
usernames or handles.

**Contract test:** write `tests/test_linguistics_ud_parser_hand_annotated.py`,
which is covered by your `own_test_glob`. Use your own CoNLL-U reader, not
a new library. The test must check that:
- every sentence carries the metadata, with a `source_url` or
  `synthetic = true`;
- the text is NFC;
- the `FORM`s equal `text.split()`;
- every `DEPREL` is in `UD_DEPREL`;
- converted to `interfaces.ud.DependencyParse` (`idx = ID - 1`,
  `head = HEAD`), every sentence passes `is_single_rooted_tree`;
- every tag is from the table.

It is test code, not parser code, so it is allowed this week.

### 6. Make the tree guarantee testable

Specify in `DESIGN.md` how a valid tree is guaranteed:
- **the decoder:** the transition system or MST decoder, including how a
  single root is enforced;
- **the final validation and fallback** from your Week 1 design.

Then rewrite the test plan around *your* code:

| Gate class | What the test checks |
|---|---|
| `cycle` | the guard or decoder refuses an attachment that would close a cycle, and the final tree is valid |
| (single root) | a configuration where the model would attach two tokens to ROOT ends with exactly one root |
| `degenerate` | an empty sentence (`ValueError`, as you planned), a one-token sentence, and an emoticon-only sentence |
| `adversarial` | the `hay` = "good" trap, and a classifier word used as a noun |
| `clf` / `classifier` | classifier attachments on your §5 sentences |

Delete the planned tests that only exercise `is_single_rooted_tree`
itself.

### 7. Word lists (only if your features or overrides need them)

If a feature template or an override uses a closed list (classifiers,
particles, emoticons, …), build it by hand. Give a source for each list (a
grammar, a dictionary, or your own VTB counts), and mark ambiguous entries
(`con`, `hay`, `đó`).

## Self-check before you call Week 2 done

- [ ] The environment works, and the `pytest tests -q` summary line is in
      `WEEK2_REPORT.md` (English).
- [ ] `DESIGN.md` is in English, and the rule-based decision is marked as
      superseded.
- [ ] The parser design (§2) specifies the family, projectivity handling,
      single root, label mapping table, test-time-only features, training
      regime, weights format and budget, overrides, and safety net.
- [ ] The projection of VTB onto stub-style tokens (§3) is specified,
      including the syllable label, the punctuation decision and real
      Project 1 input.
- [ ] Your own scripts reproduce the VTB counts cited in §2 and §4. The
      scripts are committed under `scripts/`; the VTB files are not.
- [ ] Each of the six constructions has VTB's convention, the mapping,
      the expected model behaviour, evaluation sentences, and any override.
- [ ] `data/hand_annotated.conllu` has at least 20 sentences covering at
      least 10 tags, and the contract test passes.
- [ ] The test plan targets your decoder and guard, not the frozen
      checker.
- [ ] The report contains this statement: *"No AI, LLM, or generative or
      trained model was used to find, write, translate, annotate or clean
      any data in this submission."* It also gives counts per tag (real
      and synthetic).
- [ ] There is still no `ud_parser.py` and no training code.

## What NOT to do this week

- **Don't use AI, an LLM, or any model, including your own parser, to
  produce or pre-annotate data.** See the data rule above.
- Don't write `ud_parser.py` or training code yet; they start in Weeks
  3-4.
- Don't commit the VTB files, and don't add dependencies
  (`pyproject.toml` is outside your owned paths).
- Don't use pickle for weights, ever.
- Don't use gold UPOS features that the graded input will never carry.
- Don't evaluate on VTB `test` more than once, at the end.
- Don't touch `src/vietnlp/interfaces/**`, `src/vietnlp/platform/**`,
  `src/vietnlp/acquisition/**`, `src/vietnlp/curation/**`, Project 1's
  and Project 3's files, `tests/fixtures/**`, or
  `student-projects/_gate/**`.

## Commit & push

Commit as you go: translation, parser design, projection design, VTB
scripts, then annotation batches, then the contract test. Don't make one
commit at the end; your commit history is reviewed.

```
git add student-projects/02-ud-parsing/ tests/test_linguistics_ud_parser_hand_annotated.py
git commit -m "Week 2: English DESIGN, VTB-trained parser design, projection, hand-annotated set"
git push origin student/02-ud-parsing
```

This is still not a Pull Request; that comes in Week 15.

## Looking ahead (revised for a trained parser)

- **Weeks 3-4:** TDD the VTB reader, the projection onto stub tokens
  (every projected tree valid), and the oracle (gold transitions
  reproduce the gold tree). Train end to end on a small subset. Have
  `parse()` load committed weights and return a valid tree for every
  fixture sentence. The gate's schema and tree checks should pass from
  here on.
- **Weeks 5-6:** full training on VTB `train`, tuned on `dev`; weights
  committed with attribution. Run over all 151 fixture sentences.
- **Weeks 7-8:** the six constructions, using your §5 set: per-construction
  errors, and overrides only where the evidence demands them.
- **Weeks 9-14:** as in `plan.md`. The golden test checks tree validity;
  your final report gives UAS/LAS on VTB `test` (once) and on your
  hand-annotated set.
