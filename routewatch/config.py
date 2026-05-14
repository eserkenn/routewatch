"""Configuration dataclasses and loader for routewatch."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class RouteConfig:
    url: str
    name: str = ""
    method: str = "GET"
    interval_seconds: int = 60
    timeout_seconds: float = 10.0
    expected_status: int = 200
    latency_threshold_ms: Optional[float] = None
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class WebhookConfig:
    url: str
    secret: str = ""
    timeout_seconds: float = 5.0


@dataclass
class AppConfig:
    routes: List[RouteConfig]
    webhooks: List[WebhookConfig]
    history_path: str = "latency_history.json"
    history_max_entries: int = 500
    log_level: str = "INFO"
    log_file: Optional[str] = None


def _parse_route(raw: Dict[str, Any]) -> RouteConfig:
    return RouteConfig(
        url=raw["url"],
        name=raw.get("name", ""),
        method=raw.get("method", "GET").upper(),
        interval_seconds=int(raw.get("interval_seconds", 60)),
        timeout_seconds=float(raw.get("timeout_seconds", 10.0)),
        expected_status=int(raw.get("expected_status", 200)),
        latency_threshold_ms=(
            float(raw["latency_threshold_ms"])
            if "latency_threshold_ms" in raw
            else None
        ),
        headers=raw.get("headers", {}),
    )


def _parse_webhook(raw: Dict[str, Any]) -> WebhookConfig:
    return WebhookConfig(
        url=raw["url"],
        secret=raw.get("secret", ""),
        timeout_seconds=float(raw.get("timeout_seconds", 5.0)),
    )


def load_config(path: str | Path) -> AppConfig:
    with open(path) as fh:
        data: Dict[str, Any] = json.load(fh)

    return AppConfig(
        routes=[_parse_route(r) for r in data.get("routes", [])],
        webhooks=[_parse_webhook(w) for w in data.get("webhooks", [])],
        history_path=data.get("history_path", "latency_history.json"),
        history_max_entries=int(data.get("history_max_entries", 500)),
        log_level=data.get("log_level", "INFO"),
        log_file=data.get("log_file"),
    )
