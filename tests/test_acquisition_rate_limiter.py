"""Pure logic, deterministic clock/sleep injection -- no real waiting in tests."""
import pytest

from vietnlp.acquisition.rate_limiter import TokenBucket


def _fail_if_called(*_args, **_kwargs):
    raise AssertionError("should not have slept")


def test_first_acquire_does_not_wait():
    bucket = TokenBucket(rate_limit_seconds=5.0)
    waited = bucket.acquire(_sleep=_fail_if_called, _now=lambda: 100.0)
    assert waited == 0.0


def test_second_acquire_within_interval_waits_the_remainder():
    bucket = TokenBucket(rate_limit_seconds=5.0)
    clock = iter([100.0, 102.0])
    sleeps = []
    bucket.acquire(_now=lambda: next(clock), _sleep=_fail_if_called)
    waited = bucket.acquire(_now=lambda: next(clock), _sleep=sleeps.append)
    assert waited == 3.0
    assert sleeps == [3.0]


def test_acquire_after_interval_elapsed_does_not_wait():
    bucket = TokenBucket(rate_limit_seconds=5.0)
    clock = iter([100.0, 106.0])
    bucket.acquire(_now=lambda: next(clock), _sleep=_fail_if_called)
    waited = bucket.acquire(_now=lambda: next(clock), _sleep=_fail_if_called)
    assert waited == 0.0
