"""Tests for routewatch.alert_suppressor."""

from datetime import datetime, time

import pytest

from routewatch.alert_suppressor import AlertSuppressor, MaintenanceWindow


@pytest.fixture()
def window() -> MaintenanceWindow:
    return MaintenanceWindow(
        name="nightly",
        route_pattern=r"/api/",
        start_time=time(2, 0),
        end_time=time(4, 0),
        weekdays=list(range(7)),
    )


@pytest.fixture()
def suppressor(window: MaintenanceWindow) -> AlertSuppressor:
    return AlertSuppressor(windows=[window])


def _dt(hour: int, minute: int = 0, weekday: int = 0) -> datetime:
    """Build a UTC datetime on a Monday with the given time."""
    # Monday 2024-01-01
    base = datetime(2024, 1, 1 + weekday, hour, minute)
    return base


def test_suppressed_inside_window(suppressor: AlertSuppressor) -> None:
    now = _dt(3, 0)  # 03:00 inside 02:00–04:00
    assert suppressor.is_suppressed("https://example.com/api/health", now=now)


def test_not_suppressed_outside_window(suppressor: AlertSuppressor) -> None:
    now = _dt(5, 0)  # 05:00 outside window
    assert not suppressor.is_suppressed("https://example.com/api/health", now=now)


def test_not_suppressed_non_matching_url(suppressor: AlertSuppressor) -> None:
    now = _dt(3, 0)
    assert not suppressor.is_suppressed("https://example.com/public/status", now=now)


def test_overnight_window() -> None:
    overnight = MaintenanceWindow(
        name="overnight",
        route_pattern=r".*",
        start_time=time(23, 0),
        end_time=time(1, 0),
        weekdays=list(range(7)),
    )
    s = AlertSuppressor(windows=[overnight])
    assert s.is_suppressed("http://x.com/", now=_dt(23, 30))
    assert s.is_suppressed("http://x.com/", now=_dt(0, 30))
    assert not s.is_suppressed("http://x.com/", now=_dt(12, 0))


def test_weekday_filter() -> None:
    weekday_only = MaintenanceWindow(
        name="weekday",
        route_pattern=r".*",
        start_time=time(2, 0),
        end_time=time(4, 0),
        weekdays=[0, 1, 2, 3, 4],  # Mon–Fri
    )
    s = AlertSuppressor(windows=[weekday_only])
    saturday = _dt(3, 0, weekday=5)  # Saturday
    monday = _dt(3, 0, weekday=0)
    assert not s.is_suppressed("http://x.com/", now=saturday)
    assert s.is_suppressed("http://x.com/", now=monday)


def test_add_window_dynamically() -> None:
    s = AlertSuppressor()
    assert not s.is_suppressed("http://x.com/api/", now=_dt(3, 0))
    s.add_window(
        MaintenanceWindow(
            name="added",
            route_pattern=r"/api/",
            start_time=time(2, 0),
            end_time=time(4, 0),
        )
    )
    assert s.is_suppressed("http://x.com/api/", now=_dt(3, 0))


def test_active_windows_returns_only_active(window: MaintenanceWindow) -> None:
    s = AlertSuppressor(windows=[window])
    assert len(s.active_windows(now=_dt(3, 0))) == 1
    assert len(s.active_windows(now=_dt(5, 0))) == 0
