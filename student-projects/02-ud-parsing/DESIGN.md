# Vietnamese UD Parser Design

**Student:** Lê Quốc Huy — **Student ID:** 2511310

**Project:** 02 — Vietnamese UD Dependency Parsing

**Updated:** 25 October 2026

## 1. Architecture and scope

The parser will use **arc-standard transition-based decoding with an averaged
multiclass perceptron**, trained on UD_Vietnamese-VTB (VTB). Implementation uses
Python and NumPy without additional dependencies.

**Superseded decision:** the Week 1 preference for a rule-based parser was
replaced by the professor's 9 October 2026 decision requiring training on VTB.
Handwritten rules are limited to documented overrides supported by missing
training evidence or measured errors. The star tree is a structural fallback,
not the main parsing method.

Arc-standard makes the state, actions and structural constraints explicit and
fits the implementation budget. Its basic form produces projective trees.
The reader, label mapping, projection, transitions and static oracle are
implemented. Features, training and the public `parse()` entry point remain
Week 4 work. Accuracy remains to be measured.

The public entry point is:

```python
parse(sentence: SegmentedSentence) -> DependencyParse
```

Segmentation and POS tagging belong to Project 1. Project 2 preserves the input
tokens and predicts their heads and dependency labels.

## 2. Data and reproducibility

