"""Route scheduler — runs periodic checks and fires alerts."""

import threading
from typing import List, Optional

from routewatch.alerter import build_payload, send_alert
from routewatch.checker import RouteChecker, is_alert
from routewatch.config import AppConfig, RouteConfig, WebhookConfig
from routewatch.history import LatencyHistory
from routewatch.logging_config import get_logger
from routewatch.metrics import get_collector
from routewatch.metrics_reporter import MetricsReporter

logger = get_logger(__name__)


class RouteScheduler:
    """Schedules periodic HTTP checks for all configured routes."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._threads: List[threading.Thread] = []
        self._stop_events: List[threading.Event] = []
        self._history = LatencyHistory()
        self._collector = get_collector()
        self._reporter = MetricsReporter(
            interval_seconds=config.metrics_interval_seconds,
            collector=self._collector,
        )

    def start(self) -> None:
        logger.info("Starting scheduler for %d route(s)", len(self._config.routes))
        for route in self._config.routes:
            stop_event = threading.Event()
            self._stop_events.append(stop_event)
            thread = threading.Thread(
                target=self._run_route,
                args=(route, stop_event),
                name=f"checker-{route.url}",
                daemon=True,
            )
            self._threads.append(thread)
            thread.start()
        self._reporter.start()

    def stop(self) -> None:
        logger.info("Stopping scheduler...")
        for ev in self._stop_events:
            ev.set()
        for t in self._threads:
            t.join(timeout=10)
        self._reporter.stop()
        logger.info("Scheduler stopped")

    def _run_route(
        self, route: RouteConfig, stop_event: threading.Event
    ) -> None:
        checker = RouteChecker(route, self._history)
        while not stop_event.wait(route.interval_seconds):
            result = checker.check()
            alerted = False
            if is_alert(result):
                for webhook in self._config.webhooks:
                    payload = build_payload(result, webhook)
                    send_alert(payload, webhook)
                alerted = True
            self._collector.record_check(
                route.url,
                success=result.error is None and result.status_code == route.expected_status,
                alerted=alerted,
            )
