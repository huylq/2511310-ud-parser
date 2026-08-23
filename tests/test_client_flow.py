"""The client's call ordering is a correctness property, not an implementation detail.

Cache before budget, budget before spending, record before caching. These tests pin
that order using a stubbed transport, so no network or API key is needed.
"""

import httpx
import pytest

from vietnlp.platform.agents.budget import BudgetExceeded, BudgetLedger
from vietnlp.platform.agents.cache import ResponseCache
from vietnlp.platform.agents.client import AgentClient


def _response(content: str, prompt_tokens=100, completion_tokens=10):
    return httpx.Response(
        200,
        json={
            "choices": [{"message": {"content": content}}],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "prompt_cache_hit_tokens": 0,
            },
        },
    )


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-not-real")
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return _response('{"score": 4, "reason": "ok"}')

    c = AgentClient(
        flow_run_id="test-flow",
        ledger=BudgetLedger(tmp_path / "b.db", flow_cap_usd=1.0, daily_cap_usd=1.0, total_cap_usd=1.0),
        cache=ResponseCache(tmp_path / "c.db"),
    )
    c._client = httpx.Client(
        base_url="https://api.deepseek.test",
        transport=httpx.MockTransport(handler),
        headers={"Authorization": "Bearer test-key-not-real"},
    )
    c._calls = calls
    return c


def test_identical_input_is_served_from_cache_without_a_second_call(client):
    first = client.run("quality_score", "sys", "Xin chào", prompt_version="v1")
    second = client.run("quality_score", "sys", "Xin chào", prompt_version="v1")

    assert len(client._calls) == 1, "second identical call must not hit the API"
    assert first.cached is False and second.cached is True
    assert second.usd == 0.0


def test_bumping_prompt_version_invalidates_the_cache(client):
    client.run("quality_score", "sys", "Xin chào", prompt_version="v1")
    client.run("quality_score", "sys", "Xin chào", prompt_version="v2")
    assert len(client._calls) == 2, "a new prompt version must not reuse old answers"


def test_cache_hit_is_free_even_when_the_budget_is_exhausted(client):
    """Cache lookup precedes the budget gate, so cached work never gets blocked."""
    client.run("quality_score", "sys", "Xin chào", prompt_version="v1")
    from vietnlp.platform.agents.policy import Model

    client.ledger.record(
        flow_run_id="test-flow", task="quality_score", model=Model.CHAT,
        input_tokens=10_000_000, cached_tokens=0, output_tokens=0,
    )
    hit = client.run("quality_score", "sys", "Xin chào", prompt_version="v1")
    assert hit.cached is True


def test_exhausted_budget_blocks_an_uncached_call_before_spending(client):
    from vietnlp.platform.agents.policy import Model

    client.ledger.record(
        flow_run_id="test-flow", task="quality_score", model=Model.CHAT,
        input_tokens=10_000_000, cached_tokens=0, output_tokens=0,
    )
    with pytest.raises(BudgetExceeded):
        client.run("quality_score", "sys", "văn bản mới", prompt_version="v1")
    assert client._calls == [], "budget must be checked before the request is sent"


def test_spend_is_recorded_for_a_real_call(client):
    client.run("quality_score", "sys", "Xin chào", prompt_version="v1")
    assert client.ledger.spent("test-flow").calls == 1
    assert client.ledger.spent("test-flow").flow_usd > 0


def test_reasoner_payload_omits_temperature(tmp_path, monkeypatch):
    """deepseek-reasoner rejects a temperature field; sending one 400s the call."""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-not-real")
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json as _json
        seen.update(_json.loads(request.content))
        return _response('{"form": "(and (buy e))", "predicates": ["buy"]}')

    c = AgentClient(
        flow_run_id="f",
        ledger=BudgetLedger(tmp_path / "b.db", flow_cap_usd=1.0, daily_cap_usd=1.0, total_cap_usd=1.0),
        cache=ResponseCache(tmp_path / "c.db"),
    )
    c._client = httpx.Client(base_url="https://x.test", transport=httpx.MockTransport(handler))
    c.run("semantic_parse", "sys", "Nam mua sách", prompt_version="v1")

    assert seen["model"] == "deepseek-reasoner"
    assert "temperature" not in seen