Use [UD_Vietnamese-VTB](https://github.com/UniversalDependencies/UD_Vietnamese-VTB/tree/3c971fd1c5d03561e00b267d3d0057b81a9bea84),
commit `3c971fd1c5d03561e00b267d3d0057b81a9bea84`, under CC BY-SA 4.0.
Keep the corpus outside the repository. Commit the analysis script and reports,
not the VTB files.

| Split | Sentences | Word tokens | Multisyllabic tokens | Invalid source trees | Nonprojective source trees |
|---|---:|---:|---:|---:|---:|
| Train | 1,400 | 20,215 | 4,535 | 0 | 5 |
| Dev | 1,123 | 26,162 | 5,497 | 0 | 9 |
| Test | 800 | 11,692 | 2,079 | 0 | 1 |

[analyze_vtb.py](scripts/analyze_vtb.py) verifies SHA-256 values, reads integer-ID
basic dependency nodes and reproduces these counts. Projectivity is checked
both by crossing arcs, including the artificial ROOT arc, and by the descendant
condition for every token spanned by an arc. The results agree on the source
corpus. Detailed queries, sentence IDs and hashes are in
[VTB_COUNTS.md](analysis/VTB_COUNTS.md) and [VTB_COUNTS.json](analysis/VTB_COUNTS.json).

Train only on valid, projective trees **after projection**. Record each excluded
training sentence and its reason. Do not infer the post-projection exclusion
count from the five nonprojective source trees. Keep all dev/test sentences,
including nonprojective ones, for evaluation. Repair invalid data preparation
before an experiment rather than silently dropping evaluation sentences.

Measured with [project_vtb.py](scripts/project_vtb.py), after projection:

| Split | Syllable tokens | Invalid projected trees | Nonprojective projected trees |
|---|---:|---:|---:|
| Train | 22,099 | 0 | 5 |
| Dev | 28,432 | 0 | 9 |
| Test | 12,191 | 0 | 1 |

Exclude train-s414, train-s435, train-s498, train-s518 and train-s955 for
non-projectivity after projection. The remaining 1,395 train sentences contain
22,000 syllable tokens. Static-oracle replay reconstructs every gold head and
label in 44,000 legal actions, with **0 failures**. Counts and exclusion reasons
are recorded in [PROJECTION_COUNTS.md](analysis/PROJECTION_COUNTS.md) and
[PROJECTION_COUNTS.json](analysis/PROJECTION_COUNTS.json).

Tune on dev only. Evaluate the trained model on VTB test once, after fixing the
model and pipeline. Source-corpus inventory counts are not model test scores.

## 3. Input, output and labels

The input is Project 1's `SegmentedSentence`, initially supplied by its frozen
whitespace-based stub with `upos="X"`. Validate the input and additionally
require unique, consecutive token indices `0…m-1` and a nonempty tuple of
nonempty, whitespace-free syllable strings for each token. Reject empty input
with `ValueError`; retain the validator's schema error type for schema failures.
Do not repair malformed input silently.

The output must preserve `sent_id`, token count, order, `idx`, `form` and valid
input UPOS. Convert missing UPOS (`None`) to `X`. Set `source="real"`.
`UDToken.idx` is zero-based; HEAD is zero for the root and otherwise the
one-based position of the head token. Do not emit an artificial ROOT token.

Only base labels in the frozen `UD_DEPREL` inventory may be emitted. Map VTB
subtypes to the part before the first colon **before training**, preserving
attachment direction. For example, `clf:det → clf`, `compound:svc → compound`,
`compound:dir → compound` and `nmod:poss → nmod`. The 84 observed source labels
map to 34 observed base labels. Unobserved interface labels remain valid.
Projection also adds within-word `dep` arcs. Section 14 contains the complete
mapping; [LABEL_MAPPING.md](analysis/LABEL_MAPPING.md) is the generated source.

The prediction classes are `SHIFT`, `LEFT_ARC(r)` for each non-root interface
label, and `RIGHT_ARC(r)` for each interface label. Action legality further
restricts this inventory in each state. Do not reconstruct subtypes from a
base-label prediction.

## 4. Deterministic VTB projection

### 4.1. Punctuation and syllables

Apply the following order to the basic source tree:

1. Validate the source tree and retain its metadata and original head chains.
2. Determine the gluing direction of each token with base label `punct` using
   the rules below. Select the nearest source non-`punct` token or source root
   in that direction as its target. Always retain the source root, including
   a punctuation root. Retain punctuation with no target on its chosen side.
   Concatenate each target and its assigned punctuation fragments in source
   order, without inserting spaces. Never choose a deleted node as a target.
3. Remove the incoming arc of each deleted punctuation node. For any retained
   dependent whose head is deleted, follow the **original** head chain through
   deleted nodes to the first retained ancestor and preserve its relation.
4. Split each retained word FORM using `FORM.split()`, preserving case,
   diacritics and order. Its first syllable is the anchor. Attach every later
   syllable directly to that anchor with `dep`; do not form a chain.
5. Route external incoming and outgoing arcs through word anchors, map labels
   to base labels, and assign consecutive internal IDs and updated heads.
6. Prepare model input with UPOS `X`. Validate the projected tree, root/label
   equivalence, heads, cycles and projectivity.

| Punctuation | Gluing direction |
|---|---|
| Opening brackets and typographic opening quotation marks | Forward, onto the following target |
| Closing brackets, typographic closing quotation marks and other punctuation | Backward, onto the preceding target |
| Standalone straight double quote (`"`) | Alternate opening/forward and closing/backward in source order; reset to opening for each sentence |

Identify opening marks using Unicode general categories `Ps` and `Pi`, and
closing marks using `Pe` and `Pf`, as defined in the
[Unicode Character Database](https://www.unicode.org/reports/tr44/#General_Category_Values).
For a punctuation FORM containing several characters, treat it as opening only
when every character belongs to `Ps` or `Pi`; otherwise use the backward rule.
The standalone straight-double-quote rule takes precedence. Quote alternation
is positional and does not attempt to repair unbalanced or nested quotations.

A leading opening mark can glue forward. A leading backward mark without a
preceding target remains a token; an opening mark without a following target
also remains a token. Root preservation takes precedence over all gluing rules.
Assign all targets before changing FORMs or deleting nodes so consecutive and
nested marks preserve their original order.

`project_sentence(source)` returns projected `metadata` and `tokens`, plus
`word_to_syllables` and `syllable_to_word` mappings using one-based IDs. Each
source word ID maps to the tuple of its projected syllable IDs; a deleted
punctuation ID maps to an empty tuple. Each projected syllable maps back to its
retained source word ID. Preserve the source sentence ID and do not mutate the
source tree. The result includes `is_projective`, computed from crossing arcs
including the artificial ROOT arc. Return valid non-projective trees for
measurement and later split-specific filtering.

The anchor choice is a reproducible representation, not a claim that the first
syllable is always a linguistic head. Do not use `goeswith`: Vietnamese syllable
spacing is normal orthography, not incorrectly separated text.

Use `projection_version="v2-first-dep-directional-glue"` for this convention.
Gluing punctuation is a project choice to approximate stub input, not a general
UD rule. Compare glued and separate punctuation on dev in Weeks 3–4, including
opening punctuation, and report the scoring/tokenization differences.
The measured effects of this projection are:

| Split | Internal dep arcs added | Punctuation glued backward | Punctuation glued forward | Punctuation retained |
|---|---:|---:|---:|---:|
| Train | 4,758 | 2,644 | 230 | 57 |
| Dev | 5,765 | 3,279 | 216 | 22 |
| Test | 2,165 | 1,533 | 133 | 37 |

Internal arcs exclude source `dep` relations. Gluing counts include alternating
straight quotes; retained punctuation includes roots and marks without a target
on their chosen side. Exact source punctuation FORMs on train include 408
straight double quotes and 27 opening parentheses, reproducing the task's
inventory. All projected trees pass the frozen schema and single-rooted-tree
checks. See [PROJECTION_COUNTS.md](analysis/PROJECTION_COUNTS.md) for reproduction.
Never replace training gold with fallback trees.

### 4.2. Runtime tokenization

At runtime, use the supplied `Token.syllables` to build the internal sequence.
Do not infer new word boundaries, split `form` on `_`, normalize teencode, or
glue separately supplied punctuation. Keep the input FORM unchanged. Group
metadata is used for input/output mapping, not as a model feature.

With stub input, each original token normally forms a one-syllable group.
Word-level Project 1 input may form a group with several internal syllables.
The decoder still uses the same syllable representation; Section 11 specifies
how to return the original token sequence.

## 5. Arc-standard state and legal actions

Let `tokens` be the immutable tuple of internal syllable strings and let
`n = len(tokens)`. Token IDs are `1…n`; ID 0 is the artificial ROOT.

| Field | Representation and initialization |
|---|---|
| `stack` | List of IDs, top at the right; initially `[0]` |
| `buffer_pos` | Next unread token ID; initially 1; exhausted at `n + 1` |
| `heads` | Length `n + 1`, initially all `None` |
| `labels` | Length `n + 1`, initially all `None` |

Index 0 of heads/labels is unused and stays `None`. `None` means unassigned;
`heads[i] = 0` means the root has been assigned. The two arrays represent arcs;
do not maintain a second, potentially inconsistent arc list.

`Action(kind, label=None)` stores an action kind and its optional base label;
`SHIFT` has no label. `ParserState(tokens)` initializes the fields above and
rejects empty input. `state.legal_actions()` returns a tuple of legal actions
without mutation. `state.apply(action)` updates the state or raises `ValueError`
without partial changes. `state.is_terminal` reports whether the buffer is
exhausted and the stack is `[0]`; validate the completed heads and labels before
accepting a decoded tree.

For stack suffix `[..., i, j]`, with `j` on top:

| Action | Effect | Additional legality conditions |
|---|---|---|
| `SHIFT` | Push buffer_pos and increment it | Buffer is not exhausted |
| `LEFT_ARC(r)` | Set heads[i]=j and labels[i]=r; remove i | i is not ROOT; i has no head; r is valid and not root |
| `RIGHT_ARC(r)` with i>0 | Set heads[j]=i and labels[j]=r; remove j | j is a real token without a head; r is valid and not root |
| `RIGHT_ARC(root)` with i=0 | Assign j to ROOT and remove j | Buffer exhausted; stack exactly [0,j]; j is unassigned |

ARC requires two valid stack IDs, a real dependent distinct from its head, and
an unassigned dependent. Never overwrite a head. Before adding `h → d`, walk
the current head chain from h; reject if it reaches d or an invalid reference.
Stop at ROOT or an unassigned head. Reject invalid actions without partial
state mutation. ROOT is never a dependent. `root` is used if and only if HEAD=0.

Only score legal actions. Whether a dependent has received all its **gold**
children is not a runtime legality condition; the model must learn when to
reduce. Stack size can reach n+1: using its top two tokens for ARC does not
make dependency trees binary.

Terminate only when buffer_pos=n+1 and stack=[0], then validate every head and
label. Each successful nonempty decoding has n SHIFTs and n ARCs, including
the final ROOT arc. Every action consumes input or removes a stack item.
The final-only ROOT rule permits exactly one root; single assignment and the
guard prevent multiple heads, self-loops and cycles.

## 6. Static training oracle

`StaticOracle(gold: ProjectedSentence)` stores the projected gold heads, labels
and direct children. Reject empty or non-projective gold input with `ValueError`
naming the sentence ID. `oracle.is_ready(state, dependent_id)` checks the gold
children below. `oracle.next_action(state)` returns an `Action` without mutating
the state; the caller applies it through `state.apply(action)`. Reject terminal
states and states whose token forms differ from gold, naming the sentence ID.

Gold heads and labels come from the projected VTB tree. Derive direct
`gold_children` from gold heads. A dependent d is ready only when, for every
gold child c, the current state has `heads[c]=d` and
`labels[c]=gold_labels[c]`. A gold leaf is ready immediately.

At a nonterminal state with stack suffix `[..., i, j]`, apply this order:

1. If gold_heads[i]=j, i is ready and LEFT_ARC is legal, return
   LEFT_ARC(gold_labels[i]).
2. Otherwise, if gold_heads[j]=i, j is ready and RIGHT_ARC is legal, return
   RIGHT_ARC(gold_labels[j]).
3. Otherwise SHIFT if input remains.
4. Otherwise raise an oracle/data error with the sentence ID and state.

The ROOT arc also requires the final-only ROOT conditions. Do not access
gold_heads[0] as a real dependent's head. Replay oracle actions and require
exact reconstruction of all gold heads/labels, legal transitions and 2n actions.

Training follows the oracle action even when the classifier predicts wrongly.
This static oracle is defined on gold-reachable states, not arbitrary erroneous
states. Dynamic-oracle training is outside the initial design. An unexpected
failure on a valid projective gold tree must be investigated, not replaced
with a fallback or silently excluded.

## 7. The 54 input features

A training record is one parser state before an action. Its target is a separate
oracle action. The same 54 feature slots are extracted during training and
prediction; their values change with the state. S0/S1/S2 are the top three
stack positions; B0/B1 are the next two buffer positions.

| Group | Slots | Count |
|---|---|---:|
| Bias | Constant 1 | 1 |
| Token forms | Lowercased S0, S1, S2, B0, B1 | 5 |
| Form combinations | Pairs (S1,S0), (S0,B0), (S1,B0); triple (S1,S0,B0) | 4 |
| Shape flags | Contains uppercase, is all digits, contains punctuation at S0/S1/B0 | 9 |
| Affixes | Prefix and suffix lengths 1,2,3 at S0/S1/B0 | 18 |
| State and distance | S1–S0 distance, stack size, buffer size, ROOT flags at S0/S1 | 5 |
| Built children | Left/right child counts at S0/S1 | 4 |
| Outermost children | Form and relation of leftmost/rightmost child at S0/S1 | 8 |
| **Total** | **Five groups of state features plus one bias** | **54** |

Extraction rules:

- Lowercase with `form.lower()` without removing diacritics or changing output.
  Combinations are ordered tuples, not ambiguous concatenated strings.
- Shape flags use `any(c.isupper() for c in form)`, `form.isdigit()` and Unicode categories
  beginning with P. Flags are categorical True/False values.
- Affixes use lowercased Python Unicode strings, not bytes. Omit an affix slot
  if the token is shorter than its requested length; do not pad.
- Shape/affix slots do not apply to ROOT or missing positions and create no
  encoded key there. Form/combination slots retain typed sentinel values.
- For real S1 and S0, bucket absolute ID distance as 1, 2, 3–5, 6–10, 11+.
  Use MISSING when a position is absent and ROOT when both exist but involve
  artificial ROOT. Do not treat ROOT as a real sentence position.
- Bucket stack size, including ROOT, as 1,2,3,4+ and remaining buffer size as
  0,1,2,3+. ROOT flags are True/False, or MISSING for an absent position.
- Count only direct children already attached in the current state. Bucket
  each side as 0,1,2,3+. Choose smallest-ID left child and largest-ID right
  child; read its lowercased form and already assigned relation separately.
  A side with no child uses NO_CHILD for form/relation and zero for its count.
- For a ROOT or missing parent position, all six child-related slots use the
  corresponding typed ROOT/MISSING sentinel.

Encode categorical values as sparse indicator keys containing slot identity,
position, value type and value. FORM, ROOT, MISSING and NO_CHILD types must not
collide with literal token strings. There are at most 54 active keys per state,
but the train-derived encoded vocabulary and number of weights can be larger.
Freeze that vocabulary at export. Unknown prediction keys contribute zero.

Do not use gold UPOS, input UPOS, gold heads/labels/children, oracle results,
source word boundaries, group mappings, sentence IDs or split/source metadata
as features. Already built child labels are permitted; hidden gold labels are
not. No embedding, POS dictionary or handwritten word list is used initially.

## 8. Perceptron training and averaging

For legal action a and state s, sum the action's weights for active feature keys:

```text
score(a,s) = sum(W[a,f] for active keys f)
```

Initialize all weights to zero. Ties prefer SHIFT, then LEFT_ARC, then
RIGHT_ARC; sort labels lexicographically within each ARC type. Use this same
order when creating the action inventory and scoring candidates.

For each gold-reachable state, obtain oracle target y, extract x(s), predict
the best legal action y_hat with current weights, and update only if y_hat≠y:

```text
W[y]     += x(s)
W[y_hat] -= x(s)
```

Learning rate is 1. An ARC with the correct direction but wrong label is still
an incorrect class. Apply y to advance training, then continue the sentence.
Inference instead applies the model action without oracle access or updates.

Let w_t be the weights **after** training record t. Average all records,
including correct predictions and states with only one legal action:

```text
w_bar(T) = (w_1 + ... + w_T) / T
```

Do not restart averaging at epoch boundaries. Efficiently store each parameter's
current value v, accumulated sum and last-change step. If T records have been
completed, before changing parameter p by delta:

```text
sum[p]  += (T - last[p]) * v[p]
last[p]  = T
v[p]    += delta
```

Increment T after every record. Obtain a read-only averaging snapshot with:

```text
w_bar[p] = (sum[p] + (T - last[p]) * v[p]) / T
```

Keep Python integers for values/sums/timestamps until averaging. Do not delete
history when a current weight becomes zero. Reject an empty training set
rather than divide by zero. Dev scoring does not alter weights, sums or T.

Train for at most 20 epochs. Initialize one `random.Random(42)` generator.
Each epoch shuffles a fresh copy of the original retained-sentence order with
that continuing generator; do not reset its seed. Preserve action order within
sentences. Reset parser state per sentence, not model or averaging history.

After each epoch evaluate the averaged snapshot on dev. Select greatest LAS,
then UAS, then earliest epoch, comparing exact correct-token counts on the
same denominator rather than rounded percentages. Stop after three consecutive
non-improving epochs or epoch 20. Save an independent best-snapshot copy; the
best epoch need not be the final epoch. Do not retrain on train+dev initially.
Record code/runtime/data versions, seed, configuration and run statistics.

## 9. Evaluation protocol

Decode without gold input or oracle. Use the same projection, label mapping,
decoder, group conversion, overrides and fallback as the released pipeline.

```text
UAS = tokens with correct head / scored tokens
LAS = tokens with correct head and relation / scored tokens
```

Micro-average over real tokens, including projected within-word dep arcs and
retained punctuation; exclude artificial ROOT. A syllable with glued punctuation
is scored normally. These are syllable/projection scores, not directly
comparable to published word-level VTB scores with different tokenization.
Include fallback outputs and report their count; do not drop difficult cases.

The [hand-annotated set](data/hand_annotated.conllu) is a separate out-of-domain
evaluation set, not training data. It currently contains 20 sentences, 254
tokens and 10 construction tags, with 10 formal, 5 informal and 5 teencode
sentences. All are marked synthetic=false. Exclude uncertain sentences
hc-010, hc-011, hc-016, hc-017 and hc-019 from scoring until their conventions
are resolved. This leaves 15 sentences and 207 tokens covering eight tags;
svc_di and emoticon currently occur only in uncertain sentences.

Report real/synthetic/uncertain counts, head and label errors by construction,
and all scoring denominators. No UAS/LAS or independent annotator agreement
has been measured yet. If this set informs an override, record that use and do
not describe the resulting evaluation as entirely independent.

## 10. Weight storage, pruning and loading

Store the model under `src/vietnlp/linguistics/ud_model/`:

| File | Contents |
|---|---|
| model.json | Format/version identifiers, ordered action list, encoded feature keys and nonzero averaged weights |
| metadata.json | Model SHA-256, VTB commit/hashes, configuration, runtime/code versions and dev results |
| ATTRIBUTION.md | VTB name, commit, CC BY-SA 4.0 and the fact that weights derive from VTB |

Use format_version=1, feature_version="v1-54",
projection_version="v2-first-dep-directional-glue" and transition_version="arc-standard-v1".
Store keys as typed JSON arrays and weights as `[feature_id,action_id,value]`
triples. Assign feature IDs by canonical compact JSON key order; sort triples
by both IDs. Reject duplicate keys/triples and nonfinite values. Keep Python's
round-trip float representation without manual rounding. Preserve extraction
order when summing scores, independently of serialized feature IDs.

Limit model.json plus metadata.json to **10,000,000 bytes**. First remove zero
averaged weights and features with no remaining weights. If necessary, prune
features occurring in fewer than k oracle records during **one** training pass,
always keeping bias. Try k=2,3,5,10,20,50,100,200,500,…, continuing with
1/2/5×10^j levels. Choose the first threshold meeting the size budget, reindex,
export compact UTF-8 JSON and load it again. If even bias-only storage exceeds
the budget, raise an export error. Report sizes, retained features/weights,
threshold, dev UAS/LAS before/after pruning and fallback counts. Do not select
the threshold using test data or publish pre-pruning scores as release scores.

Resolve files relative to the parser module. Load on the first valid parse
request, then share a read-only process-local cache. Do not load/train at
import time or train inside parse. Validate size, JSON/schema versions,
pipeline compatibility, SHA-256, action labels, IDs, uniqueness and finite
weights. Missing/corrupt/incompatible model files raise RuntimeError with a
reason code, not a fallback for every sentence. Never use pickle.

Target cold loading within one second, measured with perf_counter in the
project environment once actual weights exist. Verify that 151 calls in one
process load only once. This is a target, not a measured result.

## 11. Runtime pipeline and tree guarantee

### 11.1. Supported emoticon override

After validating input and loading the model, recognize only tokens whose
entire form equals `:))`. VTB has zero exact occurrences and the task requires
this override. Do not match substrings or broaden the set silently.

If ordinary tokens exist, remove supported emoticons from the decoder input,
remember original positions, then reinsert them as `discourse` dependents of
the sentence root. Do not let them head ordinary tokens. If all tokens are
supported emoticons, choose the first as root and attach later ones with
discourse. A sole emoticon must be root to preserve the single-root invariant.

Attaching to the sentence root is a limited approximation for multiclause
sentences. Other emoticons/emoji remain ordinary model input initially;
`=.=` in the evaluation set does not imply an implemented override. No
teencode normalization or closed lexical list is part of this design.

### 11.2. Decode and return original tokens

Concatenate supplied syllable tuples for non-removed tokens, assigning IDs
1…n and a `group_of` mapping to original token positions. Run legal-action
decoding with averaged weights and fixed tie order. Exceeding 2n actions or
having no legal action before completion is a decoder failure. Validate the
syllable tree before grouping.

For each original token group G, choose rep(G) by minimum depth from the real
sentence root, breaking ties by smallest internal ID. If rep(G) is the root,
give G head 0/root. Otherwise map rep(G)'s head to its original group and keep
rep(G)'s incoming relation. Omit internal arcs and incoming arcs to unselected
representatives. Reinsert emoticons and express every head against the **full
original** token sequence, not the sequence with emoticons removed.

For a non-root group, its representative's parent cannot be in the same group:
that would contradict minimum depth. The minimum depth of its parent group is
strictly smaller, preventing group-level cycles. Only the root-containing
group gets head 0. When decoding exactly matches first-syllable projection,
this returns the source word tree. For imperfect predictions, grouping can
discard arcs; structural validity does not imply optimal LAS.

Build output from original tokens, retaining forms and valid UPOS (None→X).
Check IDs, token identity/order, head range, no self-reference, root-label
equivalence, labels and connected acyclic single-root structure. Call both
validate_dependency_parse and is_single_rooted_tree; neither alone covers all
token-preservation constraints. Repeat validation after any override.

### 11.3. Fallback and errors

Use fallback only for sentence-level tree-construction failures: decoder
failure, invalid syllable tree, group-conversion failure or invalid final tree.
Do not hide invalid input, model configuration errors or unexpected programming
exceptions behind a blanket `except Exception`.

Choose a fallback root on the original sequence in this order:

1. First token that is neither a supported emoticon nor entirely Unicode P-category punctuation.
2. Otherwise first token that is not a supported emoticon.
3. Otherwise the first token.

Set it to head 0/root. Attach all others directly to it: supported emoticons
use discourse, punctuation-only tokens use punct, and remaining tokens use dep.
A word with glued punctuation is not punctuation-only. Validate the star tree;
if fallback itself fails, raise an internal error instead of returning an
invalid parse. Log sent_id, failing stage and reason code in evaluation tools
without extending the frozen interface. Fallback guarantees structure only.

## 12. Six constructions and evaluation coverage

The conventions below preserve VTB attachments through projection and base-label
mapping. Labels are learned from context rather than assigned from form alone.

| Construction | Evidence and decision | Current evaluation sentences |
|---|---|---|
| Classifiers | VTB has 250 clf and 887 clf:det. Preserve their different source heads while mapping both to clf. For con, clf/clf:det total 53 versus 67 nsubj/obj uses | hc-015: numeral+classifier+noun and ordinary noun con; hc-002/hc-005: bare classifier; hc-004: ordinary noun chuyến |
| Coordination | First conjunct heads later conj nodes; cc attaches to its associated conjunct. Hay is cc in 43/51 occurrences, including 14/16 in train; do not force evaluative hay to cc | hc-002/hc-004/hc-015/hc-020 cover và; hay_or/hay_good remain to be added |
| Serial/directional verbs | Preserve first-verb heads and source compound/xcomp distinctions. Adjacent đi+VERB includes 55 xcomp, 47 compound:svc and 10 compound:dir, plus 1 compound:vmod and 2 obj | hc-019 covers svc_di but is uncertain; dir remains uncovered |
| Possessives | Map nmod:poss to nmod, keeping của as case of the possessor. Of 587 nmod:poss arcs, 533 have a direct của case marker. Do not insert a marker in bare possessives | hc-020 covers của; hc-015/hc-016 cover bare possession, with hc-016 uncertain |
| Topic/comment | Distinguish nsubj, obj and dislocated by role, not sentence-initial position. VTB has 37 dislocated arcs and 15 preverbal obj arcs; the latter is not a topic count | topic remains uncovered; the fixture's provisional Bộ_phim→obj analysis is a reference, not confirmed gold |
| Particles/emoticons | Discourse counts: à 10/10, nhé 5/5, đấy 10/17. Nha is absent. Đó has 171 det:pmod and 5 discourse uses. Learn contextual roles; only :)) gets an initial override | particle: hc-008/009/017/018; do_dem: hc-006; emoticon: hc-016/017, both uncertain; degenerate remains uncovered |

