"""Author-identifier hashing (CLAUDE.md: hash at ingest, never persist raw
handles). The salt lives in the environment, never in code or logs -- same
secrecy discipline as the DeepSeek API key in platform/agents/client.py.
"""

from __future__ import annotations

import hashlib
import os

_SALT_ENV = "VIETNLP_AUTHOR_HASH_SALT"


class AnonymizeError(RuntimeError):
    """Raised when author-identifier hashing cannot proceed safely."""

    pass


def hash_author_id(raw: str) -> str:
    """SHA-256 of the raw handle, salted so the hash cannot be reversed by
    dictionary-matching against a list of known usernames."""
    salt = os.getenv(_SALT_ENV, "")
    if not salt:
        raise AnonymizeError(
            f"{_SALT_ENV} not set or empty; refusing to hash without a salt "
            "(would produce a reversible hash)"
        )
    return hashlib.sha256((salt + raw).encode("utf-8")).hexdigest()
