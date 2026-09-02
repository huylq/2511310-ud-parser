"""Gate input loader for Project 3 (NER & Coreference Resolution).

Same stub-segmented sentences as Project 2's loader -- both build on
Project 1's stub, independently of each other, per the plan's dependency
graph (`1 -> {2,3}`).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

from vietnlp.interfaces.linguistics import SegmentedSentence  # noqa: E402
from vietnlp.interfaces.stubs.linguistics_stub import stub_segment  # noqa: E402

SENTENCES_PATH = REPO_ROOT / "tests" / "fixtures" / "corpus" / "fixture_sentences.jsonl"


def build_inputs() -> list[SegmentedSentence]:
    rows = [json.loads(line) for line in SENTENCES_PATH.read_text(encoding="utf-8").splitlines()]
    return [stub_segment(r["sent_id"], r["register"], r["text"]) for r in rows]
