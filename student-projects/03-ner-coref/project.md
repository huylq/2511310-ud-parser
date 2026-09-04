# Project 3: NER & Coreference Resolution

## Target

Build named-entity recognition and (within-document) coreference resolution.

```
extract_entities(sentence: interfaces.linguistics.SegmentedSentence) -> list[interfaces.ner.NamedEntity]
resolve_coref(entities: list[NamedEntity]) -> list[interfaces.ner.CorefChain]
```

Given a segmented sentence (from Project 1 — its **stub**, until it merges for real),
label named-entity spans `PER`/`LOC`/`ORG`/`MISC`. `token_start`/`token_end` are 0-based,
end-exclusive indices into the SAME sentence's tokens — a span is a Python slice, never a
character offset. Locate spans against the source yourself; never trust a model-reported
offset. Coreference then groups mentions across sentences of the same document that refer
to the same entity. `source` must be `"real"`.

## Independence

This project is self-contained and runs in parallel with all the others — you wait on no one.
You build, test, and grade against the deterministic, committed stub
(`interfaces.stubs.linguistics_stub.stub_segment`) — **never** against Project 1's real output,
which you do not need and never wait for. At merge time the professor swaps the stub for the real
segmenter and re-runs your *unchanged* test suite; that swap is the integration step, not your job.

## Required products

- `src/vietnlp/linguistics/ner.py` — the `extract_entities()` implementation.
- `src/vietnlp/linguistics/coref.py` — the `resolve_coref()` implementation.
- `tests/test_linguistics_ner*.py`, `tests/test_linguistics_coref*.py` — your own tests.
- `TESTING.md` (in this directory) — filled in with real design-decision rationale.
- A passing gate: `student-projects/_gate/run_gate.sh 03-ner-coref` → `Overall: PASS`.

## Requirements

### Before you start
1. Work on branch `student/03-ner-coref` (cut from tag `curriculum-base`).
2. Set up the env: `python3.11 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"`.
3. Confirm the inherited suite is green: `pytest tests -q`.
4. Read in this order: `spec.md` → `plan.md` → `README.md` → `src/vietnlp/interfaces/ner.py` in full.

### You may use
- The **stub** segmenter output (from Project 1) as your input source.
- `interfaces.ner.{NamedEntity, CorefChain, validate_named_entities}` — frozen contract.
- `tests/fixtures/corpus/fixture_sentences.jsonl` for the sentences you extract from (via the stub segmenter).

### You must not
- Touch `src/vietnlp/interfaces/**`, `src/vietnlp/platform/**`, `src/vietnlp/acquisition/**`,
  `src/vietnlp/curation/**`, or Project 1/2's files (`segmentation.py`, `pos.py`, `ud_parser.py`),
  `tests/fixtures/**`, or `student-projects/_gate/**`.
- Do entity clustering / open-universe entity count (Project 7) or ontology class assignment (Project 5).

### Approach
Handle Vietnamese naming correctly:
- Full names are single `PER` spans, never split at the given/family boundary — Vietnamese
  names are Family + Middle + Given (`Nguyễn Văn Nam`).
- Given-name reference is the norm: `Nguyễn Văn Nam` is later referred to as `Nam`, not `Nguyễn`.
- Honorifics (`anh`, `chị`, `ông`, `bà`, `em`, `cô`) attach to given names and are NOT part of
  the name span — exclude them.
A sentence with zero entities is a valid, common case, not an error.

### Completion criteria
- Gate reports `Overall: PASS` (scope, clean install, schema, provenance `source=="real"`,
  your unit tests, golden test, ≥6 own tests across NER+coref with all required input classes:
  `honorific`, `span`, `degenerate`, `adversarial`, no live-only fixtures).
- Golden invariant: entity text occurs verbatim (NFC-normalized) at its claimed span.
- `TESTING.md` explains your span-bounding and coref-linking decisions.
- `git diff curriculum-base...student/03-ner-coref --stat` touches only your `owned_paths`.
- You can explain any line of your submission and why it is there.

## Contributing on GitHub

The repo lives at `git@github.com:phunghx/VietnamesModel.git`
(HTTPS: `https://github.com/phunghx/VietnamesModel.git`). Your branch,
`student/03-ner-coref`, is already pushed there, cut from tag
`curriculum-base`.

1. Clone and check out your branch:
   ```
   git clone git@github.com:phunghx/VietnamesModel.git
   cd VietnamesModel && git checkout student/03-ner-coref
   ```
   If you don't have push access to this repo, fork it on GitHub first, add
   your fork as a second remote, and push your commits there instead — open
   the PR in step 4 from your fork's `student/03-ner-coref` branch.
2. Commit early and often directly to `student/03-ner-coref` (or its copy on
   your fork). This branch's commit history is part of what gets reviewed,
   not just the final diff.
3. Periodically sync interface fixes: `git fetch origin && git merge origin/main`.
   The professor only ever changes `main` to republish a genuine
   `interfaces/**` defect fix (see "Interface change control" in the
   top-level `student-projects/README.md`) — this should be rare.
4. When `student-projects/_gate/run_gate.sh 03-ner-coref` reports
   `Overall: PASS` and `TESTING.md` is filled in, open a **Pull Request from
   `student/03-ner-coref` into `main`** on GitHub. That PR is your
   submission — it is what gets folded into the final concatenation of all 9
   projects. Do not merge it yourself; the professor merges after the gate
   plus the manual review pass described in the top-level README.
5. Never touch `src/vietnlp/interfaces/**` or `student-projects/_gate/**` in
   your PR (both are in every project's `forbidden_paths` — the gate's scope
   check fails on any diff there). Found a real defect in one? Open a GitHub
   Issue describing it instead of editing it.

## Optional: checking against a merged upstream project

You are graded entirely against the frozen stub
(`interfaces.stubs.linguistics_stub.stub_segment`) — that never changes, and
you never have to wait on Project 1. If Project 1's student has already
pushed real, `source="real"` commits to `student/01-word-seg-pos` and you
want an extra sanity check:

1. `git fetch origin student/01-word-seg-pos`
2. In a throwaway script (never inside your committed test suite), import
   `vietnlp.linguistics.segmentation.segment` directly from that branch's
   checkout and feed its real output into your `extract_entities()` instead
   of the stub's.
3. Note anything you learn in `TESTING.md` as a bonus observation — it does
   not change your contract: both stub and real output validate against the
   identical frozen `SegmentedSentence` schema, so your gate submission must
   still work, and be graded, using only the stub.

Never merge their branch into yours, and never make your submission depend
on their branch existing — it may land after yours, change after yours, or
not land in time at all.
