"""Deterministic, naive stub for Project 6's output -- unblocks Project 9.

Emits one flat, untyped predicate per token (`(tok "<form>")`) with no
event variable, no argument structure, and no quantifier scope --
`type_checked` is always `False`, since no ontology type-checking is
attempted. NOT a reference implementation: Project 6's real job is
exactly the neo-Davidsonian event semantics and scope resolution this
stub skips.
"""

from __future__ import annotations

from vietnlp.interfaces.semantics import LogicalForm
from vietnlp.interfaces.ud import DependencyParse


def stub_logical_form(parse: DependencyParse) -> LogicalForm:
    predicates = tuple(f'(tok "{t.form}")' for t in parse.tokens)
    form_sexp = "(and " + " ".join(predicates) + ")" if predicates else "(and)"
    return LogicalForm(
        sent_id=parse.sent_id,
        form_sexp=form_sexp,
        predicates=predicates,
        type_checked=False,
        source="stub",
    )
