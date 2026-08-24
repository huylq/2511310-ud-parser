"""The missing-credential guard is the one thing about this module fully
knowable and testable offline, since it's checked before any network call
is made. Step 6 of this task (a manual, not-committed verification) is
where the real result shape gets checked against the live z.ai server --
that step is not a pytest test, because it needs a real ZAI_API_KEY this
offline suite must never depend on.

Regression tests for empirically-verified shapes added after Step 6 live
verification (2026-08-25) confirm parsing handles double JSON encoding and
key normalization."""
import json
import pytest
from unittest.mock import AsyncMock, patch

from vietnlp.acquisition.mcp_client import MCPError, web_read, web_search


def test_web_search_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("ZAI_API_KEY", raising=False)
    with pytest.raises(MCPError, match="ZAI_API_KEY"):
        web_search("Vietnamese news today")


def test_web_read_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("ZAI_API_KEY", raising=False)
    with pytest.raises(MCPError, match="ZAI_API_KEY"):
        web_read("https://example.vn/article")


# Regression tests for empirically-verified shapes from Step 6 (2026-08-25)
# live verification against z.ai MCP server.


def test_web_search_parses_double_json_encoded_response(monkeypatch):
    """Verified 2026-08-25: z.ai returns double-JSON-encoded results.
    The response is a single text block containing a JSON string that
    itself is a JSON list when parsed."""
    monkeypatch.setenv("ZAI_API_KEY", "test-key")

    # Mock the _call_tool to return double-JSON-encoded response (as z.ai actually does)
    # The raw data is a list of dicts
    raw_data = [
        {
            "title": "Test Article",
            "link": "https://example.vn/article",
            "content": "Test content",
            "refer": "ref_1"
        }
    ]
    # First encoding: convert to JSON string
    json_string = json.dumps(raw_data)
    # Second encoding: wrap as a JSON string (this is what the MCP server returns)
    # Use json.dumps to properly encode the string with escaping
    mock_texts = [json.dumps(json_string)]

    with patch('vietnlp.acquisition.mcp_client._call_tool', new_callable=AsyncMock, return_value=mock_texts):
        results = web_search("test query")

        # Verify result structure and key normalization
        assert len(results) == 1
        assert results[0]["title"] == "Test Article"
        assert results[0]["url"] == "https://example.vn/article"  # 'link' normalized to 'url'
        assert results[0]["content"] == "Test content"
        assert results[0]["refer"] == "ref_1"


def test_web_search_uses_search_query_parameter(monkeypatch):
    """Verified 2026-08-25: z.ai uses 'search_query' parameter, not 'query'."""
    monkeypatch.setenv("ZAI_API_KEY", "test-key")

    raw_data = []
    json_string = json.dumps(raw_data)
    mock_texts = [json.dumps(json_string)]

    with patch('vietnlp.acquisition.mcp_client._call_tool', new_callable=AsyncMock, return_value=mock_texts) as mock_call:
        web_search("test query", count=5)

        # Verify that _call_tool was called with 'search_query' parameter
        mock_call.assert_called_once()
        call_args = mock_call.call_args
        # call_args is a tuple of (args, kwargs)
        # args[0] = URL, args[1] = tool_name, args[2] = arguments dict
        assert call_args[0][2]["search_query"] == "test query"
        assert call_args[0][2]["count"] == 5
        assert "query" not in call_args[0][2], "Parameter should be 'search_query', not 'query'"


def test_web_search_normalizes_link_to_url(monkeypatch):
    """Verified 2026-08-25: z.ai returns 'link' key, normalized to 'url'
    for API contract compatibility."""
    monkeypatch.setenv("ZAI_API_KEY", "test-key")

    raw_data = [
        {"link": "https://a.vn", "title": "A"},
        {"link": "https://b.vn", "title": "B"},
    ]
    json_string = json.dumps(raw_data)
    mock_texts = [json.dumps(json_string)]

    with patch('vietnlp.acquisition.mcp_client._call_tool', new_callable=AsyncMock, return_value=mock_texts):
        results = web_search("test")

        assert all("url" in r for r in results)
        assert results[0]["url"] == "https://a.vn"
        assert results[1]["url"] == "https://b.vn"
