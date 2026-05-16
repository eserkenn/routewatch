"""Tests for routewatch.rate_limiter."""
from __future__ import annotations

import time

import pytest

from routewatch.rate_limiter import RateLimiter


@pytest.fixture()
def limiter() -> RateLimiter:
    # 2 tokens/sec, capacity 3
    return RateLimiter(rate=2.0, capacity=3.0)


def test_invalid_rate_raises():
    with pytest.raises(ValueError, match="rate"):
        RateLimiter(rate=0)


def test_invalid_capacity_raises():
    with pytest.raises(ValueError, match="capacity"):
        RateLimiter(rate=1.0, capacity=-1)


def test_first_acquire_allowed(limiter: RateLimiter):
    assert limiter.acquire("webhook-a") is True


def test_bucket_drains_to_zero(limiter: RateLimiter):
    key = "webhook-b"
    # capacity is 3, so first three calls succeed
    results = [limiter.acquire(key) for _ in range(3)]
    assert all(results)
    # fourth call should be denied
    assert limiter.acquire(key) is False


def test_independent_buckets(limiter: RateLimiter):
    for _ in range(3):
        limiter.acquire("a")
    # bucket "b" still full
    assert limiter.acquire("b") is True


def test_tokens_refill_over_time(monkeypatch):
    """Tokens should replenish after time passes."""
    clock = [0.0]

    def fake_monotonic():
        return clock[0]

    monkeypatch.setattr(time, "monotonic", fake_monotonic)

    lim = RateLimiter(rate=1.0, capacity=2.0)
    key = "w"
    lim.acquire(key)
    lim.acquire(key)  # drain
    assert lim.acquire(key) is False

    clock[0] += 1.5  # 1.5 tokens should refill
    assert lim.acquire(key) is True  # 1 token consumed
    assert lim.acquire(key) is False  # only 0.5 left


def test_available_tokens_reflects_capacity(limiter: RateLimiter):
    tokens = limiter.available_tokens("new-key")
    assert tokens == pytest.approx(3.0)


def test_available_tokens_decreases_after_acquire(limiter: RateLimiter):
    key = "c"
    limiter.acquire(key)
    assert limiter.available_tokens(key) == pytest.approx(2.0)


def test_reset_restores_full_bucket(limiter: RateLimiter):
    key = "d"
    for _ in range(3):
        limiter.acquire(key)
    assert limiter.acquire(key) is False
    limiter.reset(key)
    assert limiter.acquire(key) is True


def test_reset_unknown_key_is_noop(limiter: RateLimiter):
    limiter.reset("nonexistent")  # should not raise
