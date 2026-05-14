"""Tests for alert throttling logic."""

import time

import pytest

from routewatch.alert_throttle import AlertThrottle

ROUTE_URL = "https://example.com/api/health"


@pytest.fixture
def throttle() -> AlertThrottle:
    return AlertThrottle(cooldown_seconds=60)


def test_first_alert_always_allowed(throttle: AlertThrottle) -> None:
    assert throttle.should_send(ROUTE_URL) is True


def test_alert_blocked_within_cooldown(throttle: AlertThrottle) -> None:
    throttle.record_sent(ROUTE_URL)
    assert throttle.should_send(ROUTE_URL) is False


def test_alert_allowed_after_cooldown(monkeypatch: pytest.MonkeyPatch) -> None:
    throttle = AlertThrottle(cooldown_seconds=10)
    start = time.monotonic()
    monkeypatch.setattr("routewatch.alert_throttle.time.monotonic", lambda: start)
    throttle.record_sent(ROUTE_URL)

    # Simulate time passing beyond the cooldown
    monkeypatch.setattr(
        "routewatch.alert_throttle.time.monotonic", lambda: start + 11
    )
    assert throttle.should_send(ROUTE_URL) is True


def test_record_sent_increments_count(throttle: AlertThrottle) -> None:
    assert throttle.alert_count(ROUTE_URL) == 0
    throttle.record_sent(ROUTE_URL)
    assert throttle.alert_count(ROUTE_URL) == 1
    throttle.record_sent(ROUTE_URL)
    assert throttle.alert_count(ROUTE_URL) == 2


def test_reset_clears_state(throttle: AlertThrottle) -> None:
    throttle.record_sent(ROUTE_URL)
    throttle.reset(ROUTE_URL)
    assert throttle.should_send(ROUTE_URL) is True
    assert throttle.alert_count(ROUTE_URL) == 0


def test_reset_unknown_route_is_noop(throttle: AlertThrottle) -> None:
    throttle.reset("https://unknown.example.com/")


def test_seconds_until_next_none_if_no_alert(throttle: AlertThrottle) -> None:
    assert throttle.seconds_until_next(ROUTE_URL) is None


def test_seconds_until_next_positive_after_alert(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    throttle = AlertThrottle(cooldown_seconds=60)
    start = time.monotonic()
    monkeypatch.setattr("routewatch.alert_throttle.time.monotonic", lambda: start)
    throttle.record_sent(ROUTE_URL)

    monkeypatch.setattr(
        "routewatch.alert_throttle.time.monotonic", lambda: start + 10
    )
    remaining = throttle.seconds_until_next(ROUTE_URL)
    assert remaining is not None
    assert 49.0 <= remaining <= 51.0


def test_independent_throttle_per_route(throttle: AlertThrottle) -> None:
    other = "https://other.example.com/health"
    throttle.record_sent(ROUTE_URL)
    assert throttle.should_send(ROUTE_URL) is False
    assert throttle.should_send(other) is True
