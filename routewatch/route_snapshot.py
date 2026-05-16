"""Snapshot utilities: capture a point-in-time view of all route metrics
and compute a diff between two snapshots to surface regressions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from routewatch.metrics import MetricsCollector
from routewatch.history import LatencyHistory


@dataclass
class SnapshotEntry:
    url: str
    avg_latency_ms: float
    success_rate: float
    failure_count: int


@dataclass
class RouteSnapshot:
    routes: List[SnapshotEntry] = field(default_factory=list)

    def _by_url(self) -> Dict[str, SnapshotEntry]:
        return {e.url: e for e in self.routes}


@dataclass
class DiffEntry:
    url: str
    baseline_latency_ms: float
    current_latency_ms: float
    latency_delta_ms: float

    def __post_init__(self) -> None:
        self.latency_delta_ms = self.current_latency_ms - self.baseline_latency_ms


@dataclass
class SnapshotDiff:
    changed: List[DiffEntry] = field(default_factory=list)
    added: List[SnapshotEntry] = field(default_factory=list)
    removed: List[SnapshotEntry] = field(default_factory=list)


def take_snapshot(collector: MetricsCollector, history: LatencyHistory) -> RouteSnapshot:
    """Build a RouteSnapshot from current collector metrics and latency history."""
    entries: List[SnapshotEntry] = []
    for url, metrics in collector.all().items():
        samples = history.get(url)
        avg = sum(samples) / len(samples) if samples else 0.0
        entries.append(
            SnapshotEntry(
                url=url,
                avg_latency_ms=round(avg, 3),
                success_rate=metrics.success_rate,
                failure_count=metrics.consecutive_failures,
            )
        )
    return RouteSnapshot(routes=entries)


def diff_snapshots(baseline: RouteSnapshot, current: RouteSnapshot) -> SnapshotDiff:
    """Compare two snapshots and return added, removed, and changed routes."""
    base_map = baseline._by_url()
    curr_map = current._by_url()

    added = [curr_map[url] for url in curr_map if url not in base_map]
    removed = [base_map[url] for url in base_map if url not in curr_map]
    changed: List[DiffEntry] = []

    for url in base_map:
        if url not in curr_map:
            continue
        b = base_map[url]
        c = curr_map[url]
        if c.avg_latency_ms != b.avg_latency_ms:
            changed.append(
                DiffEntry(
                    url=url,
                    baseline_latency_ms=b.avg_latency_ms,
                    current_latency_ms=c.avg_latency_ms,
                    latency_delta_ms=c.avg_latency_ms - b.avg_latency_ms,
                )
            )

    return SnapshotDiff(changed=changed, added=added, removed=removed)
