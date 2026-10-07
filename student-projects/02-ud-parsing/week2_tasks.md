# Week 2 Tasks — Project 2: UD Dependency Parsing

**Professor's evaluation of your Week 1 submission (`DESIGN.md`, commit
`17bb1b1`) is below, followed by this week's tasks.**

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

1. **The approach decision rests on one sentence.** Week 1 allowed a
   leaning, but Week 2 must lock it with a real comparison (§2).
2. **Syllables vs words is unresolved.** The stub gives you one token per
   *syllable*, while VTB's conventions are defined over *words*:
   `quyết tâm` is one VTB token. You must not segment words, which is
   Project 1's job. So your design must say how the parser attaches tokens
   it cannot group, and how it copes with real Project 1 output, where
   syllables may be joined by a space or by `_` (§3).
3. **Your planned `punct` rule will almost never fire on the graded
   input.** The stub leaves punctuation glued to the previous token: 88
   tokens in the fixture look like `nay.` or `ghê,`. The only standalone
   non-word tokens are ten `:))` emoticons, and UD attaches emoticons as
   `discourse`, not `punct` (§4).
4. **Serial verbs: your head rule is right, but there is no label rule.**
   `compound:dir` is missing from your analysis, yet it is VTB's most
   frequent label for the directional verbs `ra`/`về`/`vào`/`lên`/`xuống`
   (155 cases, against 86 `xcomp` and 64 `compound:svc`). When `đi` is
   followed by a verb, VTB always makes `đi` the head, as your rule says.
   But VTB splits the label: 55 `xcomp`, 47 `compound:svc`, 10
   `compound:dir`. With base labels only, you need a written rule for
   `compound` vs `xcomp` (§4).
5. **Final particles can be settled from the data.** VTB attaches `à`
   (10 of 10), `nhé` (5 of 5) and `đấy` (10 of 17) as `discourse`.
   - `đó` is mostly a *demonstrative* in VTB (171 `det:pmod`), so the
     fixture's sentence-final `đó` ("đừng trễ nữa đó") needs a rule that
     tells the two uses apart.
   - `nha` never occurs in VTB, so it needs an argued analogy with `nhé`.
6. **`hay` is a trap.** VTB attaches `hay` ("or") as `cc` 43 times. But
   every occurrence of `hay` in the fixture means "good"
   (`hay ghê`, `hay v`). A coordination rule copied from VTB would be
   wrong on every graded occurrence, which makes it a natural adversarial
   test.
7. **Your test plan tests the wrong thing.** It lists checks that a
   missing root, multiple roots, invalid heads, self-loops and cycles are
   detected. That is `is_single_rooted_tree`'s job: it is frozen and
   already tested in `tests/test_interfaces_contracts.py`. What *you* must
   test is that **your parser's own guard** refuses to create a cycle or a
   second root. The gate's required `cycle` test case is that test (§6).

### Correction to the Week 1 task text

`week1_tasks.md` said there is "no treebank to train against except what
you hand-annotate yourself". That is wrong. UD_Vietnamese-VTB is public
(CC BY-SA 4.0, 3,323 sentences, on GitHub at
`UniversalDependencies/UD_Vietnamese-VTB`). This doesn't force a change to
your rule-based leaning. VTB is annotated over words, whereas your graded
input is syllables from the stub, with `upos="X"` on every token. Weigh
that in §2. **If you want to train on VTB, make the case in your report.
Training on it needs the professor's approval before you build anything.**

### Process notes

- **Schedule:** Week 1 was set on 7 September and you submitted it on
  5 October, so you are about four weeks behind the plan. This week is
  scoped to close the design phase so that Weeks 3-4 can start straight
  after. The sentences you annotate this week (§5) become your Weeks 3-4
  test cases, so they are not extra work.
- **Environment:** there is no evidence yet that you set it up (Week 1,
  Day 1). This week's report must include the literal `pytest tests -q`
  summary line.

## This week's scope

Finish the research and design phase (`plan.md` Weeks 1-2):
- translate `DESIGN.md` into English;
- lock the approach;
- settle every one of the six constructions, or scope it out with a
  written reason;
- annotate real sentences by hand to prove your conventions can be
  applied.

