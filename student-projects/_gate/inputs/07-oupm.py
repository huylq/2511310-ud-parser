"""Gate input loader for Project 7 (OUPM Entity Resolution).

Builds `(entities, chains)` pairs, one per document in the PROVISIONAL
`oupm_coref_probe.jsonl` (see `tests/fixtures/oupm/PROVISIONAL.md`):
`entities` are the probe's hand-specified `NamedEntity` mentions (Project 3's
output type -- taken directly from the probe rather than re-derived via
Project 3's stub, since this fixture's whole point is to test clustering
against known, deliberately-tricky mentions, not to also re-test NER);
`chains` are Project 3's STUB coreference groupings (exact-text match) over
those same mentions, per the "build against the upstream stub" pattern.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

from vietnlp.interfaces.ner import CorefChain, NamedEntity  # noqa: E402
from vietnlp.interfaces.stubs.ner_stub import stub_coref  # noqa: E402

PROBE_PATH = REPO_ROOT / "tests" / "fixtures" / "oupm" / "oupm_coref_probe.jsonl"


def build_inputs() -> list[tuple[list[NamedEntity], list[CorefChain]]]:
    docs = [json.loads(line) for line in PROBE_PATH.read_text(encoding="utf-8").splitlines()]
    pairs: list[tuple[list[NamedEntity], list[CorefChain]]] = []
    for doc in docs:
        entities = [
            NamedEntity(
                sent_id=m["sent_id"], token_start=m["token_start"], token_end=m["token_end"],
                label=m["label"], text=m["text"], source="stub",
            )
            for m in doc["mentions"]
        ]
        chains = stub_coref(entities)
        pairs.append((entities, chains))
    return pairs


def build_known_mention_ids() -> dict[str, set[str]]:
    """`validate_entity_cluster`'s `known_mention_ids` kwarg. Returns the
    UNION of every document's mention ids, not scoped per document -- the
    generic gate loads this once for the whole batch, so it can only catch
    a wholly-hallucinated mention id, not a cluster that illegally crosses
    document boundaries. That stricter, per-document check belongs to the
    golden-file test, which has per-document structure to check against."""
    docs = [json.loads(line) for line in PROBE_PATH.read_text(encoding="utf-8").splitlines()]
    all_ids = {m["mention_id"] for doc in docs for m in doc["mentions"]}
    return {"known_mention_ids": all_ids}
