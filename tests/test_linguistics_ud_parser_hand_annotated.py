"""Format/tree contract for the student's hand-annotated set (Week 2 §5).

This validates supplied annotations; it does not run or implement a parser.
The Week 2 ten-tag minimum is checked here; per-tag counts are reported in
student-projects/02-ud-parsing/analysis/hand_annotated_check.json.
"""
from datetime import date
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlparse

import pytest

from vietnlp.interfaces._common import UD_DEPREL
from vietnlp.interfaces.ud import (
    DependencyParse,
    UDToken,
    is_single_rooted_tree,
    validate_dependency_parse,
)

DATA = (Path(__file__).resolve().parents[1]
        / "student-projects/02-ud-parsing/data/hand_annotated.conllu")
REQUIRED_METADATA = {
    "sent_id", "text", "source_url", "source_name", "accessed", "register",
    "synthetic", "constructions", "uncertain", "notes",
}
REGISTERS = {"formal", "informal", "non_diacritic", "teencode", "mixed"}
CONSTRUCTIONS = {
    "clf_num", "clf_bare", "clf_noun", "coord", "hay_or", "hay_good",
    "svc_di", "dir", "poss_cua", "poss_bare", "topic", "particle",
    "do_dem", "emoticon", "degenerate",
}


def _read_conllu(path):
    """Read only integer-ID basic trees, without another CoNLL-U library."""
    sentences = []
    metadata, rows = {}, []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line:
            if metadata or rows:
                assert metadata and rows, f"Incomplete sentence at line {line_number}"
                sentences.append((metadata, rows))
            metadata, rows = {}, []
        elif line.startswith("# "):
            assert not rows, f"Comment after tokens at line {line_number}"
            key, separator, value = line[2:].partition(" =")
            assert separator and key not in metadata, f"Invalid metadata at line {line_number}"
            metadata[key] = value.lstrip(" ")
        else:
            fields = line.split("\t")
            assert len(fields) == 10, f"Expected ten TAB-separated columns at line {line_number}"
            assert re.fullmatch(r"[1-9][0-9]*", fields[0]), f"Non-integer ID at line {line_number}"
            assert fields[6].isdigit(), f"Invalid HEAD at line {line_number}"
            rows.append(fields)
    assert not metadata and not rows, "Final sentence must end with a blank line"
    return sentences


SENTENCES = _read_conllu(DATA)


def test_hand_annotated_utf8_nfc_and_lf():
    raw = DATA.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf"), "Do not write a UTF-8 BOM"
    assert b"\r" not in raw, "Use LF line endings"
    assert raw.endswith(b"\n\n"), "Keep a blank line after the final sentence"
    content = raw.decode("utf-8")
    assert unicodedata.is_normalized("NFC", content)


def test_hand_annotated_count_and_unique_ids():
    assert len(SENTENCES) >= 20
    ids = [metadata["sent_id"] for metadata, _ in SENTENCES]
    assert len(ids) == len(set(ids))


def test_hand_annotated_week2_construction_coverage():
    tags = {
        tag.strip()
        for metadata, _ in SENTENCES
        for tag in metadata["constructions"].split(",")
        if tag.strip()
    }
    assert len(tags) >= 10, f"Week 2 requires ten distinct tags; found {sorted(tags)}"


@pytest.mark.parametrize("metadata,rows", SENTENCES,
                         ids=[m["sent_id"] for m, _ in SENTENCES])
def test_hand_annotated_sentence_contract(metadata, rows):
    sid = metadata["sent_id"]
    assert REQUIRED_METADATA <= metadata.keys(), sid
    for field in REQUIRED_METADATA - {"constructions", "source_url"}:
        assert metadata[field].strip(), (sid, field)
    assert re.fullmatch(r"hc-[0-9]{3,}", sid)
    assert metadata["register"] in REGISTERS, sid
    assert metadata["synthetic"] in {"true", "false"}, sid
    assert metadata["uncertain"] in {"true", "false"}, sid
    assert re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", metadata["accessed"]), sid
    date.fromisoformat(metadata["accessed"])
    if metadata["synthetic"] == "false":
        source = urlparse(metadata["source_url"])
        assert source.scheme in {"http", "https"} and source.netloc, sid
    tags = [t.strip() for t in metadata["constructions"].split(",") if t.strip()]
    assert set(tags) <= CONSTRUCTIONS, (sid, tags)
    assert len(tags) == len(set(tags)), sid
    assert unicodedata.is_normalized("NFC", metadata["text"]), sid
    assert [row[1] for row in rows] == metadata["text"].split(), sid
    assert [int(row[0]) for row in rows] == list(range(1, len(rows) + 1)), sid
    for row in rows:
        assert row[3] == "X", (sid, row)
        assert row[7] in UD_DEPREL, (sid, row)
        assert 0 <= int(row[6]) <= len(rows), (sid, row)
        assert (row[6] == "0") == (row[7] == "root"), (sid, row)
        assert all(row[i] == "_" for i in (2, 4, 5, 8)), (sid, row)
        assert row[9] == "_" or row[9].startswith("VTB="), (sid, row)
    parse = DependencyParse(
        sent_id=sid,
        tokens=tuple(UDToken(idx=int(r[0]) - 1, form=r[1], upos=r[3],
                             head=int(r[6]), deprel=r[7]) for r in rows),
        source="real",
    )
    assert validate_dependency_parse(parse) is parse
    assert is_single_rooted_tree(parse), sid


def test_hand_annotated_synthetic_fraction():
    synthetic = sum(m["synthetic"] == "true" for m, _ in SENTENCES)
    assert synthetic / len(SENTENCES) < 0.20