**Still no `ud_parser.py`**: that starts in Weeks 3-4.

### Data rule (binding from Week 2 on)

**Collect and annotate all data by hand. Do not use AI, an LLM, or any
generative or trained model to produce data.** This covers:

- **Finding or writing example sentences.** No chatbot, and no prompts
  such as "give me sentences with classifiers".
- **Dependency annotation.** No parser (underthesea, VnCoreNLP, Stanza,
  UDPipe, trankit, PhoNLP, DeepSeek or any other) may pre-annotate a tree,
  even if you correct it afterwards.
- **Building the closed-class word lists** (§7).
- **Translating, cleaning or re-spelling data text.** (Translating your
  own `DESIGN.md` prose is writing, not data. Do it yourself.)

**You may use:**
- your own reading and judgment as a Vietnamese speaker;
- public pages you read yourself;
- grammars and dictionaries;
- the **published, human-annotated** VTB treebank, as a reference you read
  and count with code you wrote yourself (§4);
- plain deterministic code you wrote yourself (e.g. a CoNLL-U reader).

If you're unsure whether a tool counts, ask before you use it.

**Why:** the fixture lacks most of your six constructions, and the
treebank fixture is AI-drafted. The only real evidence for your
conventions is real text that you annotate yourself. **The VTB counts in
this file came from an AI-assisted evaluation, so reproduce them with your
own script before you cite them (§4).** Any example strings here
illustrate a pattern; don't copy them into your data.

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
version that ships on your branch must be in English. Do the rest of this
week's work in the English version.

### 2. Lock the approach

Replace the one-sentence justification with a real comparison of:
- **(a)** rules over lexical cues. UPOS is `X` on stub input, so the rules
  can only use word forms, position and your closed-class word lists;
- **(b)** a statistical parser trained on VTB, which needs approval (see
  above);
- **(c)** training only on what you annotate yourself.

Judge each option on four points:
- whether it can *guarantee* a valid tree;
- how it behaves on syllable-level stub input vs word-level real Project 1
  input;
- whether you can explain each decision it makes;
- whether it fits the time left.

**State your decision.** It may not stay open past this week.

### 3. Token granularity rule

- **Write every rule in terms of tokens, never syllables.** A token may be
  one syllable (stub input) or a multi-syllable word (real Project 1
  output), possibly joined with `_`. Word-list lookups must normalize
  `_` ↔ space, NFC and case.
- **Choose one default for tokens your rules cannot analyse**, such as the
  syllables of a word the stub split apart: what they attach to, and with
  which label. Use it the same way everywhere, because consistency is what
  makes trees comparable.

  UD's `goeswith` is *not* the answer. UD reserves it for "text that is
  not well edited", and the space between Vietnamese syllables is correct
  orthography.
- **Do not build a word segmenter.** Grouping syllables into words is
  Project 1's job, so your word lists hold closed-class function words
  only (§7), never a content-word dictionary.
- **Say what you expect to be right on stub input**: function-word
  attachments such as `của`/`case`, `và`/`cc`, particles/`discourse` and
  classifiers/`clf`. Also say what only improves once real word
  segmentation arrives. Stub-input trees will be valid but coarse; that is
  acceptable if it is documented.

### 4. Settle the six constructions, with your own VTB counts

**Get the data and count it yourself.**
- Download VTB's `vi_vtb-ud-{train,dev,test}.conllu` from GitHub. Keep the
  files on your machine; **don't commit them** (they're large, and the
  share-alike licence needs attribution).
- Count deprels with a script you write yourself.
- Cite the counts in `DESIGN.md`, giving the VTB version or commit you
  used.

**For each construction, `DESIGN.md` must give:**
- the head choice;
- the base label, with VTB's subtype noted next to it;
- your VTB counts;
- the fixture example, or "gap";
- your hand-annotated examples from §5.

**Specifically:**

- **Classifiers:**
  - when `clf` attaches to the numeral and when to the noun (VTB `clf`
    vs `clf:det`);
  - how a classifier word used as an ordinary noun is recognized.
    `con` in VTB is a noun (`nsubj`/`obj`) almost as often as a
    classifier.
