# Project 8: Serving API

Read `spec.md` → `plan.md` → this file's Quickstart → start.

## Quickstart

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pip install fastapi httpx   # add to your own owned files if you introduce new deps -- see pyproject.toml
pytest tests -q
```

Your code: `src/vietnlp/serving/**`. Your tests:
`tests/test_serving_*.py`. Everything else is read-only from your branch
except `student-projects/08-serving/**` — see `gate.yaml`.

## Checking your progress

```bash
student-projects/_gate/run_gate.sh 08-serving --skip-venv
student-projects/_gate/run_gate.sh 08-serving
```

## Submission checklist

- [ ] Gate reports `Overall: PASS`.
- [ ] `TESTING.md` written.
- [ ] `git diff curriculum-base...student/08-serving --stat` touches only
      your `owned_paths`.
- [ ] You can show a response body with diacritics intact, not
      `\uXXXX`-escaped.
