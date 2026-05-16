"""Captures and compares point-in-time snapshots of route metrics."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from routewatch.metrics import MetricsCollector
from routewatch.history import LatencyHistory


@dataclass
class RouteSnapshot:
    """Immutable snapshot of a single route at a point in time."""
    url: str
    timestamp: float
    success_rate: float
    failure_rate: float
    total_checks: int
    avg_latency_ms: float
    consecutive_failures: int


@dataclass
class SnapshotDiff:
    """Difference between two snapshots for the same route."""
    url: str
    success_rate_delta: float
    avg_latency_delta_ms: float
    consecutive_failures_delta: int
    elapsed_seconds: float
    degraded: bool = field(init=False)

    def __post_init__(self) -> None:
        self.degraded = (
            self.success_rate_delta < -0.05
            or self.avg_latency_delta_ms > 100.0
            or self.consecutive_failures_delta > 0
        )


def take_snapshot(
    collector: MetricsCollector,
    history: LatencyHistory,
    url: str,
) -> RouteSnapshot:
    """Capture a snapshot for a single route."""
    metrics = collector.get(url)
    latencies = history.get(url)
    avg_lat = sum(latencies) / len(latencies) if latencies else 0.0
    return RouteSnapshot(
        url=url,
        timestamp=time.time(),
        success_rate=metrics.success_rate,
        failure_rate=metrics.failure_rate,
        total_checks=metrics.total_checks,
        avg_latency_ms=avg_lat,
        consecutive_failures=metrics.consecutive_failures,
    )


def diff_snapshots(before: RouteSnapshot, after: RouteSnapshot) -> SnapshotDiff:
    """Compute the difference between two snapshots for the same route."""
    if before.url != after.url:
        raise ValueError(f"Cannot diff snapshots for different routes: {before.url!r} vs {after.url!r}")
    return SnapshotDiff(
        url=before.url,
        success_rate_delta=after.success_rate - before.success_rate,
        avg_latency_delta_ms=after.avg_latency_ms - before.avg_latency_ms,
        consecutive_failures_delta=after.consecutive_failures - before.consecutive_failures,
        elapsed_seconds=after.timestamp - before.timestamp,
    )


def take_all_snapshots(
    collector: MetricsCollector,
    history: LatencyHistory,
) -> Dict[str, RouteSnapshot]:
    """Capture snapshots for every tracked route."""
    return {
        url: take_snapshot(collector, history, url)
        for url in collector.all_urls()
    }
