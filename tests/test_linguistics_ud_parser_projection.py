"""Tests for projecting basic word trees onto syllable tokens."""

from copy import deepcopy
from pathlib import Path

import pytest

from vietnlp.interfaces._common import UD_DEPREL
from vietnlp.interfaces.ud import (
    DependencyParse,
    UDToken,
    is_single_rooted_tree,
    validate_dependency_parse,
)
from vietnlp.linguistics import ud_parser


# Expected token fields: ID, FORM, HEAD, DEPREL. Mapping IDs are one-based.
PROJECTION_CASES = [
    # Both incoming and outgoing word arcs use the first-syllable anchor.
    pytest.param(
        """# sent_id = two-syllables
1	nhiều	_	X	_	_	2	det	_	_
2	xe khách	_	X	_	_	3	nsubj	_	_
3	chậm	_	X	_	_	0	root	_	_""",
        ((1, "nhiều", 2, "det"), (2, "xe", 4, "nsubj"),
         (3, "khách", 2, "dep"), (4, "chậm", 0, "root")),
        {1: (1,), 2: (2, 3), 3: (4,)},
        id="two_syllables_external_arcs",
    ),
    # Later syllables attach directly to the anchor, with UPOS reset to X.
    pytest.param(
        """# sent_id = three-syllables
1	A B C	_	NOUN	_	_	0	root	_	_
2	D	_	NOUN	_	_	1	dep	_	_""",
        ((1, "A", 0, "root"), (2, "B", 1, "dep"),
         (3, "C", 1, "dep"), (4, "D", 1, "dep")),
        {1: (1, 2, 3), 2: (4,)},
        id="three_syllables_star",
    ),
    # Trailing punctuation disappears as a node and remains in FORM.
    pytest.param(
        """# sent_id = trailing-punctuation
1	đi	_	X	_	_	0	root	_	_
2	.	_	PUNCT	_	_	1	punct	_	_""",
        ((1, "đi.", 0, "root"),),
        {1: (1,), 2: ()},
        id="trailing_punctuation",
    ),
    # Consecutive suffixes retain source order.
    pytest.param(
        """# sent_id = repeated-punctuation
1	đi	_	X	_	_	0	root	_	_
2	!	_	PUNCT	_	_	1	punct	_	_
3	?	_	PUNCT	_	_	1	punct	_	_""",
        ((1, "đi!?", 0, "root"),),
        {1: (1,), 2: (), 3: ()},
        id="repeated_punctuation_order",
    ),
    # Follow the original chain through multiple deleted heads.
    pytest.param(
        """# sent_id = deleted-punctuation-chain
1	đi	_	X	_	_	0	root	_	_
2	,	_	PUNCT	_	_	1	punct	_	_
3	.	_	PUNCT	_	_	2	punct	_	_
4	ăn	_	X	_	_	3	xcomp	_	_""",
        ((1, "đi,.", 0, "root"), (2, "ăn", 1, "xcomp")),
        {1: (1,), 2: (), 3: (), 4: (2,)},
        id="deleted_head_original_chain",
    ),
    # A backward mark with no preceding target remains a node.
    pytest.param(
        """# sent_id = leading-backward-mark
1	,	_	PUNCT	_	_	2	punct	_	_
2	đi	_	X	_	_	0	root	_	_""",
        ((1, ",", 2, "punct"), (2, "đi", 0, "root")),
        {1: (1,), 2: (2,)},
        id="leading_backward_mark",
    ),
    # A root remains even when its FORM is punctuation.
    pytest.param(
        """# sent_id = punctuation-root
1	.	_	PUNCT	_	_	0	root	_	_
2	đi	_	X	_	_	1	dep	_	_""",
        ((1, ".", 0, "root"), (2, "đi", 1, "dep")),
        {1: (1,), 2: (2,)},
        id="punctuation_root",
    ),
    # Opening and closing brackets glue in opposite directions.
    pytest.param(
        """# sent_id = bracket-pair
1	(	_	PUNCT	_	_	2	punct	_	_
2	đi	_	X	_	_	0	root	_	_
3	)	_	PUNCT	_	_	2	punct	_	_""",
        ((1, "(đi)", 0, "root"),),
        {1: (), 2: (1,), 3: ()},
        id="opening_and_closing_brackets",
    ),
    # Quotes are glued before the target word is split into syllables.
    pytest.param(
        """# sent_id = typographic-quotes
1	“	_	PUNCT	_	_	2	punct	_	_
2	nhà hàng	_	X	_	_	0	root	_	_
3	”	_	PUNCT	_	_	2	punct	_	_""",
        ((1, "“nhà", 0, "root"), (2, "hàng”", 1, "dep")),
        {1: (), 2: (1, 2), 3: ()},
        id="typographic_quotes_and_word_split",
    ),
    # Nested prefixes and suffixes retain their original order.
    pytest.param(
        """# sent_id = nested-opening-marks
1	“	_	PUNCT	_	_	3	punct	_	_
2	(	_	PUNCT	_	_	3	punct	_	_
3	đi	_	X	_	_	0	root	_	_
4	)	_	PUNCT	_	_	3	punct	_	_
5	”	_	PUNCT	_	_	3	punct	_	_""",
        ((1, "“(đi)”", 0, "root"),),
        {1: (), 2: (), 3: (1,), 4: (), 5: ()},
        id="nested_mark_order",
    ),
    # Straight quotes alternate, including an opening quote after other tokens.
    pytest.param(
        '''# sent_id = alternating-straight-quotes
1	đi	_	X	_	_	0	root	_	_
2	:	_	PUNCT	_	_	1	punct	_	_
3	"	_	PUNCT	_	_	4	punct	_	_
4	ăn	_	X	_	_	1	xcomp	_	_
5	"	_	PUNCT	_	_	4	punct	_	_
6	"	_	PUNCT	_	_	7	punct	_	_
7	trưa	_	X	_	_	4	obj	_	_
8	"	_	PUNCT	_	_	7	punct	_	_''',
        ((1, "đi:", 0, "root"), (2, '"ăn"', 1, "xcomp"),
         (3, '"trưa"', 2, "obj")),
        {1: (1,), 2: (), 3: (), 4: (2,), 5: (), 6: (), 7: (3,), 8: ()},
        id="straight_quote_alternation",
    ),
    # An opening mark without a following target remains a node.
    pytest.param(
        """# sent_id = opening-mark-without-target
1	đi	_	X	_	_	0	root	_	_
2	(	_	PUNCT	_	_	1	punct	_	_""",
        ((1, "đi", 0, "root"), (2, "(", 1, "punct")),
        {1: (1,), 2: (2,)},
        id="opening_mark_without_target",
    ),
    # A retained punctuation root can receive surrounding punctuation.
    pytest.param(
        """# sent_id = punctuation-only
1	(	_	PUNCT	_	_	2	punct	_	_
2	.	_	PUNCT	_	_	0	root	_	_
3	)	_	PUNCT	_	_	2	punct	_	_""",
        ((1, "(.)", 0, "root"),),
        {1: (), 2: (1,), 3: ()},
        id="punctuation_only_root",
    ),
    # Map a source subtype without changing its attachment.
    pytest.param(
        """# sent_id = subtype-mapping
1	A	_	X	_	_	0	root	_	_
2	B	_	X	_	_	1	compound:svc	_	_""",
        ((1, "A", 0, "root"), (2, "B", 1, "compound")),
        {1: (1,), 2: (2,)},
        id="base_label_mapping",
    ),
]