The restricted directional-VERB query yields 155 compound:dir, 86 xcomp and
64 compound:svc arcs. Across all forms, the head precedes its dependent in
277/277 compound:dir cases and 509/511 compound:svc cases, with the two exceptions recorded in
the JSON inventory. Do not generalize the predominant pattern into a claim
that VTB has no exceptions.

Prioritize adversarial errors involving evaluative hay and classifier forms
used as ordinary nouns. Monitor nha and demonstrative/particle đó separately.
Add no post-processing or lexical override until missing evidence or measured
dev/evaluation errors justify a documented rule.

The set currently meets Week 2's 20-sentence/10-tag count. By the end of Week 4,
expand to at least 30 sentences and every per-tag minimum, with at least three
distinct final particles and synthetic sentences below 20%. Counts and open
attachments are in [WEEK2_REPORT.md](WEEK2_REPORT.md).

## 13. Verification and references

[TESTING.md](TESTING.md) specifies implementation tests for transitions, guards,
single root, oracle replay, projection, features, averaging, loader, grouping,
fallback, adversarial constructions and the full fixture. The existing
[annotation contract test](../../tests/test_linguistics_ud_parser_hand_annotated.py)
checks format, metadata, token alignment, label/tree validity and coverage.
The Week 3 full-suite result is 464 passed, 14 skipped, 1 warning; 275 passing
cases cover Project 2. Projection measurements and oracle replay are recorded
in [PROJECTION_COUNTS.md](analysis/PROJECTION_COUNTS.md). Model scores and
loading benchmarks remain unmeasured.

