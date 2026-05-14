"""Tests for routewatch.metrics."""

import pytest
from routewatch.metrics import MetricsCollector, RouteMetrics


@pytest.fixture
def collector() -> MetricsCollector:
    return MetricsCollector()


def test_initial_metrics_are_zero(collector):
    m = collector.get("https://example.com/health")
    assert m.total_checks == 0
    assert m.successful_checks == 0
    assert m.failed_checks == 0
    assert m.alert_count == 0


def test_record_success(collector):
    collector.record_check("route-a", success=True)
    m = collector.get("route-a")
    assert m.total_checks == 1
    assert m.successful_checks == 1
    assert m.failed_checks == 0
    assert m.consecutive_successes == 1
    assert m.consecutive_failures == 0


def test_record_failure(collector):
    collector.record_check("route-b", success=False)
    m = collector.get("route-b")
    assert m.total_checks == 1
    assert m.failed_checks == 1
    assert m.consecutive_failures == 1
    assert m.consecutive_successes == 0


def test_consecutive_resets_on_switch(collector):
    collector.record_check("r", success=True)
    collector.record_check("r", success=True)
    collector.record_check("r", success=False)
    m = collector.get("r")
    assert m.consecutive_successes == 0
    assert m.consecutive_failures == 1


def test_alert_count_increments(collector):
    collector.record_check("r", success=False, alerted=True)
    collector.record_check("r", success=False, alerted=False)
    collector.record_check("r", success=False, alerted=True)
    assert collector.get("r").alert_count == 2


def test_success_rate(collector):
    for _ in range(3):
        collector.record_check("r", success=True)
    collector.record_check("r", success=False)
    m = collector.get("r")
    assert m.success_rate == pytest.approx(0.75)
    assert m.failure_rate == pytest.approx(0.25)


def test_success_rate_no_checks():
    m = RouteMetrics()
    assert m.success_rate == 0.0
    assert m.failure_rate == 0.0


def test_all_returns_copy(collector):
    collector.record_check("r1", success=True)
    collector.record_check("r2", success=False)
    snapshot = collector.all()
    assert set(snapshot.keys()) == {"r1", "r2"}


def test_reset_single(collector):
    collector.record_check("r", success=True)
    collector.reset("r")
    assert collector.get("r").total_checks == 0


def test_reset_all(collector):
    collector.record_check("r1", success=True)
    collector.record_check("r2", success=True)
    collector.reset_all()
    assert collector.all() == {}
