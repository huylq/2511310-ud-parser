"""Gate input loader for Project 9 (HF Export & Benchmark Harness).

Builds one input per document in `serving/gold_fixture.json` -- the same
static substrate Project 8 serves from (see
`tests/fixtures/generate_gold_fixture.py`). Only the `export_rows`
producer is checked by the mechanical gate; benchmark-scoring correctness
against `tests/fixtures/benchmark/*_stub.jsonl` is exercised by the
golden-file test instead (scoring logic has no single structural contract
a generic loader can drive meaningfully).
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
GOLD_FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "serving" / "gold_fixture.json"


def build_inputs() -> list[dict]:
    return json.loads(GOLD_FIXTURE_PATH.read_text(encoding="utf-8"))
