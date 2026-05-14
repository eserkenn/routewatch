"""Aggregated status summary for all monitored routes."""

from dataclasses import dataclass, field
from typing import Dict, List

from routewatch.metrics import MetricsCollector, RouteMetrics
from routewatch.history import LatencyHistory
from routewatch.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class RouteSummary:
    route_id: str
    url: str
    success_rate: float
    failure_rate: float
    avg_latency_ms: float
    consecutive_failures: int
    total_checks: int
    is_healthy: bool


@dataclass
class StatusReport:
    total_routes: int
    healthy_routes: int
    unhealthy_routes: int
    routes: List[RouteSummary] = field(default_factory=list)

    @property
    def all_healthy(self) -> bool:
        return self.unhealthy_routes == 0


def build_status_report(
    metrics: MetricsCollector,
    history: LatencyHistory,
    route_urls: Dict[str, str],
    failure_threshold: int = 3,
) -> StatusReport:
    """Build a StatusReport from current metrics and latency history."""
    summaries: List[RouteSummary] = []

    for route_id, url in route_urls.items():
        m: RouteMetrics = metrics.get(route_id)
        latencies = history.get(route_id)
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        is_healthy = m.consecutive_failures < failure_threshold

        summaries.append(
            RouteSummary(
                route_id=route_id,
                url=url,
                success_rate=m.success_rate,
                failure_rate=m.failure_rate,
                avg_latency_ms=round(avg_latency, 2),
                consecutive_failures=m.consecutive_failures,
                total_checks=m.total_checks,
                is_healthy=is_healthy,
            )
        )

    healthy = sum(1 for s in summaries if s.is_healthy)
    return StatusReport(
        total_routes=len(summaries),
        healthy_routes=healthy,
        unhealthy_routes=len(summaries) - healthy,
        routes=summaries,
    )
