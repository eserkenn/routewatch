"""Tests for routewatch.alerter (including rate-limiter integration)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from routewatch.alerter import (
    AlertPayload,
    build_payload,
    send_alert,
    to_dict,
)
from routewatch.checker import CheckResult
from routewatch.config import WebhookConfig
from routewatch.rate_limiter import RateLimiter


@pytest.fixture()
def ok_result() -> CheckResult:
    return CheckResult(
        route="home",
        url="http://example.com/",
        status_code=200,
        latency_ms=42.0,
        error=None,
        average_latency_ms=40.0,
        consecutive_failures=0,
    )


@pytest.fixture()
def error_result() -> CheckResult:
    return CheckResult(
        route="api",
        url="http://example.com/api",
        status_code=None,
        latency_ms=None,
        error="connection refused",
        average_latency_ms=None,
        consecutive_failures=3,
    )


@pytest.fixture()
def webhook() -> WebhookConfig:
    return WebhookConfig(url="http://hooks.example.com/alert")


def test_build_payload_fields(ok_result: CheckResult):
    p = build_payload(ok_result)
    assert p.route == ok_result.route
    assert p.url == ok_result.url
    assert p.status_code == 200
    assert p.latency_ms == pytest.approx(42.0)
    assert p.error is None


def test_payload_to_dict_keys(ok_result: CheckResult):
    d = to_dict(build_payload(ok_result))
    assert set(d.keys()) == {
        "route", "url", "status_code", "latency_ms",
        "error", "average_latency_ms", "consecutive_failures",
    }


def test_send_alert_success(ok_result: CheckResult, webhook: WebhookConfig):
    lim = RateLimiter(rate=10.0, capacity=10.0)
    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.status = 200

    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = send_alert(ok_result, webhook, limiter=lim)

    assert result is True


def test_send_alert_network_error(ok_result: CheckResult, webhook: WebhookConfig):
    import urllib.error
    lim = RateLimiter(rate=10.0, capacity=10.0)
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
        result = send_alert(ok_result, webhook, limiter=lim)
    assert result is False


def test_send_alert_rate_limited(ok_result: CheckResult, webhook: WebhookConfig):
    # Capacity 0 means every call is blocked
    lim = RateLimiter(rate=1.0, capacity=1.0)
    lim.acquire(webhook.url)  # drain the single token
    with patch("urllib.request.urlopen") as mock_open:
        result = send_alert(ok_result, webhook, limiter=lim)
    assert result is False
    mock_open.assert_not_called()


def test_error_result_payload(error_result: CheckResult):
    p = build_payload(error_result)
    assert p.error == "connection refused"
    assert p.consecutive_failures == 3
    assert p.status_code is None
