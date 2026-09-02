# The gate

One script (`gate.py`, wrapped by `run_gate.sh`), one `gate.yaml` per
project. Run it against a project's branch before merge:

```
student-projects/_gate/run_gate.sh 01-word-seg-pos
```

`run_gate.sh <slug>` reads `student-projects/<slug>/gate.yaml` and runs 8
checks in order; the first FAIL halts everything after it (later steps
show `SKIP`). Pass `--skip-venv` for a fast local dry run that skips step
2's clean-venv install (useful while iterating; never skip it for the
real pre-merge gate run). Pass `--base <ref>` if the base isn't
`curriculum-base` (e.g. while testing the gate itself before that tag
exists).

**An automated PASS is the floor to merge, not the merge decision.**
Manual review always follows a PASS -- see the checklist in
`student-projects/README.md`'s "The gate" section.

## The 8 steps

1. **Scope** -- the branch's diff against the base ref touches only
   `owned_paths`, never `forbidden_paths` (`interfaces/**` always
   included). Every other project's files are implicitly out of scope
   too, since anything not matching `owned_paths` fails.
2. **Clean install** -- `pip install -e .` into a throwaway venv, then
   `import vietnlp`. Catches a submission that only works inside the
   student's own already-configured environment.
3. **Schema conformance** -- runs the project's declared producer
   function(s) (see each `gate.yaml`'s `producers:` list) over fixed,
   reproducible input (built by a loader under `_gate/inputs/`, usually
   an upstream project's **stub** output -- never a real upstream
   submission, so a project is graded against a fixed target, not
   whatever another branch happens to contain today) and validates every
   output against the matching frozen `interfaces.*` pandera schema.
4. **Provenance** -- every object the project's own producer emitted
   carries `source == "real"` (the field named by `provenance_field` in
   `gate.yaml`). A submission whose objects are still tagged `"stub"`
   fails here even if steps 1-3 pass.
5. **Unit tests** -- the project's own test files (`own_test_glob`), zero
   failures.
6. **Golden-file test** -- the professor-authored test at `golden_test`.
   `SKIP`s (not `FAIL`s) if that file doesn't exist yet, e.g. before
   Project 1's own golden test is written, or for a project whose golden
   test authoring is still a follow-up pass beyond this session.
7. **Own-suite presence** -- at least `min_own_tests` functions matching
   `def test_*` across the project's own test files, and every string in
   `required_input_classes` appears somewhere in that text (test name,
   docstring, or comment). This is a presence floor only -- it does not
   check the tests are *good*, just that the required input classes were
   not skipped entirely. Test quality is a manual-review judgment call.
8. **No reserved live-only fixtures** -- none of `live_db`, `live_store`,
   `live_silver_store`, `live_deepseek_client` (from `tests/conftest.py`)
   appear in the project's own test files. Those fixtures self-skip
   without a live Postgres/MinIO/DeepSeek stack, and are reserved for the
   platform's own live-integration suite -- never appropriate for an
   offline student deliverable that must run without network or API
   spend (CLAUDE.md's own testing agreement).

## After a PASS: manual review

1. Read the golden-file test itself for gameability (does it actually
   exercise the invariant it claims to, or could a trivial/overfit
   implementation pass it?).
2. Spot-check several of the student's own tests against their
   `TESTING.md` rationale -- does the reasoning show genuine
   understanding, or does it read like unreviewed assistant output?
3. Check Vietnamese-specific edge cases against the matching
   `.claude/agents/*.md` persona's standards (folded into each project's
   own `spec.md` already -- `vietnamese-linguist`, `treebank-adjudicator`,
   `ontology-engineer`, `semantics-engineer`, `oupm-modeler`).
4. Confirm `interfaces/**` is untouched (step 1 already checks this
   mechanically, but re-confirm by eye -- this is the one directory a
   silent, accidental scope violation would be most damaging).
5. Merge, then re-run the full inherited test suite (`pytest tests -q`)
   on `main`.

## `_gate/` itself is frozen

Every project's `forbidden_paths` includes `student-projects/_gate/**`,
same as `interfaces/**`. Gate logic, input loaders, and this README are
professor-owned; a student's own gate-adjacent material (their
`TESTING.md`, their own test files) lives under their own project
directory or in `tests/`, never here.
