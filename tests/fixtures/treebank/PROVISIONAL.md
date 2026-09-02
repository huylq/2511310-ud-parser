# PROVISIONAL -- pending professor sign-off

`gold_treebank_seed.conllu` and `system_b_perturbed.conllu` are an
**AI-drafted first pass**, not yet reviewed or signed off by the professor
(the user). Per CLAUDE.md rule 2 ("DeepSeek output never enters Gold
unvalidated -- the model proposes; rules, type checks, or humans dispose")
applied to fixture authorship: Project 4 branches may build against this
file, but it is not frozen ground truth until the sign-off checklist below
is checked off. A defect found before sign-off is fixed by regenerating
via `tests/fixtures/generate_gold_treebank_seed.py`; after sign-off,
changes go through the same interface-change-control process as
`interfaces/**`.

## What's in it

20 sentences (10 formal + 10 informal), copied verbatim from the
single-sentence pool in `tests/fixtures/generate_fixture_corpus.py`
(`FORMAL`/`INFORMAL` lists) -- within the plan's "~20-30 sentences" target.
Multi-syllable words use underscore-joined FORMs (`Giáo_dục`), the
standard VLSP/VTB/PhoNLP convention, rather than a literal space inside
one CoNLL-U FORM field.

Construction types covered:

| Construction | Example sentence(s) |
|---|---|
| Simple SVO | `gold-f02`, `gold-f06`, `gold-i02` |
| NP-internal coordination (`cc`+`conj`) inside an org name | `gold-f01` |
| Classifier phrase (`clf`) | `gold-i08` ("Con mèo" -- classifier `con`) |
| Bare (juxtaposition) possessive, no `của` -- see gap below | `gold-i08` ("nhà tao") |
| Relative/participial clause (`acl`) | `gold-f04`, `gold-f06`, `gold-f08`, `gold-f10`, `gold-i07`, `gold-i09` |
| Sentence-final discourse particles | `gold-i01`, `gold-i03`, `gold-i05`, `gold-i06`, `gold-i07`, `gold-i08`, `gold-i09`, `gold-i10` |
| Negative imperative (`đừng`) | `gold-i03` |
| Intensifiers / colloquial idioms (`quá`, `ghê`, `dã man`, `quá trời`) | `gold-i02`, `gold-i06`, `gold-i07`, `gold-i08` |
| Loosely-joined clauses (`parataxis`, comma-separated) | `gold-i01` through `gold-i10` (all informal sentences) |
| Topicalized/fronted object | `gold-i04` |
| Vocative | `gold-i07` |
| Flat multiword proper names | `gold-f01`, `gold-f02`, `gold-f05`, `gold-f07`, `gold-f10` |

**Known gap:** no sentence in the source fixture corpus contains an
explicit `của`-possessive construction (confirmed by inspection of
`fixture_corpus.jsonl`), so that specific trap from the plan's I/O
contract table is not directly exercised here. `gold-i08`'s bare
juxtaposition possessive (`mèo nhà tao`, "[my] house's cat") is the
closest available analog, tagged `nmod`. Flagged for the professor to
decide during sign-off whether to add a synthetic sentence for `của`
coverage.

## Deliberately-perturbed sentences (system B)

10 of the 20 sentences carry exactly one plausible, realistic disagreement
each; the other 10 are identical to gold (real systems agree on the easy
majority):

| Sentence | What differs |
|---|---|
| `gold-f01` | Coordination scope: `Đào_tạo` attaches under `Bộ` instead of under `Giáo_dục` |
| `gold-f03` | Compound attachment: `quốc_gia` attaches to `bóng_đá` instead of `Đội_tuyển` ("national football" vs. "national team") |
| `gold-f05` | PP-attachment: the location phrase attaches inside the object NP (`khí_hậu`) instead of to the main verb |
| `gold-f07` | Deprel: `Việt` tagged `amod` instead of `flat` for the proper-name-as-modifier "tiếng Việt" |
| `gold-f09` | Nominal-modifier scope: `đợt` (round) attaches to `tuyển_sinh` instead of `kết_quả` |
| `gold-i02` | UPOS: slang intensifier `dã_man` tagged `ADJ` instead of `ADV` |
| `gold-i04` | Deprel: fronted `Bộ_phim` tagged `nsubj` instead of `obj` |
| `gold-i06` | Modal-adverb scope: `chắc` attaches across the parataxis boundary to the first clause instead of the second |
| `gold-i08` | Classifier vs. determiner: `Con` tagged `det` instead of `clf` |
| `gold-i10` | Temporal scope: `Chiều_nay` attaches to the second clause (`thiếu`) instead of the first (`đá_bóng`) |

## Sign-off checklist

- [ ] Every gold annotation is linguistically defensible against UD v2 / UD_Vietnamese-VTB conventions.
- [ ] Every perturbation is a genuinely plausible annotator/parser disagreement, not contrived noise.
- [ ] The `của`-possessive gap above is either accepted as a known limitation or filled with an added sentence.
- [ ] Sentence-final particle and parataxis-boundary analyses match how `.claude/agents/vietnamese-linguist.md` would annotate them.

Once checked off, remove this file's "PROVISIONAL" status and update
`student-projects/README.md`'s fixture table to mark this artifact frozen.
