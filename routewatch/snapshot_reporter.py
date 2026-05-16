"""Periodically logs snapshot diffs to detect latency regressions."""
from __future__ import annotations

import threading
from typing import Dict, Optional

from routewatch.metrics import MetricsCollector
from routewatch.history import LatencyHistory
from routewatch.route_snapshot import (
    RouteSnapshot,
    take_all_snapshots,
    diff_snapshots,
)
from routewatch.logging_config import get_logger

logger = get_logger(__name__)


class SnapshotReporter:
    """Runs a background thread that diffs consecutive snapshots and logs regressions."""

    def __init__(
        self,
        collector: MetricsCollector,
        history: LatencyHistory,
        interval: float = 60.0,
    ) -> None:
        self._collector = collector
        self._history = history
        self._interval = interval
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._previous: Dict[str, RouteSnapshot] = {}

    def start(self) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="snapshot-reporter")
        self._thread.start()
        logger.info("SnapshotReporter started (interval=%.1fs)", self._interval)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5.0)
        logger.info("SnapshotReporter stopped")

    def _run(self) -> None:
        while not self._stop_event.wait(self._interval):
            self._report()

    def _report(self) -> None:
        current = take_all_snapshots(self._collector, self._history)
        if not current:
            logger.debug("SnapshotReporter: no routes to snapshot")
            return

        for url, snap in current.items():
            prev = self._previous.get(url)
            if prev is None:
                logger.debug("snapshot baseline captured for %s", url)
            else:
                diff = diff_snapshots(prev, snap)
                if diff.degraded:
                    logger.warning(
                        "regression detected url=%s success_rate_delta=%.3f "
                        "latency_delta_ms=%.1f consecutive_failures_delta=%d",
                        url,
                        diff.success_rate_delta,
                        diff.avg_latency_delta_ms,
                        diff.consecutive_failures_delta,
                    )
                else:
                    logger.debug("snapshot ok for %s", url)

        self._previous = current