- **Coordination:**
  - rules for `và` and `hoặc`;
  - a rule that tells `hay` meaning "or" apart from `hay` meaning
    "good" (gap 6).
- **Serial verbs and directional verbs:**
  - the head is the first verb, which matches VTB;
  - write the `compound` vs `xcomp` label rule, covering both
    `compound:svc` and `compound:dir`;
  - document that VTB itself splits `đi`+verb between `xcomp` and
    `compound:svc`, so your rule is a decision, not a copy.
- **`của` possessives:** settled. Also cover the bare (no-`của`)
  possessive in the fixture's `Con mèo nhà tao…`.
- **Topic-comment fronting:**
  - decide between `obj`, `nsubj` and `dislocated` for a fronted element
    (VTB uses `dislocated` only 37 times; check how VTB analyses fronted
    objects);
  - cite your decision;
  - apply it to the fixture's `Bộ phim tối qua coi hay ghê…`.
- **Final particles:**
  - `discourse` for `à`, `nhé` and `đấy`, citing your counts;
  - `nha` by an argued analogy with `nhé`;
  - a rule for `đó` as a particle vs as a demonstrative;
  - emoticons such as `:))` → `discourse` (UD's `discourse` page lists
    "emojis/emoticons with an extra-syntactic expressive function").
- **Punctuation:** `punct` applies only to standalone punctuation tokens.
  Glued punctuation stays inside its token, because input tokens are
  never altered.

### 5. Hand-annotated sentences

Create `student-projects/02-ud-parsing/data/hand_annotated.conllu`. It is
in your owned paths; `tests/fixtures/**` is forbidden. **Target: at least
30 sentences.**

**Where to look.** Read the pages yourself:
- public news, government portals and Vietnamese Wikipedia, for formal
  text;
- public forums and Q&A sites, for informal and teencode text.

**Not allowed:** social media, anything behind a login, scraping scripts,
and copying sentences out of VTB. VTB is your reference, not your data.

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
- `FORM`s must equal `text.split()` in order. That is exactly what
  `stub_segment` produces, so glued punctuation stays inside the `FORM`,
  and your parser's output can later be compared with your annotation
  token by token.
