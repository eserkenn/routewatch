"""Circuit breaker to stop checking routes that are repeatedly failing."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict
import time

from routewatch.logging_config import get_logger

logger = get_logger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Route is failing; checks suspended
    HALF_OPEN = "half_open"  # Probe check allowed


@dataclass
class BreakerState:
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    opened_at: float = 0.0
    last_failure_reason: str = ""


class CircuitBreaker:
    """Tracks per-route circuit state based on consecutive failures."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout_s: float = 60.0,
    ) -> None:
        self._threshold = failure_threshold
        self._recovery_timeout = recovery_timeout_s
        self._states: Dict[str, BreakerState] = {}

    def _get(self, route_id: str) -> BreakerState:
        if route_id not in self._states:
            self._states[route_id] = BreakerState()
        return self._states[route_id]

    def is_open(self, route_id: str) -> bool:
        """Return True when the route should NOT be checked."""
        s = self._get(route_id)
        if s.state == CircuitState.OPEN:
            if time.monotonic() - s.opened_at >= self._recovery_timeout:
                logger.info("circuit half-open for %s", route_id)
                s.state = CircuitState.HALF_OPEN
                return False
            return True
        return False

    def record_success(self, route_id: str) -> None:
        """Reset the breaker on a successful check."""
        s = self._get(route_id)
        if s.state != CircuitState.CLOSED:
            logger.info("circuit closed for %s", route_id)
        s.state = CircuitState.CLOSED
        s.failure_count = 0
        s.last_failure_reason = ""

    def record_failure(self, route_id: str, reason: str = "") -> None:
        """Increment failure count and open the circuit if threshold is reached."""
        s = self._get(route_id)
        s.failure_count += 1
        s.last_failure_reason = reason
        if s.failure_count >= self._threshold and s.state != CircuitState.OPEN:
            logger.warning(
                "circuit opened for %s after %d failures: %s",
                route_id, s.failure_count, reason,
            )
            s.state = CircuitState.OPEN
            s.opened_at = time.monotonic()

    def state_of(self, route_id: str) -> CircuitState:
        return self._get(route_id).state

    def failure_count(self, route_id: str) -> int:
        return self._get(route_id).failure_count
