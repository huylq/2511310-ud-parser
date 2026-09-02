"""Gate input loader for Project 1 (Word Segmentation & POS Tagging).

Builds `(sent_id, register, text)` tuples straight from the raw fixture
sentences -- Project 1 is the one project with no upstream stub to build
on, since it IS the first stage.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SENTENCES_PATH = REPO_ROOT / "tests" / "fixtures" / "corpus" / "fixture_sentences.jsonl"


def build_inputs() -> list[tuple[str, str, str]]:
    rows = [json.loads(line) for line in SENTENCES_PATH.read_text(encoding="utf-8").splitlines()]
    return [(r["sent_id"], r["register"], r["text"]) for r in rows]
