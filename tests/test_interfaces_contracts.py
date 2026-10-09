"""Inherited contract checks for Project 2's input and output schemas."""
import pytest

from vietnlp.interfaces import linguistics, ud


def test_segmented_sentence_round_trip():
    sentence = linguistics.SegmentedSentence(
        sent_id="doc1:0",
        register="formal",
        tokens=(
            linguistics.Token(idx=0, form="Sinh viên", syllables=("Sinh", "viên"), upos="NOUN"),
            linguistics.Token(idx=1, form="học", syllables=("học",), upos="VERB"),
        ),
        source="stub",
    )
    assert linguistics.validate_segmented_sentence(sentence) is sentence


def test_segmented_sentence_rejects_zero_tokens():
    sentence = linguistics.SegmentedSentence(sent_id="doc1:0", register="formal", tokens=())
    with pytest.raises(ValueError):
        linguistics.validate_segmented_sentence(sentence)


def test_dependency_parse_round_trip_and_tree_shape():
    parse = ud.DependencyParse(
        sent_id="doc1:0",
        tokens=(
            ud.UDToken(idx=0, form="Sinh viên", upos="NOUN", head=2, deprel="nsubj"),
            ud.UDToken(idx=1, form="học", upos="VERB", head=0, deprel="root"),
        ),
        source="stub",
    )
    assert ud.validate_dependency_parse(parse) is parse
    assert ud.is_single_rooted_tree(parse)


def test_dependency_parse_rejects_two_roots():
    parse = ud.DependencyParse(
        sent_id="doc1:0",
        tokens=(
            ud.UDToken(idx=0, form="a", upos="NOUN", head=0, deprel="root"),
            ud.UDToken(idx=1, form="b", upos="VERB", head=0, deprel="root"),
        ),
    )
    ud.validate_dependency_parse(parse)  # per-row shape is fine
    assert not ud.is_single_rooted_tree(parse)  # tree-shape invariant is separate, and fails
