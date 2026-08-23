"""The one place that calls DeepSeek and the one place that spends money.

Call order is deliberate and must not be rearranged:

    cache lookup  ->  budget check  ->  API call  ->  record spend  ->  cache store

Cache before budget, so a cache hit costs nothing and cannot be blocked by a cap.
Budget before the call, so a refused call is never billed. Record before caching, so
a crash between the two loses a cache entry (cheap) and never loses a spend record
(expensive -- it would under-report spend and let the next run overshoot the cap).
"""

from __future__ import annotations

import json
import logging
import os
import random
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from .budget import BudgetLedger
from .cache import ResponseCache, cache_key
from .policy import Model, Route, route

log = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.deepseek.com"
_RETRYABLE = frozenset({429, 500, 502, 503, 504})


class DeepSeekError(RuntimeError):
    pass


@dataclass
class Result:
    content: str
    model: str
    task: str
    cached: bool
    usd: float
    input_tokens: int = 0
    cached_tokens: int = 0
    output_tokens: int = 0

    def json(self):
        """Parse the response as JSON, tolerating a ```json fence."""
        text = self.content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text
            text = text.rsplit("```", 1)[0]
        return json.loads(text)


def _read_api_key() -> str:
    """Env first, then the gitignored key file. Never logged, never returned in errors."""
    key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if key:
        return key
    for candidate in (os.getenv("DEEPSEEK_KEY_FILE"), "/run/secrets/deepseek_key", "deepseek.key"):
        if candidate and Path(candidate).is_file():
            key = Path(candidate).read_text(encoding="utf-8").strip()
            if key:
                return key
    raise DeepSeekError(
        "No DeepSeek API key. Set DEEPSEEK_API_KEY or provide deepseek.key. "
        "(The key value is never logged.)"
    )


@dataclass
class AgentClient:
    """Routed, cached, budget-capped DeepSeek access."""

    flow_run_id: str
    ledger: BudgetLedger = field(default_factory=BudgetLedger)
    cache: ResponseCache = field(default_factory=ResponseCache)
    base_url: str = field(default_factory=lambda: os.getenv("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL))
    max_retries: int = 5
    timeout: float = 120.0
    _client: httpx.Client | None = field(default=None, repr=False)

    def _http(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={
                    "Authorization": f"Bearer {_read_api_key()}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def run(
        self,
        task: str,
        system_prompt: str,
        user_content: str,
        *,
        prompt_version: str,
        json_mode: bool = False,
        force_refresh: bool = False,
    ) -> Result:
        r: Route = route(task)  # unknown task raises; there is no default model

        key = cache_key(task, prompt_version, r.model.value, system_prompt + "\x00" + user_content)
        if r.cacheable and not force_refresh:
            hit = self.cache.get(key)
            if hit is not None:
                log.debug("cache hit task=%s", task)
                return Result(content=hit, model=r.model.value, task=task, cached=True, usd=0.0)

        est_input = _estimate_tokens(system_prompt) + _estimate_tokens(user_content)
        self.ledger.check_affordable(self.flow_run_id, r.model, est_input, r.max_output_tokens)

        payload = {
            "model": r.model.value,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "max_tokens": r.max_output_tokens,
            "stream": False,
        }
        # deepseek-reasoner rejects temperature; it is fixed by the model.
        if r.model is not Model.REASONER:
            payload["temperature"] = r.temperature
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        data = self._post_with_retry("/chat/completions", payload)

        choice = data["choices"][0]
        content = choice["message"]["content"]
        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", est_input)
        cached_tokens = usage.get("prompt_cache_hit_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        usd = self.ledger.record(
            flow_run_id=self.flow_run_id,
            task=task,
            model=r.model,
            input_tokens=input_tokens,
            cached_tokens=cached_tokens,
            output_tokens=output_tokens,
        )

        if r.cacheable:
            self.cache.put(key, task, r.model.value, prompt_version, content)

        return Result(
            content=content,
            model=r.model.value,
            task=task,
            cached=False,
            usd=usd,
            input_tokens=input_tokens,
            cached_tokens=cached_tokens,
            output_tokens=output_tokens,
        )

    def _post_with_retry(self, path: str, payload: dict) -> dict:
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                resp = self._http().post(path, json=payload)
            except httpx.RequestError as exc:
                last_error = exc
            else:
                if resp.status_code == 200:
                    return resp.json()
                if resp.status_code not in _RETRYABLE:
                    # 4xx other than 429: retrying cannot help. Surface it without
                    # echoing headers, which carry the Authorization bearer token.
                    raise DeepSeekError(
                        f"DeepSeek returned {resp.status_code}: {resp.text[:500]}"
                    )
                last_error = DeepSeekError(f"HTTP {resp.status_code}")

            if attempt < self.max_retries - 1:
                backoff = min(2**attempt, 30) + random.uniform(0, 1)
                log.warning("retry %d/%d in %.1fs: %s", attempt + 1, self.max_retries, backoff, last_error)
                time.sleep(backoff)

        raise DeepSeekError(f"exhausted {self.max_retries} retries: {last_error}")


def _estimate_tokens(text: str) -> int:
    """Pre-call token estimate for the budget gate.

    Vietnamese is diacritic-dense and tokenizes worse than English -- roughly 2.5
    characters per token against English's ~4. Deliberately conservative: an
    over-estimate stops a flow early, an under-estimate overshoots the cap.
    """
    return max(1, int(len(text) / 2.5))
