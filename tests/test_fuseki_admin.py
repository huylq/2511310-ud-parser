"""Fuseki's admin HTTP API, entirely offline via respx -- no live Fuseki
required. The `graph` compose profile stays off until P3 needs it (spec S10);
this only makes sure the primitive P3 will call is already correct."""
import httpx
import pytest
import respx

from vietnlp.platform.graph.fuseki_admin import FusekiError, create_dataset, dataset_exists

BASE = "http://fuseki.test:3030"


@respx.mock
def test_dataset_exists_true_on_200():
    respx.get(f"{BASE}/$/datasets/vietnlp").mock(return_value=httpx.Response(200, json={}))
    assert dataset_exists(BASE, "vietnlp") is True


@respx.mock
def test_dataset_exists_false_on_404():
    respx.get(f"{BASE}/$/datasets/vietnlp").mock(return_value=httpx.Response(404))
    assert dataset_exists(BASE, "vietnlp") is False


@respx.mock
def test_dataset_exists_raises_on_unexpected_status():
    respx.get(f"{BASE}/$/datasets/vietnlp").mock(return_value=httpx.Response(500))
    with pytest.raises(FusekiError, match="unexpected status"):
        dataset_exists(BASE, "vietnlp")


@respx.mock
def test_create_dataset_posts_tdb2_when_absent():
    respx.get(f"{BASE}/$/datasets/vietnlp").mock(return_value=httpx.Response(404))
    create = respx.post(f"{BASE}/$/datasets").mock(return_value=httpx.Response(200))
    create_dataset(BASE, "vietnlp")
    assert create.called
    sent = create.calls.last.request.content.decode()
    assert "dbName=vietnlp" in sent and "dbType=tdb2" in sent


@respx.mock
def test_create_dataset_is_idempotent_when_already_present():
    respx.get(f"{BASE}/$/datasets/vietnlp").mock(return_value=httpx.Response(200, json={}))
    create = respx.post(f"{BASE}/$/datasets").mock(return_value=httpx.Response(200))
    create_dataset(BASE, "vietnlp")
    assert not create.called, "must not re-create an existing dataset"
