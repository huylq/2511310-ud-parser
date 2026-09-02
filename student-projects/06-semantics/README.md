# Project 6: Semantics / FOL

Read `spec.md` → `plan.md` → this file's Quickstart → start.

## Quickstart

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests -q
```

Your code: `src/vietnlp/semantics/translator.py`. Your tests:
`tests/test_semantics_*.py`. Everything else is read-only from your
branch except `student-projects/06-semantics/**` — see `gate.yaml`.

## Checking your progress

```bash
student-projects/_gate/run_gate.sh 06-semantics --skip-venv
student-projects/_gate/run_gate.sh 06-semantics
```

## Submission checklist

- [ ] Gate reports `Overall: PASS`.
- [ ] `TESTING.md` written.
- [ ] `git diff curriculum-base...student/06-semantics --stat` touches
      only your `owned_paths`.
- [ ] You can explain your S-expression grammar and type-checking rule
      without notes.
