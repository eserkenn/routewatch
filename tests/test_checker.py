"""Tests for the RouteChecker and CheckResult classes."""

import pytest
import httpx
import respx

from routewatch.checker import RouteChecker, CheckResult
from routewatch.config import RouteConfig


@pytest.fixture
def basic_route():
    return RouteConfig(
        name="healthcheck",
        url="https://example.com/health",
        method="GET",
        expected_status=200,
        timeout_seconds=5.0,
        latency_threshold_ms=500.0,
        interval_seconds=30,
    )


@respx.mock
def test_successful_check(basic_route):
    respx.get("https://example.com/health").mock(
        return_value=httpx.Response(200)
    )
    checker = RouteChecker(config=basic_route)
    result = checker.check()

    assert result.success is True
    assert result.status_code == 200
    assert result.latency_ms is not None
    assert result.latency_ms >= 0
    assert result.error is None
    assert result.is_alert is False


@respx.mock
def test_unexpected_status_code(basic_route):
    respx.get("https://example.com/health").mock(
        return_value=httpx.Response(503)
    )
    checker = RouteChecker(config=basic_route)
    result = checker.check()

    assert result.success is False
    assert result.status_code == 503
    assert "503" in result.error
    assert result.is_alert is True


@respx.mock
def test_request_error(basic_route):
    respx.get("https://example.com/health").mock(
        side_effect=httpx.ConnectError("connection refused")
    )
    checker = RouteChecker(config=basic_route)
    result = checker.check()

    assert result.success is False
    assert result.status_code is None
    assert result.error is not None
    assert result.is_alert is True


@respx.mock
def test_latency_history_accumulates(basic_route):
    respx.get("https://example.com/health").mock(
        return_value=httpx.Response(200)
    )
    checker = RouteChecker(config=basic_route)

    assert checker.average_latency_ms is None

    checker.check()
    checker.check()
    checker.check()

    assert checker.average_latency_ms is not None
    assert checker.average_latency_ms >= 0


@respx.mock
def test_no_threshold_does_not_alert(basic_route):
    basic_route.latency_threshold_ms = None
    respx.get("https://example.com/health").mock(
        return_value=httpx.Response(200)
    )
    checker = RouteChecker(config=basic_route)
    result = checker.check()

    assert result.threshold_exceeded is False
    assert result.is_alert is False


@respx.mock
def test_timeout_triggers_alert(basic_route):
    """A timeout error should mark the result as failed and trigger an alert."""
    respx.get("https://example.com/health").mock(
        side_effect=httpx.TimeoutException("request timed out")
    )
    checker = RouteChecker(config=basic_route)
    result = checker.check()

    assert result.success is False
    assert result.status_code is None
    assert result.error is not None
    assert result.is_alert is True
