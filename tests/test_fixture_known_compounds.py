"""Contract for `known_compounds.txt` -- Project 1's compound-word fixture.
Backs the golden-file invariant in the plan's I/O contract table: "compounds
not split".
"""
import json
import unicodedata
from pathlib import Path

COMPOUNDS_PATH = Path(__file__).parent / "fixtures" / "corpus" / "known_compounds.txt"
CORPUS_PATH = Path(__file__).parent / "fixtures" / "corpus" / "fixture_corpus.jsonl"


def load_known_compounds() -> list[str]:
    """Reference loader every Project 1 submission's own tests should mirror:
    skip blank lines and '#' comments, keep everything else verbatim."""
    lines = COMPOUNDS_PATH.read_text(encoding="utf-8").splitlines()
    return [line for line in lines if line.strip() and not line.startswith("#")]


def test_compounds_file_exists():
    assert COMPOUNDS_PATH.exists(), "see tests/fixtures/corpus/known_compounds.txt"


def test_between_30_and_50_compounds():
    compounds = load_known_compounds()
    assert 30 <= len(compounds) <= 50, len(compounds)


def test_every_compound_spans_at_least_two_syllables():
    for compound in load_known_compounds():
        assert len(compound.split()) >= 2, compound


def test_compounds_are_unique():
    compounds = load_known_compounds()
    assert len(compounds) == len(set(compounds))


def test_compounds_are_nfc_normalized():
    for compound in load_known_compounds():
        assert compound == unicodedata.normalize("NFC", compound)


def test_most_compounds_occur_verbatim_in_the_fixture_corpus():
    with CORPUS_PATH.open(encoding="utf-8") as f:
        blob = "\n".join(json.loads(line)["text"] for line in f).lower()
    compounds = load_known_compounds()
    present = sum(1 for c in compounds if c.lower() in blob)
    assert present >= len(compounds) - 3, f"only {present}/{len(compounds)} found in fixture_corpus.jsonl"
