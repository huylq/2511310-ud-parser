"""Contract for Project 9 (HF Export & Benchmark Harness) -- the terminal
project; nothing downstream consumes its output.

`ExportRow` is the denormalized, one-row-per-sentence shape written into
the HF dataset dir (mirrors `sentences` in
`platform/db/migrations/0001_core_schema.sql`; annotation layers
(tokens/entities/logical forms) are separate HF config splits joined on
`sent_id`, not nested here -- an HF `datasets.Dataset` has no notion of a
foreign key or nested struct-of-variable-length-list the way Postgres
does). `BenchmarkReport` is the harness's scored output against the
VLSP/UIT-VSFC/ViQuAD-shaped stand-ins in `tests/fixtures/benchmark/`,
explicitly not the real shared-task benchmark -- `stub_note` records that
distinction on every report so a number never gets quoted without its
caveat.

Per the plan's I/O contract table: the dataset card must document the
register taxonomy and NFC normalization explicitly. `REQUIRED_CARD_SECTIONS`
makes that a checkable list for the gate rather than a convention a student
might forget to write down.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import pandera as pa

SCHEMA_VERSION = "1.0"

REQUIRED_CARD_SECTIONS = (
    "register_taxonomy",  # the news/forum/social/... registers this export spans
    "normalization",       # must state NFC, and that the original input-method form is preserved upstream
    "license",
    "known_limitations",
)


@dataclass(frozen=True)
class ExportRow:
    sent_id: str
    document_id: str
    text: str                 # NFC-normalized
    register: str
    tokens: tuple[str, ...]     # surface forms, in document order
    lang: str = "vi"


@dataclass(frozen=True)
class BenchmarkReport:
    task: str          # e.g. "vlsp_ner", "uit_vsfc", "viquad"
    metric: str
    value: float
    n_items: int
    stub_note: str = ""  # non-empty when scored against a format-shape stand-in, not the real benchmark


EXPORT_ROW_SCHEMA = pa.DataFrameSchema(
    {
        "sent_id": pa.Column(str, pa.Check.str_length(min_value=1)),
        "document_id": pa.Column(str, pa.Check.str_length(min_value=1)),
        "text": pa.Column(str, pa.Check.str_length(min_value=1)),
        "register": pa.Column(str, pa.Check.str_length(min_value=1)),
        "lang": pa.Column(str),
    },
    strict=False,
)


def to_row(row: ExportRow) -> dict:
    return {
        "sent_id": row.sent_id,
        "document_id": row.document_id,
        "text": row.text,
        "register": row.register,
        "lang": row.lang,
    }


def validate_export_rows(rows: list[ExportRow], expected_count: int | None = None) -> list[ExportRow]:
    """`expected_count`, when supplied, enforces the plan's "row count
    matches source" golden invariant -- pass the source sentence count the
    export was drawn from."""
    if rows:
        EXPORT_ROW_SCHEMA.validate(pd.DataFrame([to_row(r) for r in rows]), lazy=False)
    if expected_count is not None and len(rows) != expected_count:
        raise ValueError(f"exported {len(rows)} rows, expected {expected_count}")
    return rows


def validate_benchmark_report(report: BenchmarkReport) -> BenchmarkReport:
    if not report.task.strip() or not report.metric.strip():
        raise ValueError("BenchmarkReport requires a non-empty task and metric")
    if not 0.0 <= report.value <= 1.0:
        raise ValueError(f"BenchmarkReport {report.task}/{report.metric}: value {report.value} outside [0,1]")
    if report.n_items <= 0:
        raise ValueError(f"BenchmarkReport {report.task}/{report.metric}: n_items must be positive")
    return report


def validate_dataset_card(sections_present: set[str]) -> None:
    """`sections_present` is the set of section keys a student's dataset
    card actually documents. Raises `ValueError` naming whichever of
    `REQUIRED_CARD_SECTIONS` is missing."""
    missing = [s for s in REQUIRED_CARD_SECTIONS if s not in sections_present]
    if missing:
        raise ValueError(f"dataset card missing required section(s): {missing}")
