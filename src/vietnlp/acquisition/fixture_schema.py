"""Pandera contract for the committed synthetic fixture corpus.

This is NOT the production Bronze contract (spec S4.1 uses raw_payload:
bytes; see platform/storage/bronze.py for that). The fixture is plain-text
JSONL, so it substitutes a decoded `text` field -- JSONL cannot hold raw
bytes cleanly. The content_hash check keeps the derived-identity invariant
honest even in this substitute shape: content_hash must always be
sha256(text.encode()), never a value trusted from the input.
"""

from __future__ import annotations

import hashlib

import pandas as pd
import pandera as pa

_REGISTER_VALUES = {"formal", "informal", "teencode", "khong_dau", "mixed"}
_ROBOTS_VALUES = {"allowed", "disallowed", "no_robots"}

FIXTURE_SCHEMA = pa.DataFrameSchema(
    {
        "content_hash": pa.Column(str, pa.Check.str_matches(r"^[0-9a-f]{64}$")),
        "source_id": pa.Column(str, pa.Check.str_length(min_value=1)),
        "url": pa.Column(str, pa.Check.str_startswith("https://")),
        "fetched_at": pa.Column(str, pa.Check.str_length(min_value=1)),
        "http_status": pa.Column(int, pa.Check.in_range(100, 599)),
        "robots_decision": pa.Column(str, pa.Check.isin(_ROBOTS_VALUES)),
        "content_type": pa.Column(str, pa.Check.str_length(min_value=1)),
        "text": pa.Column(str, pa.Check.str_length(min_value=1)),
        "license": pa.Column(str, pa.Check.str_length(min_value=1)),
        "register": pa.Column(str, pa.Check.isin(_REGISTER_VALUES)),
    },
    strict=False,
    checks=pa.Check(
        lambda df: df["content_hash"] == df["text"].apply(
            lambda t: hashlib.sha256(t.encode("utf-8")).hexdigest()
        ),
        error="content_hash must equal sha256(text) -- identity is derived, never trusted from input",
    ),
)


def validate_fixture_record(record: dict) -> dict:
    """Validate one fixture-shaped record. Raises pandera.errors.SchemaError."""
    df = pd.DataFrame([record])
    validated = FIXTURE_SCHEMA.validate(df, lazy=False)
    return validated.iloc[0].to_dict()
