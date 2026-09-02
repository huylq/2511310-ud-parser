"""Generates `corpus/fixture_sentences.jsonl` -- the sentence-level fixture
Projects 1-3 build against, one JSON object per sentence.

Purely mechanical: runs the real
`vietnlp.platform.db.sentence_split.split_sentences` over every document in
the committed `fixture_corpus.jsonl` (CLAUDE.md rule 1's spirit applied to
fixtures too -- this file is reproducible from the corpus, never
hand-edited). `sent_id` follows the
`f"{content_hash}:{sent_idx}"` convention documented in
`src/vietnlp/interfaces/linguistics.py::SegmentedSentence.sent_id`, so a
student can join a `fixture_sentences.jsonl` row straight into a
`SegmentedSentence` without inventing an id scheme.

Run: python tests/fixtures/generate_fixture_sentences.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from vietnlp.platform.db.sentence_split import split_sentences  # noqa: E402

CORPUS_PATH = Path(__file__).parent / "corpus" / "fixture_corpus.jsonl"
OUT_PATH = Path(__file__).parent / "corpus" / "fixture_sentences.jsonl"


def build_sentences() -> list[dict]:
    records = []
    with CORPUS_PATH.open(encoding="utf-8") as f:
        documents = [json.loads(line) for line in f]
    for doc in documents:
        for sent_idx, (text, char_start, char_end) in enumerate(split_sentences(doc["text"])):
            records.append({
                "sent_id": f"{doc['content_hash']}:{sent_idx}",
                "content_hash": doc["content_hash"],
                "idx": sent_idx,
                "text": text,
                "char_start": char_start,
                "char_end": char_end,
                "register": doc["register"],
            })
    return records


def main() -> None:
    records = build_sentences()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"wrote {len(records)} sentences (from 100 documents) to {OUT_PATH}")


if __name__ == "__main__":
    main()
