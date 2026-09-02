# Project 7: OUPM Entity Resolution

Read `spec.md` → `plan.md` → this file's Quickstart → start.

## Quickstart

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests -q
```

Your code: `src/vietnlp/oupm/resolver.py`. Your tests:
`tests/test_oupm_*.py`. Everything else is read-only from your branch
except `student-projects/07-oupm/**` — see `gate.yaml`.

## Checking your progress

```bash
student-projects/_gate/run_gate.sh 07-oupm --skip-venv
student-projects/_gate/run_gate.sh 07-oupm
```

## Submission checklist

- [ ] Gate reports `Overall: PASS`.
- [ ] `TESTING.md` written.
- [ ] `git diff curriculum-base...student/07-oupm --stat` touches only
      your `owned_paths`.
- [ ] You can explain why your system does NOT merge the
      same-name-different-people case.
