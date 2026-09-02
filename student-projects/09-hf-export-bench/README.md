# Project 9: HF Export & Benchmark Harness

Read `spec.md` → `plan.md` → this file's Quickstart → start.

## Quickstart

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests -q
```

Your code: `src/vietnlp/export/**`. Your tests:
`tests/test_export_*.py`. Everything else is read-only from your branch
except `student-projects/09-hf-export-bench/**` — see `gate.yaml`.

## Checking your progress

```bash
student-projects/_gate/run_gate.sh 09-hf-export-bench --skip-venv
student-projects/_gate/run_gate.sh 09-hf-export-bench
```

## Submission checklist

- [ ] Gate reports `Overall: PASS`.
- [ ] `TESTING.md` written.
- [ ] `git diff curriculum-base...student/09-hf-export-bench --stat`
      touches only your `owned_paths`.
- [ ] Your dataset card passes `validate_dataset_card()`.
