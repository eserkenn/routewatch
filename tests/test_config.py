"""Tests for routewatch configuration loader."""

import json
import os
import pytest
from routewatch.config import load_config, AppConfig, RouteConfig, WebhookConfig


@pytest.fixture
def minimal_config(tmp_path):
    cfg = {
        "routes": [
            {"name": "Test Route", "url": "https://example.com/"}
        ],
        "webhooks": [
            {"url": "https://hooks.example.com/alert"}
        ]
    }
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(cfg))
    return str(config_file)


@pytest.fixture
def full_config(tmp_path):
    cfg = {
        "check_interval_seconds": 30,
        "alert_cooldown_seconds": 120,
        "routes": [
            {
                "name": "API",
                "url": "https://api.example.com/health",
                "method": "POST",
                "timeout": 2.0,
                "latency_threshold_ms": 100.0,
                "expected_status": 201,
                "headers": {"Authorization": "Bearer token"}
            }
        ],
        "webhooks": [
            {"url": "https://hooks.example.com/alert", "secret": "s3cr3t"}
        ]
    }
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(cfg))
    return str(config_file)


def test_load_minimal_config(minimal_config):
    config = load_config(minimal_config)
    assert isinstance(config, AppConfig)
    assert len(config.routes) == 1
    assert len(config.webhooks) == 1
    assert config.check_interval_seconds == 60
    assert config.alert_cooldown_seconds == 300


def test_route_defaults(minimal_config):
    config = load_config(minimal_config)
    route = config.routes[0]
    assert isinstance(route, RouteConfig)
    assert route.name == "Test Route"
    assert route.url == "https://example.com/"
    assert route.method == "GET"
    assert route.timeout == 5.0
    assert route.latency_threshold_ms == 500.0
    assert route.expected_status == 200
    assert route.headers == {}


def test_load_full_config(full_config):
    config = load_config(full_config)
    assert config.check_interval_seconds == 30
    assert config.alert_cooldown_seconds == 120
    route = config.routes[0]
    assert route.method == "POST"
    assert route.timeout == 2.0
    assert route.latency_threshold_ms == 100.0
    assert route.expected_status == 201
    assert route.headers == {"Authorization": "Bearer token"}
    webhook = config.webhooks[0]
    assert isinstance(webhook, WebhookConfig)
    assert webhook.secret == "s3cr3t"


def test_missing_config_raises():
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/path/config.json")


def test_env_var_config_path(full_config, monkeypatch):
    monkeypatch.setenv("ROUTEWATCH_CONFIG", full_config)
    config = load_config()
    assert len(config.routes) == 1
    assert config.routes[0].name == "API"
