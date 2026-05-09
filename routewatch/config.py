"""Configuration loader for routewatch."""

import os
import json
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RouteConfig:
    url: str
    name: str
    method: str = "GET"
    timeout: float = 5.0
    latency_threshold_ms: float = 500.0
    headers: dict = field(default_factory=dict)
    expected_status: int = 200


@dataclass
class WebhookConfig:
    url: str
    secret: Optional[str] = None


@dataclass
class AppConfig:
    routes: List[RouteConfig]
    webhooks: List[WebhookConfig]
    check_interval_seconds: int = 60
    alert_cooldown_seconds: int = 300


def load_config(path: Optional[str] = None) -> AppConfig:
    """Load configuration from a JSON file."""
    config_path = path or os.environ.get("ROUTEWATCH_CONFIG", "config.json")

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r") as f:
        raw = json.load(f)

    routes = [
        RouteConfig(
            url=r["url"],
            name=r.get("name", r["url"]),
            method=r.get("method", "GET"),
            timeout=r.get("timeout", 5.0),
            latency_threshold_ms=r.get("latency_threshold_ms", 500.0),
            headers=r.get("headers", {}),
            expected_status=r.get("expected_status", 200),
        )
        for r in raw.get("routes", [])
    ]

    webhooks = [
        WebhookConfig(url=w["url"], secret=w.get("secret"))
        for w in raw.get("webhooks", [])
    ]

    return AppConfig(
        routes=routes,
        webhooks=webhooks,
        check_interval_seconds=raw.get("check_interval_seconds", 60),
        alert_cooldown_seconds=raw.get("alert_cooldown_seconds", 300),
    )
