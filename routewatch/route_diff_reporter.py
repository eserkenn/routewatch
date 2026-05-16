"""Periodically compares live route metrics against a baseline snapshot
and logs any routes whose average latency has regressed beyond a threshold."""

from __future__ import annotations

import threading
import time
from typing import Optional

from routewatch.logging_config import get_logger
from routewatch.metrics import MetricsCollector
from routewatch.history import LatencyHistory
from routewatch.route_snapshot import take_snapshot, diff_snapshots, RouteSnapshot

logger = get_logger(__name__)

_DEFAULT_INTERVAL_S = 60
_DEFAULT_REGRESSION_THRESHOLD_MS = 50.0


class RouteDiffReporter:
    """Background reporter that detects latency regressions vs a baseline."""

    def __init__(
        self,
        collector: MetricsCollector,
        history: LatencyHistory,
        interval_s: float = _DEFAULT_INTERVAL_S,
        regression_threshold_ms: float = _DEFAULT_REGRESSION_THRESHOLD_MS,
    ) -> None:
        self._collector = collector
        self._history = history
        self._interval_s = interval_s
        self._regression_threshold_ms = regression_threshold_ms
        self._baseline: Optional[RouteSnapshot] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        """Capture baseline and start the background diff thread."""
        self._baseline = take_snapshot(self._collector, self._history)
        logger.info("RouteDiffReporter started; baseline captured for %d route(s).",
                    len(self._baseline.routes))
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="route-diff-reporter")
        self._thread.start()

    def stop(self) -> None:
        """Stop the background thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("RouteDiffReporter stopped.")

    def _run(self) -> None:
        while not self._stop_event.wait(self._interval_s):
            self._report()

    def _report(self) -> None:
        if self._baseline is None:
            return
        current = take_snapshot(self._collector, self._history)
        diff = diff_snapshots(self._baseline, current)
        regressions = [
            entry for entry in diff.changed
            if entry.latency_delta_ms >= self._regression_threshold_ms
        ]
        if not regressions:
            logger.info("RouteDiffReporter: no latency regressions detected.")
            return
        for entry in regressions:
            logger.warning(
                "Latency regression on %s: +%.1f ms (baseline=%.1f ms, current=%.1f ms)",
                entry.url,
                entry.latency_delta_ms,
                entry.baseline_latency_ms,
                entry.current_latency_ms,
            )
