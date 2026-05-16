"""Token-bucket rate limiter for outbound webhook calls."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class BucketState:
    tokens: float
    last_refill: float = field(default_factory=time.monotonic)


class RateLimiter:
    """Per-webhook token-bucket rate limiter.

    Args:
        rate:     tokens replenished per second.
        capacity: maximum tokens the bucket can hold.
    """

    def __init__(self, rate: float = 1.0, capacity: float = 5.0) -> None:
        if rate <= 0:
            raise ValueError("rate must be positive")
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self._rate = rate
        self._capacity = capacity
        self._buckets: Dict[str, BucketState] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    def _refill(self, state: BucketState, now: float) -> None:
        elapsed = now - state.last_refill
        state.tokens = min(self._capacity, state.tokens + elapsed * self._rate)
        state.last_refill = now

    def _get_bucket(self, key: str) -> BucketState:
        if key not in self._buckets:
            self._buckets[key] = BucketState(tokens=self._capacity)
        return self._buckets[key]

    # ------------------------------------------------------------------
    def acquire(self, key: str) -> bool:
        """Attempt to consume one token for *key*.

        Returns True if the call is allowed, False if rate-limited.
        """
        with self._lock:
            now = time.monotonic()
            bucket = self._get_bucket(key)
            self._refill(bucket, now)
            if bucket.tokens >= 1.0:
                bucket.tokens -= 1.0
                return True
            return False

    def available_tokens(self, key: str) -> float:
        """Return current token count for *key* (after refill)."""
        with self._lock:
            now = time.monotonic()
            bucket = self._get_bucket(key)
            self._refill(bucket, now)
            return bucket.tokens

    def reset(self, key: str) -> None:
        """Remove bucket state for *key*."""
        with self._lock:
            self._buckets.pop(key, None)
