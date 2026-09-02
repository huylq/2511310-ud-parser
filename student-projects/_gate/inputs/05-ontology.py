"""Gate input loader for Project 5 (Ontology Engineering).

Builds `NamedEntity` objects via Project 1's stub segmenter and Project 3's
stub NER (`interfaces.stubs.ner_stub.stub_extract_entities`) chained
together -- Project 5 consumes Project 3's output per the plan's
dependency graph (`3 -> 5`).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

from vietnlp.interfaces.ner import NamedEntity  # noqa: E402
from vietnlp.interfaces.stubs.linguistics_stub import stub_segment  # noqa: E402
from vietnlp.interfaces.stubs.ner_stub import stub_extract_entities  # noqa: E402

SENTENCES_PATH = REPO_ROOT / "tests" / "fixtures" / "corpus" / "fixture_sentences.jsonl"


def build_inputs() -> list[NamedEntity]:
    rows = [json.loads(line) for line in SENTENCES_PATH.read_text(encoding="utf-8").splitlines()]
    entities: list[NamedEntity] = []
    for r in rows:
        sentence = stub_segment(r["sent_id"], r["register"], r["text"])
        entities.extend(stub_extract_entities(sentence))
    return entities
