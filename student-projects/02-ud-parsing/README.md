# Project 2: UD Dependency Parsing

Read `spec.md` → `plan.md` → this file's Quickstart → start.

## Quickstart

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests -q
```

Your code: `src/vietnlp/linguistics/ud_parser.py`. Your tests:
`tests/test_linguistics_ud_parser*.py`. Everything else is read-only from
your branch except `student-projects/02-ud-parsing/**` — see `gate.yaml`.

## Checking your progress

```bash
student-projects/_gate/run_gate.sh 02-ud-parsing --skip-venv
student-projects/_gate/run_gate.sh 02-ud-parsing
```

## Submission checklist

- [ ] Gate reports `Overall: PASS`.
- [ ] `TESTING.md` written.
- [ ] `git diff curriculum-base...student/02-ud-parsing --stat` touches
      only your `owned_paths`.
- [ ] You can explain any line of your parser and why it's there.
