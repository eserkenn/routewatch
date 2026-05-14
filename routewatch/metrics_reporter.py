"""Periodic reporter that logs a summary of collected metrics."""

import threading
from typing import Optional

from routewatch.logging_config import get_logger
from routewatch.metrics import MetricsCollector, get_collector

logger = get_logger(__name__)


class MetricsReporter:
    """Logs per-route metrics on a fixed interval."""

    def __init__(
        self,
        interval_seconds: int = 60,
        collector: Optional[MetricsCollector] = None,
    ) -> None:
        self._interval = interval_seconds
        self._collector = collector or get_collector()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._run, name="metrics-reporter", daemon=True
        )
        self._thread.start()
        logger.info("MetricsReporter started (interval=%ds)", self._interval)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("MetricsReporter stopped")

    def _run(self) -> None:
        while not self._stop_event.wait(self._interval):
            self._report()

    def _report(self) -> None:
        all_metrics = self._collector.all()
        if not all_metrics:
            logger.info("[metrics] No routes tracked yet.")
            return
        for route_id, m in all_metrics.items():
            logger.info(
                "[metrics] route=%s total=%d ok=%d fail=%d alerts=%d "
                "success_rate=%.1f%% consec_fail=%d",
                route_id,
                m.total_checks,
                m.successful_checks,
                m.failed_checks,
                m.alert_count,
                m.success_rate * 100,
                m.consecutive_failures,
            )
