"""HTTP route checker that measures latency and detects regressions."""

import time
import logging
from dataclasses import dataclass, field
from typing import Optional

import httpx

from routewatch.config import RouteConfig

logger = logging.getLogger(__name__)


@dataclass
class CheckResult:
    route: str
    url: str
    status_code: Optional[int]
    latency_ms: Optional[float]
    success: bool
    error: Optional[str] = None
    threshold_exceeded: bool = False

    @property
    def is_alert(self) -> bool:
        return not self.success or self.threshold_exceeded


@dataclass
class RouteChecker:
    config: RouteConfig
    _history: list[float] = field(default_factory=list, init=False)

    def check(self) -> CheckResult:
        """Perform a single HTTP check against the configured route."""
        start = time.monotonic()
        try:
            response = httpx.request(
                method=self.config.method,
                url=self.config.url,
                timeout=self.config.timeout_seconds,
                follow_redirects=True,
            )
            latency_ms = (time.monotonic() - start) * 1000
            success = response.status_code == self.config.expected_status

            threshold_exceeded = (
                latency_ms > self.config.latency_threshold_ms
                if self.config.latency_threshold_ms is not None
                else False
            )

            self._history.append(latency_ms)
            if len(self._history) > 100:
                self._history.pop(0)

            result = CheckResult(
                route=self.config.name,
                url=self.config.url,
                status_code=response.status_code,
                latency_ms=round(latency_ms, 2),
                success=success,
                threshold_exceeded=threshold_exceeded,
                error=None if success else f"Expected {self.config.expected_status}, got {response.status_code}",
            )
        except httpx.RequestError as exc:
            latency_ms = (time.monotonic() - start) * 1000
            logger.warning("Request error for %s: %s", self.config.url, exc)
            result = CheckResult(
                route=self.config.name,
                url=self.config.url,
                status_code=None,
                latency_ms=round(latency_ms, 2),
                success=False,
                error=str(exc),
            )

        logger.debug("Checked %s: %s", self.config.name, result)
        return result

    @property
    def average_latency_ms(self) -> Optional[float]:
        if not self._history:
            return None
        return round(sum(self._history) / len(self._history), 2)
