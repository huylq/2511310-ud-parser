"""Uses Prefect's official offline test harness -- no server, no network,
consistent with the offline pytest requirement in CLAUDE.md."""
import json
from pathlib import Path

import pytest
from prefect.testing.utilities import prefect_test_harness

from vietnlp.platform.flows.bootstrap_flow import bronze_to_silver_stub

CORPUS_PATH = Path(__file__).parent / "fixtures" / "corpus" / "fixture_corpus.jsonl"


@pytest.fixture(autouse=True, scope="module")
def _prefect_test_mode():
    with prefect_test_harness():
        yield


def _load_fixture(n: int | None = None) -> list[dict]:
    with CORPUS_PATH.open(encoding="utf-8") as f:
        records = [json.loads(line) for line in f]
    return records[:n] if n else records


def test_processes_every_valid_fixture_record():
    result = bronze_to_silver_stub(_load_fixture())
    assert result == {"processed": 100, "dead_lettered": 0}


def test_invalid_record_is_dead_lettered_not_dropped():
    """CLAUDE.md rule 4: no silent drops."""
    good = _load_fixture(3)
    bad = dict(good[0])
    bad["content_hash"] = "not-a-real-hash"  # breaks the derived-hash check

    caught = []
    result = bronze_to_silver_stub(good + [bad], dead_letter_sink=caught.append)

    assert result == {"processed": 3, "dead_lettered": 1}
    assert len(caught) == 1
    assert caught[0][0] == bad
    assert "content_hash" in caught[0][1]


def test_without_a_sink_the_record_is_still_counted_not_silently_lost():
    bad = dict(_load_fixture(1)[0])
    bad["url"] = "ftp://not-https"  # fails the fixture schema's url check

    result = bronze_to_silver_stub([bad])
    assert result == {"processed": 0, "dead_lettered": 1}
