# PROVISIONAL -- pending professor sign-off

`oupm_coref_probe.jsonl` and `oupm_coref_probe_gold_clusters.jsonl` are an
**AI-drafted first pass**, not yet reviewed or signed off by the professor
(the user). Per CLAUDE.md rule 2 ("DeepSeek output never enters Gold
unvalidated -- the model proposes; rules, type checks, or humans dispose")
applied to fixture authorship: Project 7 branches may build against this
file, but it is not frozen ground truth until the sign-off below is
checked off. A defect found before sign-off is fixed by regenerating via
`tests/fixtures/generate_oupm_coref_probe.py`; after sign-off, changes go
through the same interface-change-control process as `interfaces/**`.

## What's in it

12 synthetic documents (33 mentions, 21 gold clusters), each built around
one specific entity-resolution trap:

| Doc | Trap |
|---|---|
| `probe-01-surname-collision` | Two different people share the surname `Nguyễn`; bare surname alone must not merge them |
| `probe-02-diacritic-variant` | Same name, two tone-mark placements (`Hòa` vs `Hoà`) -- CLAUDE.md's own worked example |
| `probe-03-honorific-stripping` | Honorific + given name (`Anh Bình`) refers back to a full name (`Trần Văn Bình`) |
| `probe-04-nickname` | A nickname (`Hương Nhỏ`) that shares only one syllable with the full name (`Lê Thị Hương`) |
| `probe-05-same-name-different-people` | Two DIFFERENT people share an identical full name; only co-occurring location context disambiguates them -- must NOT merge |
| `probe-06-org-acronym-variant` | An organization's acronym (`FPT`) vs. its full name (`Tập đoàn FPT`) |
| `probe-07-honorific-plus-surname-collision` | Honorific stripping combined with a surname-collision distractor in the same document |
| `probe-08-multi-person-same-surname-stress` | Three people share one surname in a single document; only one of them recurs |
| `probe-09-middle-name-dropped` | A middle name (`Thị`) is dropped on second reference |
| `probe-10-same-given-name-different-surname` | Two different people share a given name (`Sơn`) but not a surname -- must NOT merge |
| `probe-11-mixed-per-loc-labels` | A PER and a LOC mention co-occur; label must gate clustering (never merge across labels) |
| `probe-12-easy-baseline-exact-repeats` | Exact string repeats of one name, three times -- a control case even the naive stub gets right |

## Sign-off checklist

- [ ] Every "must merge" cluster is linguistically correct given the sentence context.
- [ ] Every "must NOT merge" case is a genuine, defensible non-merge, not an artifact of thin fixture data.
- [ ] No trap is redundant with another to the point of not adding coverage.
- [ ] Vietnamese naming conventions (honorifics, kinship terms, common surname distribution) are represented accurately.

Once checked off, remove this file's "PROVISIONAL" status by deleting this
checklist section and updating `student-projects/README.md`'s fixture
table to mark this artifact frozen.
