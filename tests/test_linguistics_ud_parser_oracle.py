"""Tests for static-oracle replay and gold-child readiness."""

from copy import deepcopy
from pathlib import Path

import pytest

from vietnlp.interfaces.ud import (
    DependencyParse,
    UDToken,
    is_single_rooted_tree,
    validate_dependency_parse,
)
from vietnlp.linguistics import ud_parser


def _project(conllu):
    return ud_parser.project_sentence(ud_parser.read_conllu(conllu)[0])


def _assert_unchanged(state, before):
    assert vars(state) == vars(before)


def _replay(gold):
    oracle = ud_parser.StaticOracle(gold)
    state = ud_parser.ParserState(tuple(token.form for token in gold.tokens))
    actions = []
    n = len(gold.tokens)
    for _ in range(2 * n):
        assert not state.is_terminal
        before = deepcopy(state)
        action = oracle.next_action(state)
        _assert_unchanged(state, before)
        assert action in state.legal_actions()
        state.apply(action)
        actions.append((action.kind, action.label))

    assert state.is_terminal
    assert state.heads == [None] + [token.head for token in gold.tokens]
    assert state.labels == [None] + [token.deprel for token in gold.tokens]
    assert sum(kind == "SHIFT" for kind, _ in actions) == n
    assert sum(kind != "SHIFT" for kind, _ in actions) == n
    assert actions[-1] == ("RIGHT_ARC", "root")
    tree = DependencyParse(
        sent_id=gold.metadata["sent_id"],
        tokens=tuple(
            UDToken(index - 1, form, "X", state.heads[index], state.labels[index])
            for index, form in enumerate(state.tokens, start=1)
        ),
        source="real",
    )
    validate_dependency_parse(tree)
    assert is_single_rooted_tree(tree)
    return actions


@pytest.mark.parametrize(
    "conllu, expected",
    [
        # Delay each right reduction until its dependent has all its children.
        pytest.param(
            """# sent_id = oracle-left-headed-chain
1	A	_	X	_	_	0	root	_	_
2	B	_	X	_	_	1	dep	_	_
3	C	_	X	_	_	2	dep	_	_""",
            [("SHIFT", None), ("SHIFT", None), ("SHIFT", None),
             ("RIGHT_ARC", "dep"), ("RIGHT_ARC", "dep"), ("RIGHT_ARC", "root")],
            id="left_headed_chain",
        ),
        # Left reductions occur as soon as each gold head reaches the stack.
        pytest.param(
            """# sent_id = oracle-right-headed-chain
1	A	_	X	_	_	2	dep	_	_
2	B	_	X	_	_	3	dep	_	_
3	C	_	X	_	_	0	root	_	_""",
            [("SHIFT", None), ("SHIFT", None), ("LEFT_ARC", "dep"),
             ("SHIFT", None), ("LEFT_ARC", "dep"), ("RIGHT_ARC", "root")],
            id="right_headed_chain",
        ),
        # A head may retain three children on both sides without binary branching.
        pytest.param(
            """# sent_id = oracle-three-dependents
1	A	_	X	_	_	2	dep	_	_
2	B	_	X	_	_	0	root	_	_
3	C	_	X	_	_	2	dep	_	_
4	D	_	X	_	_	2	dep	_	_""",
            [("SHIFT", None), ("SHIFT", None), ("LEFT_ARC", "dep"),
             ("SHIFT", None), ("RIGHT_ARC", "dep"), ("SHIFT", None),
             ("RIGHT_ARC", "dep"), ("RIGHT_ARC", "root")],
            id="three_dependents_both_sides",
        ),
    ],
)
def test_static_oracle_round_trip_and_action_order(conllu, expected):
    assert _replay(_project(conllu)) == expected


SINGLE_TOKEN = """# sent_id = oracle-single-token
1	A	_	X	_	_	0	root	_	_"""


def test_static_oracle_degenerate_single_token():
    """A leaf root needs one SHIFT and one final ROOT arc."""
    assert _replay(_project(SINGLE_TOKEN)) == [
        ("SHIFT", None), ("RIGHT_ARC", "root"),
    ]


def test_static_oracle_clf_round_trip():
    """Preserve the classifier relation when replaying left reductions."""
    gold = _project("""# sent_id = oracle-clf
1	chuyến	_	X	_	_	2	clf	_	_
2	xe	_	X	_	_	3	nsubj	_	_
3	chậm	_	X	_	_	0	root	_	_""")
    assert _replay(gold) == [
        ("SHIFT", None), ("SHIFT", None), ("LEFT_ARC", "clf"),
        ("SHIFT", None), ("LEFT_ARC", "nsubj"), ("RIGHT_ARC", "root"),
    ]


def test_static_oracle_degenerate_empty_input_raises():
    """Reject an empty gold sentence before starting a replay."""
    gold = ud_parser.ProjectedSentence(
        metadata={"sent_id": "oracle-empty"}, tokens=(),
        word_to_syllables={}, syllable_to_word={}, is_projective=True,
    )
    with pytest.raises(ValueError, match="oracle-empty"):
        ud_parser.StaticOracle(gold)


ANNOTATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "student-projects/02-ud-parsing/data/hand_annotated.conllu"
)
PROJECTIVE_ANNOTATIONS = [
    gold
    for source in ud_parser.read_conllu(ANNOTATION_PATH.read_text(encoding="utf-8"))
    if (gold := ud_parser.project_sentence(source)).is_projective
]