Primary references:

- [Week 2 task](week2_tasks.md), [input interface](../../src/vietnlp/interfaces/linguistics.py), [output interface](../../src/vietnlp/interfaces/ud.py) and [label inventory](../../src/vietnlp/interfaces/_common.py).
- [Nivre 2008](https://aclanthology.org/J08-4003/), transition-based dependency parsing.
- [UD CoNLL-U](https://universaldependencies.org/format.html), [conj](https://universaldependencies.org/u/dep/conj.html), [cc](https://universaldependencies.org/u/dep/cc.html), [case](https://universaldependencies.org/u/dep/case.html), [xcomp](https://universaldependencies.org/u/dep/xcomp.html), [dislocated](https://universaldependencies.org/u/dep/dislocated.html) and [discourse](https://universaldependencies.org/u/dep/discourse.html).
- VTB convention pages for [clf](https://universaldependencies.org/treebanks/vi_vtb/vi_vtb-dep-clf.html), [clf:det](https://universaldependencies.org/treebanks/vi_vtb/vi_vtb-dep-clf-det.html), [compound:svc](https://universaldependencies.org/treebanks/vi_vtb/vi_vtb-dep-compound-svc.html) and [nmod:poss](https://universaldependencies.org/treebanks/vi_vtb/vi_vtb-dep-nmod-poss.html). Counts in this design come from the pinned local corpus, not the live documentation pages.

## 14. Complete VTB label mapping

The table below is generated from the pinned corpus before projection. Counts
exclude the additional within-word dep arcs introduced by projection.

| VTB label | Output label | Train | Dev | Test | Total |
|---|---|---:|---:|---:|---:|
| `acl` | `acl` | 94 | 67 | 85 | 246 |
| `acl:relcl` | `acl` | 1 | 20 | 2 | 23 |
| `acl:subj` | `acl` | 344 | 853 | 142 | 1339 |
| `acl:tmod` | `acl` | 63 | 122 | 51 | 236 |
| `acl:tonp` | `acl` | 31 | 51 | 15 | 97 |
| `advcl` | `advcl` | 282 | 373 | 211 | 866 |
| `advcl:objective` | `advcl` | 130 | 112 | 64 | 306 |
| `advmod` | `advmod` | 1094 | 1342 | 752 | 3188 |
| `advmod:adj` | `advmod` | 127 | 306 | 153 | 586 |
| `advmod:dir` | `advmod` | 8 | 1 | 9 | 18 |
| `advmod:neg` | `advmod` | 243 | 266 | 182 | 691 |
| `amod` | `amod` | 457 | 434 | 235 | 1126 |
| `appos` | `appos` | 59 | 104 | 27 | 190 |
| `appos:nmod` | `appos` | 36 | 111 | 26 | 173 |
| `aux` | `aux` | 136 | 191 | 86 | 413 |
| `aux:pass` | `aux` | 139 | 182 | 45 | 366 |
| `case` | `case` | 1121 | 1460 | 565 | 3146 |
| `cc` | `cc` | 407 | 407 | 224 | 1038 |
| `ccomp` | `ccomp` | 201 | 250 | 107 | 558 |
| `clf` | `clf` | 85 | 118 | 47 | 250 |
| `clf:det` | `clf` | 348 | 336 | 203 | 887 |
| `compound` | `compound` | 520 | 1288 | 154 | 1962 |
| `compound:adj` | `compound` | 2 | 20 | 1 | 23 |
| `compound:amod` | `compound` | 7 | 74 | 17 | 98 |
| `compound:apr` | `compound` | 1 | 0 | 1 | 2 |
| `compound:atov` | `compound` | 14 | 10 | 4 | 28 |
| `compound:dir` | `compound` | 98 | 144 | 35 | 277 |
| `compound:pron` | `compound` | 5 | 23 | 18 | 46 |
| `compound:prt` | `compound` | 32 | 22 | 35 | 89 |
| `compound:redup` | `compound` | 3 | 0 | 1 | 4 |
| `compound:svc` | `compound` | 129 | 292 | 90 | 511 |
| `compound:verbnoun` | `compound` | 7 | 31 | 26 | 64 |
| `compound:vmod` | `compound` | 274 | 298 | 149 | 721 |
| `compound:z` | `compound` | 11 | 5 | 1 | 17 |
| `conj` | `conj` | 745 | 1259 | 468 | 2472 |
| `cop` | `cop` | 194 | 185 | 102 | 481 |
| `csubj` | `csubj` | 42 | 48 | 20 | 110 |
| `csubj:asubj` | `csubj` | 7 | 7 | 6 | 20 |
| `csubj:pass` | `csubj` | 9 | 1 | 0 | 10 |
| `csubj:vsubj` | `csubj` | 18 | 25 | 13 | 56 |
| `dep` | `dep` | 3 | 1 | 3 | 7 |
| `det` | `det` | 320 | 543 | 189 | 1052 |
| `det:pmod` | `det` | 316 | 254 | 189 | 759 |
| `discourse` | `discourse` | 145 | 150 | 134 | 429 |
| `dislocated` | `dislocated` | 10 | 18 | 9 | 37 |
| `expl` | `expl` | 0 | 4 | 0 | 4 |
| `fixed` | `fixed` | 6 | 18 | 8 | 32 |
| `flat` | `flat` | 3 | 3 | 10 | 16 |
| `flat:date` | `flat` | 48 | 65 | 9 | 122 |
| `flat:foreign` | `flat` | 0 | 7 | 0 | 7 |
| `flat:name` | `flat` | 6 | 0 | 2 | 8 |
| `flat:number` | `flat` | 23 | 100 | 9 | 132 |
| `flat:redup` | `flat` | 3 | 0 | 0 | 3 |
| `flat:time` | `flat` | 13 | 6 | 2 | 21 |
| `iobj` | `iobj` | 17 | 6 | 11 | 34 |
| `list` | `list` | 21 | 24 | 0 | 45 |
| `mark` | `mark` | 299 | 512 | 294 | 1105 |
| `mark:pcomp` | `mark` | 76 | 106 | 39 | 221 |
| `nmod` | `nmod` | 740 | 1304 | 461 | 2505 |
| `nmod:poss` | `nmod` | 233 | 253 | 101 | 587 |
| `nsubj` | `nsubj` | 1577 | 1519 | 958 | 4054 |
| `nsubj:nn` | `nsubj` | 4 | 104 | 14 | 122 |
| `nsubj:pass` | `nsubj` | 93 | 103 | 32 | 228 |
| `nsubj:xsubj` | `nsubj` | 5 | 0 | 5 | 10 |
| `nummod` | `nummod` | 533 | 636 | 238 | 1407 |
| `nummod:det` | `nummod` | 0 | 71 | 0 | 71 |
| `obj` | `obj` | 1660 | 1835 | 867 | 4362 |
| `obl` | `obl` | 501 | 460 | 259 | 1220 |
| `obl:about` | `obl` | 33 | 27 | 15 | 75 |
| `obl:adj` | `obl` | 8 | 111 | 17 | 136 |
| `obl:adv` | `obl` | 0 | 3 | 1 | 4 |
| `obl:agent` | `obl` | 21 | 52 | 3 | 76 |
| `obl:comp` | `obl` | 146 | 555 | 163 | 864 |
| `obl:iobj` | `obl` | 48 | 52 | 27 | 127 |
| `obl:tmod` | `obl` | 379 | 552 | 207 | 1138 |
| `obl:with` | `obl` | 69 | 72 | 49 | 190 |
| `parataxis` | `parataxis` | 220 | 182 | 128 | 530 |
| `punct` | `punct` | 2931 | 3517 | 1703 | 8151 |
| `root` | `root` | 1400 | 1123 | 800 | 3323 |
| `vocative` | `vocative` | 6 | 6 | 2 | 14 |
| `xcomp` | `xcomp` | 710 | 917 | 329 | 1956 |
| `xcomp:adj` | `xcomp` | 64 | 36 | 31 | 131 |
| `xcomp:dir` | `xcomp` | 0 | 17 | 0 | 17 |
| `xcomp:vcomp` | `xcomp` | 1 | 0 | 2 | 3 |
