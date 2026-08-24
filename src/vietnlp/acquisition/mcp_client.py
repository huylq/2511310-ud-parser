"""Thin synchronous wrapper around z.ai's web-search-prime and web-reader
MCP tools, called directly over MCP's Streamable HTTP transport. This runs
as unattended Python in a Prefect flow -- there is no Claude Code MCP
runtime available here -- so it speaks the MCP protocol itself via the
official `mcp` SDK, the same way platform/agents/client.py speaks
DeepSeek's HTTP API directly rather than through any wrapper.
"""

from __future__ import annotations

import asyncio
import json
import os

import httpx

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

_SEARCH_URL = "https://api.z.ai/api/mcp/web_search_prime/mcp"
_READER_URL = "https://api.z.ai/api/mcp/web_reader/mcp"
_API_KEY_ENV = "ZAI_API_KEY"


class MCPError(RuntimeError):
    pass


def _api_key() -> str:
    key = os.getenv(_API_KEY_ENV, "").strip()
    if not key:
        raise MCPError(f"{_API_KEY_ENV} not set. (Value is never logged.)")
    return key


async def _call_tool(url: str, tool_name: str, arguments: dict) -> list[str]:
    headers = {"Authorization": f"Bearer {_api_key()}"}
    http_client = httpx.AsyncClient(headers=headers)
    async with streamable_http_client(url, http_client=http_client) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            if result.is_error:
                raise MCPError(f"{tool_name} returned an error: {result.content}")
            # MCP tool results are a list of content blocks; text-typed
            # blocks carry `.text` (per the MCP spec). Non-text block types
            # are not expected from either of these two tools.
            texts = [block.text for block in result.content if hasattr(block, "text")]
            if not texts:
                raise MCPError(f"{tool_name} returned no text content: {result.content!r}")
            return texts


def web_search(query: str, count: int = 10) -> list[dict]:
    """Discover candidate URLs for a query. Returns a list of dicts, each
    with at least a `url` key.

    Empirically verified 2026-08-25 against live z.ai server:
    - Tool parameter is 'search_query' not 'query'
    - Result is double-JSON-encoded (parse twice)
    - Result keys are 'link' (not 'url'), 'title', 'content', 'refer'
    - Normalizes 'link' to 'url' for API contract"""
    texts = asyncio.run(_call_tool(_SEARCH_URL, "web_search_prime", {"search_query": query, "count": count}))
    combined = "\n".join(texts)
    try:
        parsed = json.loads(combined)
    except json.JSONDecodeError as exc:
        raise MCPError(
            f"web_search_prime result was not JSON as expected: {exc}. "
            f"Raw text (first 500 chars): {combined[:500]!r}"
        ) from exc

    # Handle double JSON encoding: if result is a string, parse again
    if isinstance(parsed, str):
        try:
            parsed = json.loads(parsed)
        except json.JSONDecodeError as exc:
            raise MCPError(
                f"web_search_prime double-encoded result could not be parsed: {exc}. "
                f"Raw text (first 500 chars): {combined[:500]!r}"
            ) from exc

    results = parsed if isinstance(parsed, list) else parsed.get("results", [])

    # Normalize keys: 'link' -> 'url' for API contract
    normalized = []
    for result in results:
        if isinstance(result, dict):
            normalized_result = result.copy()
            if "link" in normalized_result and "url" not in normalized_result:
                normalized_result["url"] = normalized_result.pop("link")
            normalized.append(normalized_result)

    return normalized


def web_read(url: str) -> str:
    """Extract clean text from one URL."""
    texts = asyncio.run(_call_tool(_READER_URL, "webReader", {"url": url}))
    return "\n".join(texts)