- `UPOS` = `X` (as the stub gives it; POS tagging is Project 1's job).
- `HEAD` and `DEPREL` are filled in, with `DEPREL` from `UD_DEPREL` only
  (base labels).
- Optional: record VTB's finer label in `MISC`, e.g. `VTB=compound:dir`.

**Coverage required.** The counts are real instances. If you can't find
a pattern in real text, write sentences yourself and mark them
`synthetic = true`. Keep synthetic sentences under 20% of the set and
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
- Annotate using your `DESIGN.md` conventions only. If they don't decide
  an attachment, fix the convention first, record it in a decisions log
  in `DESIGN.md` naming the sentence that forced it, then annotate.
- If you can't decide, set `uncertain = true`. The sentence stays in the
  set but is excluded from pass/fail tests.
- Recommended: ask a classmate to annotate 5 sentences using only your
  conventions, without seeing your trees. Report unlabelled and labelled
  attachment agreement (UAS/LAS), computed by your own script.

**Privacy and licensing:** public content only, single sentences with the
URL, never whole articles. Prefer public figures, and never record forum
usernames or handles.

**Contract test:** write `tests/test_linguistics_ud_parser_hand_annotated.py`,
which is covered by your `own_test_glob`. Use your own CoNLL-U reader, not
a new library: `pyproject.toml` is not in your owned paths, so you cannot
add dependencies. The test must check that:
- every sentence carries the metadata above, with a `source_url` or
  `synthetic = true`;
- the text is NFC;
- the `FORM`s equal `text.split()`;
- every `DEPREL` is in `UD_DEPREL`;
- converted to `interfaces.ud.DependencyParse` (`idx = ID - 1`,
  `head = HEAD`), every sentence passes `is_single_rooted_tree`;
- every construction tag is from the table.

It is test code, not parser code, so it is allowed this week. It is also
how you'll find out whether your environment works.

### 6. Make the tree guarantee testable

**In `DESIGN.md`, specify the guard** as pseudocode for a single
attachment function: for example `attach(heads, dependent, head) -> bool`.
It refuses an out-of-range head, a self-loop, a second root, and any
attachment that would close a cycle. Every rule must go through it. You
will TDD it first, in Week 3.

**Rewrite the test plan around your parser, not the interface:**

| Gate class | What the test checks |
|---|---|
| `cycle` | two rules would attach two tokens to each other; the guard refuses the second, and the final tree is valid |
| `degenerate` | an empty sentence (`ValueError`, as you planned), a one-token sentence, and an emoticon-only sentence |
| `adversarial` | the `hay` trap, and a classifier word used as a noun |
| `clf` / `classifier` | your classifier rules on your §5 sentences |

Delete the planned tests that only exercise `is_single_rooted_tree`
itself.

### 7. Closed-class word lists (built by hand, with sources)

With `upos="X"`, closed-class words are your main cue. Draft these lists
as tables in `DESIGN.md` or as files under `data/`:
- classifiers;
- coordinating conjunctions;
- adpositions (`của`, …);
- sentence-final particles;
- directional verbs;
- negators;
- the copula `là`.

For each list, give its source: a grammar, a dictionary, or your own VTB
counts. Mark every entry that is ambiguous (`con`, `hay`, `đó`, `ra`,
`về`) and say which rule resolves it.

## Self-check before you call Week 2 done

- [ ] The environment works, and the `pytest tests -q` summary line is in
      `WEEK2_REPORT.md` (English).
- [ ] `DESIGN.md` is in English.
- [ ] The approach is locked, with the three-way comparison from §2.
- [ ] The token-granularity rule is written, including the default for
      unanalysable tokens and a note on what stub input will get right.
- [ ] Each of the six constructions has a head, a base label, your own
      VTB counts, the fixture example or gap, and §5 examples, or is
      scoped out with a written reason.
- [ ] `data/hand_annotated.conllu` has at least 30 sentences and meets the
      coverage table. Synthetic sentences are under 20% and listed in the
      report. The contract test passes.
- [ ] The guard is specified in `DESIGN.md`, and the test plan targets
      your parser, not the frozen checker.
- [ ] The closed-class word lists are drafted with sources, and ambiguous
      entries are marked.
- [ ] The report contains this statement: *"No AI, LLM, or generative or
      trained model was used to find, write, translate, annotate or clean
      any data in this submission."* It also gives counts per
      construction tag (real and synthetic), and the classmate UAS/LAS if
      you did the second annotation.
- [ ] There is still no `ud_parser.py`.

## What NOT to do this week

- **Don't use AI, an LLM, or any parser or model for data.** See the data
  rule above.
- Don't write `ud_parser.py` yet; it starts in Weeks 3-4.
- Don't build a word segmenter or a content-word dictionary; that is
  Project 1's job.
- Don't commit the VTB files, and don't change `pyproject.toml` (it is
  outside your owned paths).
- Don't train anything on VTB without the professor's approval.
- Don't touch `src/vietnlp/interfaces/**`, `src/vietnlp/platform/**`,
  `src/vietnlp/acquisition/**`, `src/vietnlp/curation/**`, Project 1's
  and Project 3's files, `tests/fixtures/**`, or
  `student-projects/_gate/**`.

## Commit & push

Commit as you go: translation, then each construction, then annotation
batches, then the contract test. Don't make one commit at the end; your
commit history is reviewed.

```
git add student-projects/02-ud-parsing/ tests/test_linguistics_ud_parser_hand_annotated.py
git commit -m "Week 2: English DESIGN, approach locked, conventions, hand-annotated sentences"
git push origin student/02-ud-parsing
```

This is still not a Pull Request; that comes in Week 15.

## Looking ahead

**Weeks 3-4:** TDD the guard first, then a skeleton `parse()` over stub
input that always returns a valid tree. Then add rules one construction at
a time, each checked against your §5 sentences. Your own tests must
eventually cover the gate's required classes: `clf`, `classifier`,
`cycle`, `degenerate` and `adversarial`.

**Weeks 5-6:** run over all 151 fixture sentences. The fixture checks
tree validity at scale; only your hand-annotated set measures whether
your attachments are right.
