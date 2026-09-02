# Project 5: Ontology Engineering

Read `spec.md` → `plan.md` → this file's Quickstart → start.

## Quickstart

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests -q
```

Your code: `src/vietnlp/ontology/induction.py`. Your tests:
`tests/test_ontology_*.py`. Everything else is read-only from your branch
except `student-projects/05-ontology/**` — see `gate.yaml`.
`tests/fixtures/corpus/seed_upper_ontology.ttl` is read-only too.

## Checking your progress

```bash
student-projects/_gate/run_gate.sh 05-ontology --skip-venv
student-projects/_gate/run_gate.sh 05-ontology
```

## Submission checklist

- [ ] Gate reports `Overall: PASS`.
- [ ] `TESTING.md` written.
- [ ] `git diff curriculum-base...student/05-ontology --stat` touches
      only your `owned_paths`.
- [ ] You can defend every disjointness axiom you added.