@pytest.mark.parametrize(
    "gold", PROJECTIVE_ANNOTATIONS,
    ids=[gold.metadata["sent_id"] for gold in PROJECTIVE_ANNOTATIONS],
)
def test_static_oracle_round_trip_projective_hand_annotated(gold):
    """Reconstruct every head and label in each projective annotated tree."""
    _replay(gold)


# In each tree, token 2 is the gold child of the next reduction's dependent.
READINESS_CASES = [
    pytest.param(
        """# sent_id = oracle-ready-left
1	A	_	X	_	_	3	dep	_	_
2	B	_	X	_	_	1	dep	_	_
3	C	_	X	_	_	0	root	_	_
4	D	_	X	_	_	3	dep	_	_""",
        1, 3, "LEFT_ARC", id="left_arc",
    ),
    pytest.param(
        """# sent_id = oracle-ready-right
1	A	_	X	_	_	0	root	_	_
2	B	_	X	_	_	3	dep	_	_
3	C	_	X	_	_	1	dep	_	_
4	D	_	X	_	_	1	dep	_	_""",
        3, 1, "RIGHT_ARC", id="right_arc",
    ),
]


def _readiness_state(gold, child_head, child_label):
    state = ud_parser.ParserState(tuple(token.form for token in gold.tokens))
    state.stack = [0, 1, 3]
    state.buffer_pos = 4
    state.heads[2] = child_head
    state.labels[2] = child_label
    return state


@pytest.mark.parametrize("conllu, dependent, other, kind", READINESS_CASES)
@pytest.mark.parametrize(
    "child_status, expected",
    [("correct", True), ("unassigned", False),
     ("wrong_head", False), ("wrong_label", False)],
)
def test_static_oracle_readiness_requires_gold_child_head_and_label(
    conllu, dependent, other, kind, child_status, expected
):
    """A child counts only when both its head and label match gold."""
    gold = _project(conllu)
    oracle = ud_parser.StaticOracle(gold)
    child_head, child_label = {
        "correct": (dependent, "dep"),
        "unassigned": (None, None),
        "wrong_head": (other, "dep"),
        "wrong_label": (dependent, "obj"),
    }[child_status]
    state = _readiness_state(gold, child_head, child_label)
    before = deepcopy(state)

    assert oracle.is_ready(state, dependent) is expected
    assert oracle.is_ready(state, 2) is True  # A gold leaf is immediately ready.
    _assert_unchanged(state, before)
    if expected:
        action = oracle.next_action(state)
        assert action == ud_parser.Action(kind, "dep")
        assert action in state.legal_actions()
        _assert_unchanged(state, before)


@pytest.mark.parametrize("conllu, dependent, other, kind", READINESS_CASES)
def test_static_oracle_reports_blocked_state(conllu, dependent, other, kind):
    """A wrong child label must not permit reduction after buffer exhaustion."""
    gold = _project(conllu)
    oracle = ud_parser.StaticOracle(gold)
    state = _readiness_state(gold, dependent, "obj")
    state.buffer_pos = 5
    state.heads[4] = gold.tokens[3].head
    state.labels[4] = gold.tokens[3].deprel
    before = deepcopy(state)

    with pytest.raises(ValueError, match=gold.metadata["sent_id"]) as error:
        oracle.next_action(state)
    assert "stack" in str(error.value)
    assert "buffer_pos" in str(error.value)
    _assert_unchanged(state, before)


@pytest.mark.parametrize(
    "conllu",
    [
        # Crossing non-ROOT arcs cannot be replayed by arc-standard reductions.
        pytest.param(
            """# sent_id = oracle-crossing-nonroot
1	A	_	X	_	_	0	root	_	_
2	B	_	X	_	_	1	dep	_	_
3	C	_	X	_	_	1	dep	_	_
4	D	_	X	_	_	2	dep	_	_""",
            id="nonroot_crossing",
        ),
        # Include crossings involving the artificial ROOT arc.
        pytest.param(
            """# sent_id = oracle-crossing-root
1	A	_	X	_	_	3	dep	_	_
2	B	_	X	_	_	0	root	_	_
3	C	_	X	_	_	2	dep	_	_""",
            id="root_crossing",
        ),
    ],
)
def test_static_oracle_adversarial_nonprojective_raises(conllu):
    """Reject a non-projective gold tree before producing any actions."""
    gold = _project(conllu)
    assert gold.is_projective is False
    with pytest.raises(ValueError, match=gold.metadata["sent_id"]):
        ud_parser.StaticOracle(gold)


def test_static_oracle_rejects_terminal_state():
    """A completed run has no next oracle action."""
    gold = _project(SINGLE_TOKEN)
    oracle = ud_parser.StaticOracle(gold)
    state = ud_parser.ParserState(("A",))
    state.apply(ud_parser.Action("SHIFT"))
    state.apply(ud_parser.Action("RIGHT_ARC", "root"))
    before = deepcopy(state)
    with pytest.raises(ValueError, match=gold.metadata["sent_id"]):
        oracle.next_action(state)
    _assert_unchanged(state, before)


def test_static_oracle_rejects_mismatched_tokens():
    """The current state must contain the same syllables as the gold tree."""
    gold = _project(SINGLE_TOKEN)
    oracle = ud_parser.StaticOracle(gold)
    state = ud_parser.ParserState(("B",))
    before = deepcopy(state)
    with pytest.raises(ValueError, match=gold.metadata["sent_id"]):
        oracle.next_action(state)
    _assert_unchanged(state, before)
