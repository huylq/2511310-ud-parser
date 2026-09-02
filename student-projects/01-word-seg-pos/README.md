# Project 1: Word Segmentation & POS Tagging

Read in this order: `spec.md` (what to build and why) → `plan.md` (your
15-week task breakdown) → this file's Quickstart → start Task 1.

## Quickstart

```bash
cd <repo root, on your student/01-word-seg-pos branch>
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests -q                          # confirm the inherited suite is green before you start
pytest tests/golden/test_word_seg_pos_golden.py -q   # will SKIP until you create segmentation.py -- expected
```

Your code lives at `src/vietnlp/linguistics/segmentation.py` (and
optionally `pos.py`). Your tests live at
`tests/test_linguistics_segmentation.py` (and optionally
`tests/test_linguistics_pos.py`). Everything else in this repo is
read-only from your branch except `student-projects/01-word-seg-pos/**`
— see `gate.yaml`'s `owned_paths`/`forbidden_paths` for the exact list.

## Checking your progress

```bash
student-projects/_gate/run_gate.sh 01-word-seg-pos --skip-venv   # fast, skips the clean-install check
student-projects/_gate/run_gate.sh 01-word-seg-pos               # full, run before you consider yourself done
```

See `student-projects/_gate/README.md` for exactly what each of the 8
steps checks.

## Submission checklist

- [ ] `student-projects/_gate/run_gate.sh 01-word-seg-pos` reports
      `Overall: PASS`.
- [ ] `TESTING.md` is written (see its template in this directory) —
      every design decision explained, not just listed.
- [ ] `git diff curriculum-base...student/01-word-seg-pos --stat` touches
      only files in your `owned_paths`.
- [ ] You can explain, to the professor, any single line of your
      segmentation or tagging logic and why it's there.

## What happens after you submit

Per `student-projects/README.md`: an automated gate PASS is the floor to
merge, not the merge decision. The professor reads your golden-test
approach for gameability, spot-checks your own tests against `TESTING.md`,
and checks your Vietnamese-specific handling against
`.claude/agents/vietnamese-linguist.md`'s standards (already folded into
`spec.md`'s Architecture section). After merge, Project 2 and Project 3
can start building against your real segmenter instead of the stub.
