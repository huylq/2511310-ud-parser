"""Inherited checks for the segmentation input stub and UD output stub."""
from vietnlp.interfaces import linguistics, ud
from vietnlp.interfaces.stubs import linguistics_stub, ud_stub


def _stub_sentence(text="Sinh viên học bài ."):
    return linguistics_stub.stub_segment("doc1:0", "formal", text)


def test_linguistics_stub_round_trip():
    sentence = _stub_sentence()
    assert sentence.source == "stub"
    assert linguistics.validate_segmented_sentence(sentence) is sentence
    # naive: splits on whitespace, never merges syllables into one word
    assert [t.form for t in sentence.tokens] == ["Sinh", "viên", "học", "bài", "."]
    assert all(t.upos == "X" for t in sentence.tokens)


def test_ud_stub_round_trip():
    parse = ud_stub.stub_parse(_stub_sentence())
    assert parse.source == "stub"
    assert ud.validate_dependency_parse(parse) is parse
    assert ud.is_single_rooted_tree(parse)
