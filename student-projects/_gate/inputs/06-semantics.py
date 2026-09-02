"""Gate input loader for Project 6 (Semantics / FOL).

Builds `DependencyParse` objects via Project 1's stub segmenter chained
into Project 2's stub parser -- Project 6 consumes Project 2's output
per the plan's dependency graph (`{2,5} -> 6`). Ontology predicate type
signatures (the other half of Project 6's declared inputs) are read
directly from the frozen seed ontology by the project's own type-checker,
not threaded through this loader -- the gate's schema-conformance step
only exercises the structural `LogicalForm` contract, not type-checking
quality (that is the golden-file test's job).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

from vietnlp.interfaces.ud import DependencyParse  # noqa: E402
from vietnlp.interfaces.stubs.linguistics_stub import stub_segment  # noqa: E402
from vietnlp.interfaces.stubs.ud_stub import stub_parse  # noqa: E402

SENTENCES_PATH = REPO_ROOT / "tests" / "fixtures" / "corpus" / "fixture_sentences.jsonl"


def build_inputs() -> list[DependencyParse]:
    rows = [json.loads(line) for line in SENTENCES_PATH.read_text(encoding="utf-8").splitlines()]
    return [stub_parse(stub_segment(r["sent_id"], r["register"], r["text"])) for r in rows]
