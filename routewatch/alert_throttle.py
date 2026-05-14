"""Alert throttling to prevent repeated alerts for the same route."""

import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from routewatch.logging_config import get_logger

logger = get_logger(__name__)

_DEFAULT_COOLDOWN_SECONDS = 300  # 5 minutes


@dataclass
class ThrottleState:
    last_alert_at: float = 0.0
    alert_count: int = 0


class AlertThrottle:
    """Tracks per-route alert cooldowns to avoid flooding webhooks."""

    def __init__(self, cooldown_seconds: int = _DEFAULT_COOLDOWN_SECONDS) -> None:
        self.cooldown_seconds = cooldown_seconds
        self._states: Dict[str, ThrottleState] = {}

    def should_send(self, route_url: str) -> bool:
        """Return True if enough time has passed since the last alert for this route."""
        now = time.monotonic()
        state = self._states.get(route_url)

        if state is None:
            return True

        elapsed = now - state.last_alert_at
        if elapsed >= self.cooldown_seconds:
            return True

        logger.debug(
            "Alert throttled for %s (%.1fs remaining in cooldown)",
            route_url,
            self.cooldown_seconds - elapsed,
        )
        return False

    def record_sent(self, route_url: str) -> None:
        """Mark that an alert was just sent for the given route."""
        state = self._states.setdefault(route_url, ThrottleState())
        state.last_alert_at = time.monotonic()
        state.alert_count += 1
        logger.debug(
            "Alert recorded for %s (total=%d)", route_url, state.alert_count
        )

    def reset(self, route_url: str) -> None:
        """Clear throttle state for a route (e.g. when it recovers)."""
        if route_url in self._states:
            del self._states[route_url]
            logger.debug("Throttle state cleared for %s", route_url)

    def alert_count(self, route_url: str) -> int:
        """Return how many alerts have been sent for the given route."""
        state = self._states.get(route_url)
        return state.alert_count if state else 0

    def seconds_until_next(self, route_url: str) -> Optional[float]:
        """Return seconds remaining in cooldown, or None if not throttled."""
        state = self._states.get(route_url)
        if state is None:
            return None
        remaining = self.cooldown_seconds - (time.monotonic() - state.last_alert_at)
        return max(0.0, remaining) if remaining > 0 else None
