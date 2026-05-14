"""Periodic status reporter that logs a human-readable summary."""

import threading
from typing import Dict

from routewatch.metrics import MetricsCollector
from routewatch.history import LatencyHistory
from routewatch.status import build_status_report
from routewatch.logging_config import get_logger

logger = get_logger(__name__)


class StatusReporter:
    """Logs a periodic status summary for all monitored routes."""

    def __init__(
        self,
        metrics: MetricsCollector,
        history: LatencyHistory,
        route_urls: Dict[str, str],
        interval_seconds: float = 60.0,
        failure_threshold: int = 3,
    ) -> None:
        self._metrics = metrics
        self._history = history
        self._route_urls = route_urls
        self._interval = interval_seconds
        self._failure_threshold = failure_threshold
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="status-reporter")
        self._thread.start()
        logger.info("StatusReporter started (interval=%.1fs)", self._interval)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=self._interval + 2)
        logger.info("StatusReporter stopped")

    def _run(self) -> None:
        while not self._stop_event.wait(self._interval):
            self._report()

    def _report(self) -> None:
        report = build_status_report(
            self._metrics,
            self._history,
            self._route_urls,
            self._failure_threshold,
        )
        if report.total_routes == 0:
            logger.info("[status] No routes configured.")
            return

        overall = "OK" if report.all_healthy else "DEGRADED"
        logger.info(
            "[status] overall=%s healthy=%d/%d",
            overall,
            report.healthy_routes,
            report.total_routes,
        )
        for s in report.routes:
            health = "healthy" if s.is_healthy else "UNHEALTHY"
            logger.info(
                "[status] route=%s url=%s status=%s success_rate=%.1f%% avg_latency=%.2fms checks=%d",
                s.route_id,
                s.url,
                health,
                s.success_rate * 100,
                s.avg_latency_ms,
                s.total_checks,
            )
