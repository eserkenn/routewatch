"""In-memory metrics collector for route check statistics."""

from dataclasses import dataclass, field
from threading import Lock
from typing import Dict

from routewatch.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class RouteMetrics:
    total_checks: int = 0
    successful_checks: int = 0
    failed_checks: int = 0
    alert_count: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0

    @property
    def success_rate(self) -> float:
        if self.total_checks == 0:
            return 0.0
        return self.successful_checks / self.total_checks

    @property
    def failure_rate(self) -> float:
        if self.total_checks == 0:
            return 0.0
        return self.failed_checks / self.total_checks


class MetricsCollector:
    """Thread-safe collector for per-route check metrics."""

    def __init__(self) -> None:
        self._metrics: Dict[str, RouteMetrics] = {}
        self._lock = Lock()

    def _get_or_create(self, route_id: str) -> RouteMetrics:
        if route_id not in self._metrics:
            self._metrics[route_id] = RouteMetrics()
        return self._metrics[route_id]

    def record_check(self, route_id: str, success: bool, alerted: bool = False) -> None:
        with self._lock:
            m = self._get_or_create(route_id)
            m.total_checks += 1
            if success:
                m.successful_checks += 1
                m.consecutive_successes += 1
                m.consecutive_failures = 0
            else:
                m.failed_checks += 1
                m.consecutive_failures += 1
                m.consecutive_successes = 0
            if alerted:
                m.alert_count += 1
            logger.debug(
                "Metrics updated for %s: total=%d success=%d failed=%d",
                route_id, m.total_checks, m.successful_checks, m.failed_checks,
            )

    def get(self, route_id: str) -> RouteMetrics:
        with self._lock:
            return self._get_or_create(route_id)

    def all(self) -> Dict[str, RouteMetrics]:
        with self._lock:
            return dict(self._metrics)

    def reset(self, route_id: str) -> None:
        with self._lock:
            self._metrics.pop(route_id, None)

    def reset_all(self) -> None:
        with self._lock:
            self._metrics.clear()


_collector = MetricsCollector()


def get_collector() -> MetricsCollector:
    """Return the global MetricsCollector singleton."""
    return _collector
