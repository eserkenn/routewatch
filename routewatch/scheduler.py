"""Scheduler: periodically runs route checks and triggers alerts."""

import asyncio
import logging
from typing import Dict

from routewatch.alerter import build_payload, send_alert
from routewatch.checker import RouteChecker, is_alert
from routewatch.config import AppConfig, RouteConfig

logger = logging.getLogger(__name__)


class RouteScheduler:
    """Manages periodic checking of all configured routes."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._checkers: Dict[str, RouteChecker] = {
            route.name: RouteChecker(route) for route in config.routes
        }
        self._running = False

    async def _check_route(self, checker: RouteChecker) -> None:
        """Run a single route check and send alert if needed."""
        result = await checker.check()
        logger.debug(
            "Checked %s: ok=%s latency=%.1fms",
            result.route_name,
            result.ok,
            result.latency_ms,
        )
        if is_alert(result, checker.route):
            for webhook in self.config.webhooks:
                payload = build_payload(result, webhook)
                await send_alert(payload, webhook)
                logger.info(
                    "Alert sent for %s to %s", result.route_name, webhook.url
                )

    async def _run_route_loop(self, checker: RouteChecker) -> None:
        """Continuously check a route at its configured interval."""
        interval = checker.route.interval_seconds
        while self._running:
            try:
                await self._check_route(checker)
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("Unexpected error checking %s: %s", checker.route.name, exc)
            await asyncio.sleep(interval)

    async def run(self) -> None:
        """Start all route check loops concurrently."""
        self._running = True
        logger.info("Scheduler starting with %d route(s).", len(self._checkers))
        tasks = [
            asyncio.create_task(self._run_route_loop(checker))
            for checker in self._checkers.values()
        ]
        try:
            await asyncio.gather(*tasks)
        finally:
            self._running = False

    def stop(self) -> None:
        """Signal all loops to stop after their current sleep."""
        logger.info("Scheduler stopping.")
        self._running = False
