"""Contract for Project 6 (Semantics / FOL), consumed by Project 9
(export/benchmark).

Mirrors `logical_forms.form_sexp/predicates/type_checked` in
`platform/db/migrations/0001_core_schema.sql`. The balanced-parens check
below mirrors `platform/agents/registry.py::_validate_logical_form` --
duplicated rather than imported because that function also does a
`predicates` dict-shape normalization specific to a raw DeepSeek response,
which is out of scope for a plain structural contract check; both must stay
in sync on the well-formedness rule itself, which is why the check is a
single, tiny, well-commented function rather than reimplemented ad hoc in
each place.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from ._common import SOURCE_VALUES

SCHEMA_VERSION = "1.0"

_SEXP_TOKEN = re.compile(r"\(|\)|[^\s()]+")


@dataclass(frozen=True)
class LogicalForm:
    sent_id: str
    form_sexp: str
    predicates: tuple[str, ...] = ()
    type_checked: bool = False
    source: Literal["stub", "real"] = "stub"


def is_balanced(form_sexp: str) -> bool:
    """Well-formedness only, per `_validate_logical_form`'s own docstring:
    this is not a correctness check. Semantic correctness (do the predicate
    arities match the ontology's type signatures) is Project 6's own
    type-checker's job, reflected in `LogicalForm.type_checked`."""
    depth = 0
    for token in _SEXP_TOKEN.findall(form_sexp):
        if token == "(":
            depth += 1
        elif token == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def validate_logical_form(lf: LogicalForm) -> LogicalForm:
    if lf.source not in SOURCE_VALUES:
        raise ValueError(f"LogicalForm {lf.sent_id!r}: source {lf.source!r} not in {sorted(SOURCE_VALUES)}")
    if not lf.form_sexp.strip():
        raise ValueError(f"LogicalForm {lf.sent_id!r}: empty form_sexp")
    if not is_balanced(lf.form_sexp):
        raise ValueError(f"LogicalForm {lf.sent_id!r}: unbalanced S-expression {lf.form_sexp!r}")
    return lf
