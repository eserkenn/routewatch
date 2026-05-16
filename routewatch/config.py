"""Configuration dataclasses and loader for routewatch."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RouteConfig:
    url: str
    interval_seconds: int = 60
    expected_status: int = 200
    timeout_seconds: float = 10.0
    latency_threshold_ms: float = 2000.0
    tags: list[str] = field(default_factory=list)


@dataclass
class WebhookConfig:
    url: str
    secret: str = ""


@dataclass
class AppConfig:
    routes: list[RouteConfig]
    webhooks: list[WebhookConfig] = field(default_factory=list)
    history_path: str = "latency_history.json"
    log_level: str = "INFO"
    metrics_interval_seconds: int = 60
    status_interval_seconds: int = 120
    health_port: int = 8080
    tag_include: list[str] = field(default_factory=list)
    tag_exclude: list[str] = field(default_factory=list)


def _parse_route(raw: dict[str, Any]) -> RouteConfig:
    return RouteConfig(
        url=raw["url"],
        interval_seconds=raw.get("interval_seconds", 60),
        expected_status=raw.get("expected_status", 200),
        timeout_seconds=raw.get("timeout_seconds", 10.0),
        latency_threshold_ms=raw.get("latency_threshold_ms", 2000.0),
        tags=raw.get("tags", []),
    )


def _parse_webhook(raw: dict[str, Any]) -> WebhookConfig:
    return WebhookConfig(
        url=raw["url"],
        secret=raw.get("secret", ""),
    )


def load_config(path: str | Path) -> AppConfig:
    data = json.loads(Path(path).read_text())
    routes = [_parse_route(r) for r in data.get("routes", [])]
    webhooks = [_parse_webhook(w) for w in data.get("webhooks", [])]
    return AppConfig(
        routes=routes,
        webhooks=webhooks,
        history_path=data.get("history_path", "latency_history.json"),
        log_level=data.get("log_level", "INFO"),
        metrics_interval_seconds=data.get("metrics_interval_seconds", 60),
        status_interval_seconds=data.get("status_interval_seconds", 120),
        health_port=data.get("health_port", 8080),
        tag_include=data.get("tag_include", []),
        tag_exclude=data.get("tag_exclude", []),
    )
