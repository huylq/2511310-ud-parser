"""Contract for Project 2 (UD Dependency Parsing), consumed by Project 4
(treebank adjudication), Project 6 (semantics), 8 (serving) and 9
(export/benchmark).

Mirrors `tokens.head/deprel` in
`platform/db/migrations/0001_core_schema.sql`. `head` follows the CoNLL-U
convention: 0 means this token is the sentence root; any other value is the
1-based index (matching `UDToken.idx + 1`, since `idx` here is 0-based like
`interfaces.linguistics.Token`) of this token's syntactic head.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd
import pandera as pa

from ._common import SOURCE_VALUES, UD_DEPREL, UPOS_TAGSET


SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class UDToken:
    idx: int          # 0-based, matches interfaces.linguistics.Token.idx for the same sentence
    form: str
    upos: str
    head: int         # 0 = root; else 1-based idx of the head token (idx + 1)
    deprel: str


@dataclass(frozen=True)
class DependencyParse:
    sent_id: str
    tokens: tuple[UDToken, ...]
    source: Literal["stub", "real"] = "stub"


UD_SCHEMA = pa.DataFrameSchema(
    {
        "sent_id": pa.Column(str, pa.Check.str_length(min_value=1)),
        "idx": pa.Column(int, pa.Check.ge(0)),
        "form": pa.Column(str, pa.Check.str_length(min_value=1)),
        "upos": pa.Column(str, pa.Check.isin(UPOS_TAGSET)),
        "head": pa.Column(int, pa.Check.ge(0)),
        "deprel": pa.Column(str, pa.Check.isin(UD_DEPREL)),
        "source": pa.Column(str, pa.Check.isin(SOURCE_VALUES)),
    },
    strict=False,
)


def to_rows(parse: DependencyParse) -> list[dict]:
    return [
        {
            "sent_id": parse.sent_id,
            "idx": t.idx,
            "form": t.form,
            "upos": t.upos,
            "head": t.head,
            "deprel": t.deprel,
            "source": parse.source,
        }
        for t in parse.tokens
    ]


def is_single_rooted_tree(parse: DependencyParse) -> bool:
    """Structural check pandera's column-level schema can't express: exactly
    one root, every non-root head refers to a real token in this sentence,
    and no cycles. This is the golden-file invariant Project 2's own test
    suite must enforce over the full fixture corpus -- it is NOT checked by
    `validate_dependency_parse`, which only checks per-row shape; a caller
    that also needs tree-well-formedness must call this too."""
    n = len(parse.tokens)
    if n == 0:
        return False
    roots = [t for t in parse.tokens if t.head == 0]
    if len(roots) != 1:
        return False
    valid_idx = {t.idx for t in parse.tokens}
    by_idx = {t.idx: t for t in parse.tokens}
    for t in parse.tokens:
        if t.head != 0 and (t.head - 1) not in valid_idx:
            return False
    # Cycle check: walk each token's head chain; it must terminate at the root.
    for t in parse.tokens:
        seen = set()
        cur = t
        while cur.head != 0:
            if cur.idx in seen:
                return False
            seen.add(cur.idx)
            cur = by_idx[cur.head - 1]
    return True


def validate_dependency_parse(parse: DependencyParse) -> DependencyParse:
    """Per-row schema check only -- see `is_single_rooted_tree` for the
    separate tree-shape invariant. Raises `pandera.errors.SchemaError` or
    `ValueError` on a nonconforming object."""
    rows = to_rows(parse)
    if not rows:
        raise ValueError(f"DependencyParse {parse.sent_id!r} has zero tokens")
    UD_SCHEMA.validate(pd.DataFrame(rows), lazy=False)
    return parse
