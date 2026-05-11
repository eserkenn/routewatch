"""Webhook alerter for sending latency regression notifications."""

from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Optional

from routewatch.checker import CheckResult
from routewatch.config import WebhookConfig

logger = logging.getLogger(__name__)


@dataclass
class AlertPayload:
    route_name: str
    url: str
    status_code: Optional[int]
    latency_ms: Optional[float]
    average_latency_ms: Optional[float]
    error: Optional[str]
    threshold_ms: float

    def to_dict(self) -> dict:
        return {
            "alert": "latency_regression",
            "route": self.route_name,
            "url": self.url,
            "status_code": self.status_code,
            "latency_ms": self.latency_ms,
            "average_latency_ms": self.average_latency_ms,
            "error": self.error,
            "threshold_ms": self.threshold_ms,
        }


def build_payload(result: CheckResult, threshold_ms: float) -> AlertPayload:
    return AlertPayload(
        route_name=result.route_name,
        url=result.url,
        status_code=result.status_code,
        latency_ms=result.latency_ms,
        average_latency_ms=result.average_latency_ms,
        error=result.error,
        threshold_ms=threshold_ms,
    )


def send_alert(webhook: WebhookConfig, result: CheckResult, threshold_ms: float) -> bool:
    """Send an alert to the configured webhook URL.

    Returns True if the request succeeded, False otherwise.
    """
    payload = build_payload(result, threshold_ms)
    body = json.dumps(payload.to_dict()).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    headers.update(webhook.headers)

    req = urllib.request.Request(webhook.url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            logger.info(
                "Alert sent for route '%s' — webhook responded %s",
                result.route_name,
                resp.status,
            )
            return True
    except urllib.error.URLError as exc:
        logger.error("Failed to send alert for route '%s': %s", result.route_name, exc)
        return False
