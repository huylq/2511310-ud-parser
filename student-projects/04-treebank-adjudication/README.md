# Project 4: Treebank Curation & Adjudication

Read `spec.md` → `plan.md` → this file's Quickstart → start.

## Quickstart

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests -q
```

Your code: `src/vietnlp/treebank/adjudicator.py`. Your tests:
`tests/test_treebank_*.py`. Everything else is read-only from your branch
except `student-projects/04-treebank-adjudication/**` — see `gate.yaml`.

## Checking your progress

```bash
student-projects/_gate/run_gate.sh 04-treebank-adjudication --skip-venv
student-projects/_gate/run_gate.sh 04-treebank-adjudication
```

## Submission checklist

- [ ] Gate reports `Overall: PASS`.
- [ ] `TESTING.md` written.
- [ ] `git diff curriculum-base...student/04-treebank-adjudication --stat`
      touches only your `owned_paths`.
- [ ] You can defend every ruling in your own words, unaided.
