"""Token-bucket rate limiting, one bucket per source.

Politeness is structural, not advisory: acquire() blocks until a request is
allowed, so a caller cannot outrun the vetted rate_limit_seconds by mistake.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class TokenBucket:
    rate_limit_seconds: float
    _last_request_at: float | None = field(default=None, repr=False)

    def acquire(self, *, _sleep=time.sleep, _now=time.monotonic) -> float:
        """Block until a request is allowed. Returns the actual wait (seconds)."""
        now = _now()
        waited = 0.0
        if self._last_request_at is not None:
            elapsed = now - self._last_request_at
            waited = max(0.0, self.rate_limit_seconds - elapsed)
            if waited > 0:
                _sleep(waited)
        self._last_request_at = now + waited
        return waited
