"""Tests for arc-standard state changes and attachment guards."""

from copy import deepcopy

import pytest

from vietnlp.interfaces._common import UD_DEPREL
from vietnlp.linguistics import ud_parser


def _assert_unchanged(state, before):
    for name in ("tokens", "stack", "buffer_pos", "heads", "labels"):
        assert getattr(state, name) == getattr(before, name), name


def _assert_rejected(state, action):
    before = deepcopy(state)
    with pytest.raises(ValueError):
        state.apply(action)
    _assert_unchanged(state, before)


def _shift_two():
    state = ud_parser.ParserState(("A", "B"))
    state.apply(ud_parser.Action("SHIFT"))
    state.apply(ud_parser.Action("SHIFT"))
    return state


def test_arc_standard_initial_state():
    """Start with only ROOT on the stack and every head unassigned."""
    state = ud_parser.ParserState(("A", "B", "C"))

    assert state.tokens == ("A", "B", "C")
    assert state.stack == [0]
    assert state.buffer_pos == 1
    assert state.heads == [None, None, None, None]
    assert state.labels == [None, None, None, None]
    assert state.is_terminal is False


def test_arc_standard_shift_updates_stack_and_buffer_only():
    """SHIFT consumes one buffer token without creating an arc."""
    state = ud_parser.ParserState(("A", "B"))

    state.apply(ud_parser.Action("SHIFT"))

    assert state.stack == [0, 1]
    assert state.buffer_pos == 2
    assert state.heads == [None, None, None]
    assert state.labels == [None, None, None]


@pytest.mark.parametrize(
    "kind, expected_stack, expected_heads, expected_labels",
    [
        ("LEFT_ARC", [0, 2], [None, 2, None], [None, "dep", None]),
        ("RIGHT_ARC", [0, 1], [None, None, 1], [None, None, "dep"]),
    ],
)
def test_arc_standard_arc_direction_and_reduction(
    kind, expected_stack, expected_heads, expected_labels
):
    """Each ARC assigns the correct dependent and removes that stack item."""
    state = _shift_two()

    state.apply(ud_parser.Action(kind, "dep"))

    assert state.stack == expected_stack
    assert state.buffer_pos == 3
    assert state.heads == expected_heads
    assert state.labels == expected_labels


def test_arc_standard_rejects_shift_with_exhausted_buffer():
    """Reject SHIFT after all tokens have been consumed."""
    state = _shift_two()
    _assert_rejected(state, ud_parser.Action("SHIFT"))


@pytest.mark.parametrize("kind", ["LEFT_ARC", "RIGHT_ARC"])
def test_arc_standard_rejects_arc_on_short_stack(kind):
    """An ARC requires two stack items."""
    state = ud_parser.ParserState(("A",))
    _assert_rejected(state, ud_parser.Action(kind, "dep"))


def test_arc_standard_rejects_root_as_dependent():
    """LEFT_ARC must never give the artificial ROOT a head."""
    state = ud_parser.ParserState(("A",))
    state.apply(ud_parser.Action("SHIFT"))
    _assert_rejected(state, ud_parser.Action("LEFT_ARC", "dep"))


@pytest.mark.parametrize(
    "kind, dependent_id, existing_head",
    [("LEFT_ARC", 1, 2), ("RIGHT_ARC", 2, 1)],
)
def test_arc_standard_rejects_already_assigned_dependent(kind, dependent_id, existing_head):
    """An attachment must not overwrite an existing head or label."""
    state = _shift_two()
    state.heads[dependent_id] = existing_head
    state.labels[dependent_id] = "dep"
    _assert_rejected(state, ud_parser.Action(kind, "dep"))


@pytest.mark.parametrize("kind", ["LEFT_ARC", "RIGHT_ARC"])
def test_arc_standard_rejects_self_loop(kind):
    """Reject equal head/dependent IDs before mutating the state."""
    state = _shift_two()
    state.stack = [0, 1, 1]
    _assert_rejected(state, ud_parser.Action(kind, "dep"))


@pytest.mark.parametrize("kind, head_id, dependent_id", [("LEFT_ARC", 2, 1), ("RIGHT_ARC", 1, 2)])
def test_arc_standard_cycle_closing_arc_is_rejected(kind, head_id, dependent_id):
    """The proposed head already depends on the proposed dependent."""
    state = _shift_two()
    state.heads[head_id] = dependent_id
    state.labels[head_id] = "dep"
    _assert_rejected(state, ud_parser.Action(kind, "dep"))


@pytest.mark.parametrize("kind, head_id", [("LEFT_ARC", 2), ("RIGHT_ARC", 1)])
def test_arc_standard_rejects_invalid_reference_in_head_chain(kind, head_id):
    """Reject a head chain pointing outside the sentence."""
    state = _shift_two()
    state.heads[head_id] = 3
    state.labels[head_id] = "dep"
    _assert_rejected(state, ud_parser.Action(kind, "dep"))


@pytest.mark.parametrize(
    "kind, stack",
    [("LEFT_ARC", [0, 1, 3]), ("RIGHT_ARC", [0, -1, 1]), ("LEFT_ARC", [0, 3, 1])],
)
def test_arc_standard_rejects_out_of_range_arc_endpoints(kind, stack):
    """Invalid token IDs must not be used as Python list indices."""
    state = _shift_two()
    state.stack = stack.copy()
    _assert_rejected(state, ud_parser.Action(kind, "dep"))


