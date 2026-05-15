"""Scheduler that runs periodic HTTP checks for each configured route."""

from __future__ import annotations

import threading
from typing import List, Optional

from routewatch.config import AppConfig, RouteConfig, WebhookConfig
from routewatch.checker import RouteChecker
from routewatch.alerter import build_payload, send_alert
from routewatch.circuit_breaker import CircuitBreaker
from routewatch.logging_config import get_logger

logger = get_logger(__name__)


class RouteScheduler:
    """Manages one timer thread per route, respecting circuit-breaker state."""

    def __init__(
        self,
        config: AppConfig,
        checker: Optional[RouteChecker] = None,
        breaker: Optional[CircuitBreaker] = None,
    ) -> None:
        self._config = config
        self._checker = checker or RouteChecker()
        self._breaker = breaker or CircuitBreaker(
            failure_threshold=config.circuit_breaker_threshold,
            recovery_timeout_s=config.circuit_breaker_recovery_s,
        )
        self._timers: List[threading.Timer] = []
        self._lock = threading.Lock()
        self._running = False

    def start(self) -> None:
        self._running = True
        for route in self._config.routes:
            self._schedule(route)
        logger.info("scheduler started with %d route(s)", len(self._config.routes))

    def stop(self) -> None:
        self._running = False
        with self._lock:
            for t in self._timers:
                t.cancel()
            self._timers.clear()
        logger.info("scheduler stopped")

    def _schedule(self, route: RouteConfig) -> None:
        if not self._running:
            return
        t = threading.Timer(route.interval_s, self._run_route, args=(route,))
        t.daemon = True
        with self._lock:
            self._timers.append(t)
        t.start()

    def _run_route(self, route: RouteConfig) -> None:
        route_id = f"{route.method} {route.url}"
        try:
            if self._breaker.is_open(route_id):
                logger.debug("circuit open — skipping %s", route_id)
                return

            result = self._checker.check(route)

            if result.ok:
                self._breaker.record_success(route_id)
            else:
                self._breaker.record_failure(route_id, result.error or str(result.status_code))
                for webhook in self._config.webhooks:
                    if self._should_alert(route, result):
                        payload = build_payload(result, webhook)
                        send_alert(payload, webhook)
        except Exception as exc:  # noqa: BLE001
            logger.exception("unexpected error checking %s: %s", route_id, exc)
        finally:
            self._schedule(route)

    def _should_alert(self, route: RouteConfig, result) -> bool:  # type: ignore[override]
        from routewatch.checker import is_alert
        return is_alert(result, route)
