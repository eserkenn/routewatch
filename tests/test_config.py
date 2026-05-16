"""Tests for routewatch.config including tag fields."""
from __future__ import annotations

import json
import pytest

from routewatch.config import AppConfig, RouteConfig, WebhookConfig, load_config


@pytest.fixture()
def minimal_config(tmp_path):
    data = {"routes": [{"url": "https://example.com"}]}
    p = tmp_path / "config.json"
    p.write_text(json.dumps(data))
    return p


@pytest.fixture()
def full_config(tmp_path):
    data = {
        "routes": [
            {
                "url": "https://example.com/api",
                "interval_seconds": 15,
                "expected_status": 201,
                "timeout_seconds": 3.0,
                "latency_threshold_ms": 500.0,
                "tags": ["prod", "api"],
            }
        ],
        "webhooks": [{"url": "https://hooks.example.com", "secret": "s3cr3t"}],
        "history_path": "/tmp/hist.json",
        "log_level": "DEBUG",
        "metrics_interval_seconds": 30,
        "status_interval_seconds": 90,
        "health_port": 9090,
        "tag_include": ["prod"],
        "tag_exclude": ["internal"],
    }
    p = tmp_path / "config.json"
    p.write_text(json.dumps(data))
    return p


def test_load_minimal_config(minimal_config):
    cfg = load_config(minimal_config)
    assert isinstance(cfg, AppConfig)
    assert len(cfg.routes) == 1
    assert cfg.routes[0].url == "https://example.com"


def test_route_defaults(minimal_config):
    cfg = load_config(minimal_config)
    r = cfg.routes[0]
    assert r.interval_seconds == 60
    assert r.expected_status == 200
    assert r.timeout_seconds == 10.0
    assert r.latency_threshold_ms == 2000.0
    assert r.tags == []


def test_load_full_config(full_config):
    cfg = load_config(full_config)
    r = cfg.routes[0]
    assert r.interval_seconds == 15
    assert r.expected_status == 201
    assert r.tags == ["prod", "api"]

    assert cfg.log_level == "DEBUG"
    assert cfg.health_port == 9090
    assert cfg.tag_include == ["prod"]
    assert cfg.tag_exclude == ["internal"]


def test_webhook_parsed(full_config):
    cfg = load_config(full_config)
    assert len(cfg.webhooks) == 1
    assert cfg.webhooks[0].url == "https://hooks.example.com"
    assert cfg.webhooks[0].secret == "s3cr3t"


def test_tag_filter_defaults(minimal_config):
    cfg = load_config(minimal_config)
    assert cfg.tag_include == []
    assert cfg.tag_exclude == []


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "nonexistent.json")
