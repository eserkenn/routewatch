"""Tests for the RouteScheduler."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from routewatch.checker import CheckResult
from routewatch.config import AppConfig, RouteConfig, WebhookConfig
from routewatch.scheduler import RouteScheduler


@pytest.fixture
def route():
    return RouteConfig(
        name="api",
        url="https://example.com/health",
        method="GET",
        expected_status=200,
        timeout_seconds=5.0,
        interval_seconds=30,
        latency_threshold_ms=500.0,
        history_size=5,
    )


@pytest.fixture
def webhook():
    return WebhookConfig(url="https://hooks.example.com/alert", secret=None)


@pytest.fixture
def app_config(route, webhook):
    return AppConfig(routes=[route], webhooks=[webhook])


@pytest.fixture
def scheduler(app_config):
    return RouteScheduler(app_config)


def _ok_result(route):
    return CheckResult(
        route_name=route.name,
        url=route.url,
        ok=True,
        status_code=200,
        latency_ms=120.0,
        error=None,
    )


def _bad_result(route):
    return CheckResult(
        route_name=route.name,
        url=route.url,
        ok=False,
        status_code=500,
        latency_ms=800.0,
        error="Server Error",
    )


@pytest.mark.asyncio
async def test_check_route_ok_no_alert(scheduler, route):
    ok = _ok_result(route)
    with patch("routewatch.scheduler.is_alert", return_value=False) as mock_alert, \
         patch.object(scheduler._checkers["api"], "check", new=AsyncMock(return_value=ok)):
        await scheduler._check_route(scheduler._checkers["api"])
        mock_alert.assert_called_once()


@pytest.mark.asyncio
async def test_check_route_bad_sends_alert(scheduler, route, webhook):
    bad = _bad_result(route)
    mock_payload = MagicMock()
    with patch("routewatch.scheduler.is_alert", return_value=True), \
         patch.object(scheduler._checkers["api"], "check", new=AsyncMock(return_value=bad)), \
         patch("routewatch.scheduler.build_payload", return_value=mock_payload) as mock_build, \
         patch("routewatch.scheduler.send_alert", new=AsyncMock()) as mock_send:
        await scheduler._check_route(scheduler._checkers["api"])
        mock_build.assert_called_once_with(bad, webhook)
        mock_send.assert_awaited_once_with(mock_payload, webhook)


@pytest.mark.asyncio
async def test_scheduler_creates_checkers(scheduler, route):
    assert "api" in scheduler._checkers
    assert scheduler._checkers["api"].route == route


@pytest.mark.asyncio
async def test_stop_sets_running_false(scheduler):
    scheduler._running = True
    scheduler.stop()
    assert scheduler._running is False


@pytest.mark.asyncio
async def test_run_loop_stops_when_not_running(scheduler, route):
    ok = _ok_result(route)
    call_count = 0

    async def fake_check():
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            scheduler.stop()
        return ok

    scheduler._running = True
    checker = scheduler._checkers["api"]
    with patch.object(checker, "check", new=fake_check), \
         patch("routewatch.scheduler.is_alert", return_value=False), \
         patch("asyncio.sleep", new=AsyncMock()):
        await scheduler._run_route_loop(checker)

    assert call_count >= 2