@pytest.mark.parametrize(
    "kind, label",
    [
        ("SHIFT", "dep"),
        ("LEFT_ARC", None),
        ("RIGHT_ARC", None),
        ("LEFT_ARC", "_"),
        ("RIGHT_ARC", "_"),
        ("LEFT_ARC", "root"),
        ("UNKNOWN", None),
    ],
)
def test_arc_standard_rejects_invalid_action_or_label(kind, label):
    """Reject malformed action kinds and labels without changing state."""
    state = _shift_two()
    _assert_rejected(state, ud_parser.Action(kind, label))


def test_arc_standard_rejects_root_arc_while_buffer_has_input():
    """ROOT attachment cannot occur while unread input remains."""
    state = ud_parser.ParserState(("A", "B"))
    state.apply(ud_parser.Action("SHIFT"))
    _assert_rejected(state, ud_parser.Action("RIGHT_ARC", "root"))


def test_arc_standard_rejects_root_arc_with_extra_stack_items():
    """The final ROOT action requires stack [0, j]."""
    state = _shift_two()
    _assert_rejected(state, ud_parser.Action("RIGHT_ARC", "root"))


def test_arc_standard_degenerate_single_token_root_once():
    """A single token receives ROOT exactly once."""
    state = ud_parser.ParserState(("A",))
    state.apply(ud_parser.Action("SHIFT"))
    assert state.is_terminal is False

    state.apply(ud_parser.Action("RIGHT_ARC", "root"))

    assert state.stack == [0]
    assert state.buffer_pos == 2
    assert state.heads == [None, 0]
    assert state.labels == [None, "root"]
    assert state.is_terminal is True
    _assert_rejected(state, ud_parser.Action("RIGHT_ARC", "root"))


def test_arc_standard_degenerate_empty_input_raises():
    """Empty input cannot initialize a decoding run."""
    with pytest.raises(ValueError):
        ud_parser.ParserState(())


NONROOT_LABELS = UD_DEPREL - {"root"}


@pytest.mark.parametrize(
    "stack, buffer_pos, heads, labels, expected",
    [
        # At the start only SHIFT is legal.
        pytest.param(
            [0], 1, [None] * 4, [None] * 4,
            {("SHIFT", None)}, id="initial",
        ),
        # Two real stack items allow either ARC direction and another SHIFT.
        pytest.param(
            [0, 1, 2], 3, [None] * 4, [None] * 4,
            {("SHIFT", None)}
            | {("LEFT_ARC", label) for label in NONROOT_LABELS}
            | {("RIGHT_ARC", label) for label in NONROOT_LABELS},
            id="two_real_stack_items",
        ),
        # All remaining dependents are assigned; only the ROOT arc remains.
        pytest.param(
            [0, 2], 4, [None, 2, None, 2], [None, "dep", None, "dep"],
            {("RIGHT_ARC", "root")}, id="final_root",
        ),
    ],
)
def test_arc_standard_legal_action_set(stack, buffer_pos, heads, labels, expected):
    """Enumerate exactly the legal actions without mutating the state."""
    state = ud_parser.ParserState(("A", "B", "C"))
    state.stack = stack.copy()
    state.buffer_pos = buffer_pos
    state.heads = heads.copy()
    state.labels = labels.copy()
    before = deepcopy(state)

    actual = {(action.kind, action.label) for action in state.legal_actions()}

    assert actual == expected
    _assert_unchanged(state, before)


def test_arc_standard_full_run_uses_n_shifts_and_n_arcs():
    """A complete three-token run takes 2n actions and creates a valid tree."""
    from vietnlp.interfaces.ud import (
        DependencyParse, UDToken, is_single_rooted_tree, validate_dependency_parse,
    )

    state = ud_parser.ParserState(("A", "B", "C"))
    actions = [
        ud_parser.Action("SHIFT"),
        ud_parser.Action("SHIFT"),
        ud_parser.Action("LEFT_ARC", "dep"),
        ud_parser.Action("SHIFT"),
        ud_parser.Action("RIGHT_ARC", "dep"),
        ud_parser.Action("RIGHT_ARC", "root"),
    ]
    for action in actions:
        assert state.is_terminal is False
        assert action in state.legal_actions()
        state.apply(action)

    assert state.is_terminal is True
    assert state.stack == [0]
    assert state.buffer_pos == 4
    assert state.heads == [None, 2, 0, 2]
    assert state.labels == [None, "dep", "root", "dep"]
    assert len(actions) == 2 * len(state.tokens)
    assert sum(action.kind == "SHIFT" for action in actions) == len(state.tokens)
    assert sum(action.kind != "SHIFT" for action in actions) == len(state.tokens)
    assert state.heads.count(0) == 1

    tree = DependencyParse(
        sent_id="transition-run",
        tokens=tuple(
            UDToken(index - 1, form, "X", state.heads[index], state.labels[index])
            for index, form in enumerate(state.tokens, start=1)
        ),
        source="real",
    )
    validate_dependency_parse(tree)
    assert is_single_rooted_tree(tree)
    assert state.legal_actions() == ()
