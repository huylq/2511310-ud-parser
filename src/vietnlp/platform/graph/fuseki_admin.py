"""Fuseki dataset provisioning, via its HTTP admin API.

Not exercised against a live server in P0: Fuseki sits behind the `graph`
compose profile and is not needed until P3 (spec S10). This module exists
now so P3 has a tested primitive to call rather than starting from a shell
script written under deadline.
"""

from __future__ import annotations

import httpx


class FusekiError(RuntimeError):
    pass


def dataset_exists(base_url: str, name: str, *, auth: tuple[str, str] | None = None) -> bool:
    resp = httpx.get(f"{base_url}/$/datasets/{name}", auth=auth, timeout=10.0)
    if resp.status_code == 200:
        return True
    if resp.status_code == 404:
        return False
    raise FusekiError(f"unexpected status checking dataset {name!r}: {resp.status_code}")


def create_dataset(base_url: str, name: str, *, auth: tuple[str, str] | None = None) -> None:
    """Idempotent: a dataset that already exists is left untouched."""
    if dataset_exists(base_url, name, auth=auth):
        return
    resp = httpx.post(
        f"{base_url}/$/datasets", data={"dbName": name, "dbType": "tdb2"}, auth=auth, timeout=10.0,
    )
    if resp.status_code not in (200, 201):
        raise FusekiError(f"failed to create dataset {name!r}: {resp.status_code} {resp.text[:300]}")
