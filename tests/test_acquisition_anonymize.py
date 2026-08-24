"""CLAUDE.md: hash author identifiers at ingest, never persist raw handles."""
from vietnlp.acquisition.anonymize import hash_author_id


def test_hash_is_stable_for_identical_input(monkeypatch):
    monkeypatch.setenv("VIETNLP_AUTHOR_HASH_SALT", "test-salt")
    assert hash_author_id("nguyen_van_a") == hash_author_id("nguyen_van_a")


def test_hash_differs_for_different_input(monkeypatch):
    monkeypatch.setenv("VIETNLP_AUTHOR_HASH_SALT", "test-salt")
    assert hash_author_id("user_one") != hash_author_id("user_two")


def test_hash_is_sha256_hex_length(monkeypatch):
    monkeypatch.setenv("VIETNLP_AUTHOR_HASH_SALT", "test-salt")
    assert len(hash_author_id("someone")) == 64


def test_hash_changes_with_different_salt(monkeypatch):
    monkeypatch.setenv("VIETNLP_AUTHOR_HASH_SALT", "salt-a")
    h1 = hash_author_id("same_user")
    monkeypatch.setenv("VIETNLP_AUTHOR_HASH_SALT", "salt-b")
    h2 = hash_author_id("same_user")
    assert h1 != h2
