"""Golden-file test for Project 1 (Word Segmentation & POS Tagging).
Professor-authored (per `student-projects/_gate/README.md` step 6) --
never edit this from a student branch; it is what a submission is judged
against, and `student-projects/01-word-seg-pos/gate.yaml` points here.

`pytest.importorskip` means this file collects cleanly on `main` today,
before any student has written `vietnlp.linguistics.segmentation` -- the
gate's own step 3 (schema conformance) already fails first and halts
before this step runs in that case, so the skip only matters for someone
running this file directly.

Checks the three golden invariants from the plan's I/O contract table row
for Project 1:
  - lossless syllable recombination over all 151 fixture sentences
  - every token's UPOS is in the frozen tagset
  - every entry in `known_compounds.txt` that occurs in a sentence's text
    is segmented as ONE token, never split at the space
"""
import json
import unicodedata
from pathlib import Path

import pytest

segmentation = pytest.importorskip(
    "vietnlp.linguistics.segmentation", reason="Project 1 not yet submitted"
)

from vietnlp.interfaces.linguistics import validate_segmented_sentence  # noqa: E402
from vietnlp.platform.agents.registry import UPOS_TAGSET  # noqa: E402
from tests.test_fixture_known_compounds import load_known_compounds  # noqa: E402

FIXTURES = Path(__file__).parent.parent / "fixtures" / "corpus"


def _load_sentences() -> list[dict]:
    with (FIXTURES / "fixture_sentences.jsonl").open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def _recombine(sentence) -> str:
    """Concatenates every token's underlying syllables back into one
    string, collapsing to single spaces -- the "lossless recombination"
    check does not require exact whitespace/punctuation-spacing fidelity,
    only that no syllable was dropped, duplicated, or corrupted."""
    syllables = [s for token in sentence.tokens for s in token.syllables]
    return unicodedata.normalize("NFC", " ".join(syllables))


def _original_syllables(text: str) -> str:
    return unicodedata.normalize("NFC", " ".join(text.split()))


@pytest.mark.parametrize("row", _load_sentences(), ids=lambda r: r["sent_id"])
def test_segmentation_is_schema_valid_and_marked_real(row):
    sentence = segmentation.segment(row["sent_id"], row["register"], row["text"])
    validate_segmented_sentence(sentence)
    assert sentence.source == "real", "a submission must produce source='real', never 'stub'"


@pytest.mark.parametrize("row", _load_sentences(), ids=lambda r: r["sent_id"])
def test_segmentation_is_a_lossless_syllable_recombination(row):
    sentence = segmentation.segment(row["sent_id"], row["register"], row["text"])
    assert _recombine(sentence) == _original_syllables(row["text"]), (
        f"{row['sent_id']}: syllables lost or corrupted during segmentation"
    )


@pytest.mark.parametrize("row", _load_sentences(), ids=lambda r: r["sent_id"])
def test_every_upos_is_in_the_frozen_tagset(row):
    sentence = segmentation.segment(row["sent_id"], row["register"], row["text"])
    for token in sentence.tokens:
        assert token.upos in UPOS_TAGSET, f"{row['sent_id']}: token {token.form!r} upos {token.upos!r}"


def test_known_compounds_are_never_split():
    compounds = load_known_compounds()
    sentences = _load_sentences()
    checked = 0
    for compound in compounds:
        for row in sentences:
            if compound.lower() not in row["text"].lower():
                continue
            sentence = segmentation.segment(row["sent_id"], row["register"], row["text"])
            forms = [t.form.lower() for t in sentence.tokens]
            assert compound.lower() in forms, (
                f"{row['sent_id']}: compound {compound!r} was split into separate tokens {forms}"
            )
            checked += 1
    assert checked > 0, "no known_compounds.txt entry occurred in any fixture sentence -- test is vacuous"
