"""Configuration loading and validation for routewatch."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class RouteConfig:
    url: str
    method: str = "GET"
    interval_seconds: int = 60
    timeout_seconds: int = 10
    expected_status: int = 200
    latency_threshold_ms: float = 2000.0
    name: Optional[str] = None


@dataclass
class WebhookConfig:
    url: str
    secret: Optional[str] = None


@dataclass
class AppConfig:
    routes: List[RouteConfig]
    webhooks: List[WebhookConfig] = field(default_factory=list)
    log_level: str = "INFO"
    history_path: str = ".routewatch_history.json"
    consecutive_failures_threshold: int = 3
    alert_cooldown_seconds: int = 300
    health_endpoint_enabled: bool = False
    health_endpoint_host: str = "127.0.0.1"
    health_endpoint_port: int = 9090


def _parse_route(raw: Dict[str, Any]) -> RouteConfig:
    return RouteConfig(
        url=raw["url"],
        method=raw.get("method", "GET"),
        interval_seconds=raw.get("interval_seconds", 60),
        timeout_seconds=raw.get("timeout_seconds", 10),
        expected_status=raw.get("expected_status", 200),
        latency_threshold_ms=raw.get("latency_threshold_ms", 2000.0),
        name=raw.get("name"),
    )


def _parse_webhook(raw: Dict[str, Any]) -> WebhookConfig:
    return WebhookConfig(
        url=raw["url"],
        secret=raw.get("secret"),
    )


def load_config(path: str) -> AppConfig:
    data = json.loads(Path(path).read_text())
    routes = [_parse_route(r) for r in data.get("routes", [])]
    webhooks = [_parse_webhook(w) for w in data.get("webhooks", [])]
    return AppConfig(
        routes=routes,
        webhooks=webhooks,
        log_level=data.get("log_level", "INFO"),
        history_path=data.get("history_path", ".routewatch_history.json"),
        consecutive_failures_threshold=data.get("consecutive_failures_threshold", 3),
        alert_cooldown_seconds=data.get("alert_cooldown_seconds", 300),
        health_endpoint_enabled=data.get("health_endpoint_enabled", False),
        health_endpoint_host=data.get("health_endpoint_host", "127.0.0.1"),
        health_endpoint_port=data.get("health_endpoint_port", 9090),
    )
