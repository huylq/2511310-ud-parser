# Project 3: NER & Coreference Resolution

Read `spec.md` → `plan.md` → this file's Quickstart → start.

## Quickstart

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests -q
```

Your code: `src/vietnlp/linguistics/ner.py`,
`src/vietnlp/linguistics/coref.py`. Your tests:
`tests/test_linguistics_ner*.py`, `tests/test_linguistics_coref*.py`.
Everything else is read-only from your branch except
`student-projects/03-ner-coref/**` — see `gate.yaml`.

## Checking your progress

```bash
student-projects/_gate/run_gate.sh 03-ner-coref --skip-venv
student-projects/_gate/run_gate.sh 03-ner-coref
```

## Submission checklist

- [ ] Gate reports `Overall: PASS`.
- [ ] `TESTING.md` written.
- [ ] `git diff curriculum-base...student/03-ner-coref --stat` touches
      only your `owned_paths`.
- [ ] You can explain any line of your NER/coref logic and why it's there.