def _assert_valid_projection(projected):
    tree = DependencyParse(
        sent_id=projected.metadata["sent_id"],
        tokens=tuple(
            UDToken(token.id - 1, token.form, token.upos, token.head, token.deprel)
            for token in projected.tokens
        ),
        source="real",
    )
    assert [token.id for token in projected.tokens] == list(range(1, len(tree.tokens) + 1))
    assert all(token.upos == "X" for token in projected.tokens)
    assert all(token.deprel in UD_DEPREL for token in projected.tokens)
    validate_dependency_parse(tree)
    assert is_single_rooted_tree(tree), tree.sent_id


@pytest.mark.parametrize("conllu, expected, word_to_syllables", PROJECTION_CASES)
def test_project_sentence_exact_tokens_and_mappings(conllu, expected, word_to_syllables):
    """Check exact projected nodes and both directions of the ID mapping."""
    source = ud_parser.read_conllu(conllu)[0]
    before = deepcopy(source)

    projected = ud_parser.project_sentence(source)

    assert tuple(
        (token.id, token.form, token.head, token.deprel)
        for token in projected.tokens
    ) == expected
    assert projected.word_to_syllables == word_to_syllables
    assert projected.syllable_to_word == {
        syllable_id: word_id
        for word_id, syllable_ids in word_to_syllables.items()
        for syllable_id in syllable_ids
    }
    assert projected.metadata["sent_id"] == source.metadata["sent_id"]
    assert source == before
    _assert_valid_projection(projected)


def test_project_sentence_resets_straight_quote_state():
    """An unmatched quote in one sentence must not affect the next sentence."""
    source = ud_parser.read_conllu('''# sent_id = unmatched-opening-quote
1	"	_	PUNCT	_	_	2	punct	_	_
2	đi	_	X	_	_	0	root	_	_''')[0]

    for _ in range(2):
        projected = ud_parser.project_sentence(source)
        assert tuple(
            (token.id, token.form, token.head, token.deprel)
            for token in projected.tokens
        ) == ((1, '"đi', 0, "root"),)
        assert projected.word_to_syllables == {1: (), 2: (1,)}
        assert projected.syllable_to_word == {1: 2}
        _assert_valid_projection(projected)


ANNOTATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "student-projects/02-ud-parsing/data/hand_annotated.conllu"
)
ANNOTATED_SENTENCES = ud_parser.read_conllu(ANNOTATION_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "source", ANNOTATED_SENTENCES,
    ids=[sentence.metadata["sent_id"] for sentence in ANNOTATED_SENTENCES],
)
def test_project_sentence_hand_annotated_tree_and_mapping(source):
    """Every annotated tree remains valid and its retained IDs round-trip."""
    before = deepcopy(source)

    projected = ud_parser.project_sentence(source)

    _assert_valid_projection(projected)
    assert source == before
    assert projected.metadata["sent_id"] == source.metadata["sent_id"]
    assert set(projected.word_to_syllables) == {token.id for token in source.tokens}
    assert set(projected.syllable_to_word) == {token.id for token in projected.tokens}
    assigned = []
    for word_id, syllable_ids in projected.word_to_syllables.items():
        assert tuple(sorted(syllable_ids)) == syllable_ids
        for syllable_id in syllable_ids:
            assert projected.syllable_to_word[syllable_id] == word_id
            assigned.append(syllable_id)
    assert sorted(assigned) == list(range(1, len(projected.tokens) + 1))
