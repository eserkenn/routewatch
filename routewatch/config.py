"""Configuration models and loader for routewatch."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class RouteConfig:
    name: str
    url: str
    interval_seconds: int = 60
    expected_status: int = 200
    latency_threshold_ms: float = 500.0
    history_size: int = 10


@dataclass
class WebhookConfig:
    url: str
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class AppConfig:
    routes: List[RouteConfig]
    webhook: Optional[WebhookConfig] = None
    log_level: str = "INFO"


def _parse_route(raw: Dict[str, Any]) -> RouteConfig:
    return RouteConfig(
        name=raw["name"],
        url=raw["url"],
        interval_seconds=raw.get("interval_seconds", 60),
        expected_status=raw.get("expected_status", 200),
        latency_threshold_ms=raw.get("latency_threshold_ms", 500.0),
        history_size=raw.get("history_size", 10),
    )


def _parse_webhook(raw: Optional[Dict[str, Any]]) -> Optional[WebhookConfig]:
    if raw is None:
        return None
    return WebhookConfig(
        url=raw["url"],
        headers=raw.get("headers", {}),
    )


def load_config(path: str | Path) -> AppConfig:
    """Load and parse an AppConfig from a JSON file."""
    data = json.loads(Path(path).read_text())
    routes = [_parse_route(r) for r in data.get("routes", [])]
    webhook = _parse_webhook(data.get("webhook"))
    return AppConfig(
        routes=routes,
        webhook=webhook,
        log_level=data.get("log_level", "INFO"),
    )
