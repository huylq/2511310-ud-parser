"""P0's only flow: proves the orchestration wiring end-to-end with a stub.

Real Bronze-to-Silver logic belongs to P1 (curation/). This flow exists to
(a) demonstrate retry/backoff as task decorators, the reason Prefect was
chosen over Airflow (spec S3.1), and (b) prove the dead-letter path works
before anything depends on it -- CLAUDE.md rule 4: no silent drops, ever.
"""

from __future__ import annotations

from typing import Callable, Iterable

from pandera.errors import SchemaError
from prefect import flow, task

from vietnlp.acquisition.fixture_schema import validate_fixture_record

DeadLetterSink = Callable[[tuple[dict, str]], None]


@task
def _validate(record: dict) -> dict:
    """Deterministic; a schema failure is a data problem, not a transient
    one, so this task does not retry."""
    return validate_fixture_record(record)


@task(retries=2, retry_delay_seconds=1)
def _stub_silver_projection(record: dict) -> dict:
    """Placeholder for the real curation stage (P1). The retry policy models
    the transient I/O failures a real projection step would actually see."""
    return {"content_hash": record["content_hash"], "silver_stub": True}


@flow(name="bronze-to-silver-stub")
def bronze_to_silver_stub(
    records: Iterable[dict], dead_letter_sink: DeadLetterSink | None = None
) -> dict:
    processed = 0
    dead_lettered = 0
    for record in records:
        try:
            validated = _validate(record)
            _stub_silver_projection(validated)
            processed += 1
        except SchemaError as exc:
            dead_lettered += 1
            if dead_letter_sink is not None:
                dead_letter_sink((record, str(exc)))
    return {"processed": processed, "dead_lettered": dead_lettered}
