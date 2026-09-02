"""Gate input loader for Project 2 (UD Dependency Parsing).

Builds `SegmentedSentence` objects via Project 1's STUB segmenter (not a
real Project 1 submission -- the gate never depends on another project's
in-progress work). This is the "build against the stub from day one"
mechanism from `student-projects/README.md`, applied to grading: Project 2
is graded on its own parser's behavior over a fixed, reproducible input,
never over whatever Project 1 happens to produce at merge time.
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
