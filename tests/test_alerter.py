"""Tests for the webhook alerter module."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from routewatch.alerter import AlertPayload, build_payload, send_alert
from routewatch.checker import CheckResult
from routewatch.config import WebhookConfig


@pytest.fixture
def ok_result() -> CheckResult:
    return CheckResult(
        route_name="homepage",
        url="https://example.com/",
        status_code=200,
        latency_ms=320.5,
        average_latency_ms=280.0,
        error=None,
    )


@pytest.fixture
def error_result() -> CheckResult:
    return CheckResult(
        route_name="api-health",
        url="https://example.com/health",
        status_code=None,
        latency_ms=None,
        average_latency_ms=None,
        error="Connection refused",
    )


@pytest.fixture
def webhook() -> WebhookConfig:
    return WebhookConfig(url="https://hooks.example.com/alert", headers={})


def test_build_payload_fields(ok_result):
    payload = build_payload(ok_result, threshold_ms=300.0)
    assert payload.route_name == "homepage"
    assert payload.latency_ms == 320.5
    assert payload.threshold_ms == 300.0
    assert payload.error is None


def test_payload_to_dict_keys(ok_result):
    payload = build_payload(ok_result, threshold_ms=300.0)
    d = payload.to_dict()
    assert d["alert"] == "latency_regression"
    assert d["route"] == "homepage"
    assert d["threshold_ms"] == 300.0


def test_send_alert_success(webhook, ok_result):
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_response) as mock_open:
        result = send_alert(webhook, ok_result, threshold_ms=300.0)

    assert result is True
    mock_open.assert_called_once()
    request_obj = mock_open.call_args[0][0]
    assert request_obj.full_url == webhook.url
    assert request_obj.get_header("Content-type") == "application/json"
    body = json.loads(request_obj.data)
    assert body["route"] == "homepage"


def test_send_alert_failure(webhook, error_result):
    import urllib.error

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
        result = send_alert(webhook, error_result, threshold_ms=500.0)

    assert result is False


def test_send_alert_includes_custom_headers(ok_result):
    wh = WebhookConfig(
        url="https://hooks.example.com/alert",
        headers={"X-Api-Key": "secret"},
    )
    mock_response = MagicMock()
    mock_response.status = 204
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_response) as mock_open:
        send_alert(wh, ok_result, threshold_ms=300.0)

    request_obj = mock_open.call_args[0][0]
    assert request_obj.get_header("X-api-key") == "secret"
