"""Retry policy for HTTP checks — defines backoff behaviour on transient failures."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from routewatch.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class RetryPolicy:
    """Configures how many times a failing check is retried and how long to wait."""

    max_retries: int = 2
    base_delay_s: float = 0.5
    backoff_factor: float = 2.0
    max_delay_s: float = 10.0

    def delay_for(self, attempt: int) -> float:
        """Return the sleep duration (seconds) before *attempt* (0-indexed)."""
        if attempt == 0:
            return 0.0
        delay = self.base_delay_s * (self.backoff_factor ** (attempt - 1))
        return min(delay, self.max_delay_s)


def with_retry(
    fn: Callable[[], object],
    policy: RetryPolicy,
    *,
    route_url: str = "",
    _sleep: Callable[[float], None] = time.sleep,
) -> object:
    """Call *fn* up to ``policy.max_retries + 1`` times, sleeping between attempts.

    Returns the first successful result.  Re-raises the last exception when all
    attempts are exhausted.
    """
    last_exc: Exception | None = None
    total_attempts = policy.max_retries + 1

    for attempt in range(total_attempts):
        delay = policy.delay_for(attempt)
        if delay > 0:
            logger.debug(
                "retry attempt %d/%d for %s — waiting %.2fs",
                attempt,
                policy.max_retries,
                route_url or "<unknown>",
                delay,
            )
            _sleep(delay)

        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning(
                "attempt %d/%d failed for %s: %s",
                attempt + 1,
                total_attempts,
                route_url or "<unknown>",
                exc,
            )

    raise last_exc  # type: ignore[misc]
