"""Webhook alerting with optional rate limiting."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional

import urllib.request
import urllib.error

from routewatch.checker import CheckResult
from routewatch.config import WebhookConfig
from routewatch.logging_config import get_logger
from routewatch.rate_limiter import RateLimiter

log = get_logger(__name__)

# Module-level shared rate limiter (1 alert/sec, burst of 5)
_default_limiter: RateLimiter = RateLimiter(rate=1.0, capacity=5.0)


@dataclass
class AlertPayload:
    route: str
    url: str
    status_code: Optional[int]
    latency_ms: Optional[float]
    error: Optional[str]
    average_latency_ms: Optional[float]
    consecutive_failures: int


def to_dict(payload: AlertPayload) -> Dict[str, Any]:
    return {
        "route": payload.route,
        "url": payload.url,
        "status_code": payload.status_code,
        "latency_ms": payload.latency_ms,
        "error": payload.error,
        "average_latency_ms": payload.average_latency_ms,
        "consecutive_failures": payload.consecutive_failures,
    }


def build_payload(result: CheckResult) -> AlertPayload:
    return AlertPayload(
        route=result.route,
        url=result.url,
        status_code=result.status_code,
        latency_ms=result.latency_ms,
        error=result.error,
        average_latency_ms=result.average_latency_ms,
        consecutive_failures=result.consecutive_failures,
    )


def send_alert(
    result: CheckResult,
    webhook: WebhookConfig,
    limiter: Optional[RateLimiter] = None,
) -> bool:
    """Send an alert to *webhook*.  Returns True on success.

    If *limiter* is provided (or the module default is used), the call is
    rate-limited per webhook URL.  Blocked calls are logged and return False.
    """
    active_limiter = limiter if limiter is not None else _default_limiter
    if not active_limiter.acquire(webhook.url):
        log.warning("rate-limited: skipping alert for %s -> %s", result.route, webhook.url)
        return False

    payload = build_payload(result)
    body = json.dumps(to_dict(payload)).encode()
    req = urllib.request.Request(
        webhook.url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            log.info("alert sent to %s (HTTP %s)", webhook.url, resp.status)
            return True
    except urllib.error.URLError as exc:
        log.error("failed to send alert to %s: %s", webhook.url, exc)
        return False
