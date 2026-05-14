"""Tests for routewatch.status module."""

import pytest

from routewatch.metrics import MetricsCollector
from routewatch.history import LatencyHistory
from routewatch.status import build_status_report, RouteSummary, StatusReport


@pytest.fixture
def collector():
    return MetricsCollector()


@pytest.fixture
def history(tmp_path):
    return LatencyHistory(persist_path=str(tmp_path / "hist.json"))


ROUTE_URLS = {"api_health": "http://example.com/health", "api_users": "http://example.com/users"}


def test_empty_routes_returns_zero_counts(collector, history):
    report = build_status_report(collector, history, {})
    assert report.total_routes == 0
    assert report.healthy_routes == 0
    assert report.unhealthy_routes == 0
    assert report.all_healthy is True


def test_all_healthy_when_no_failures(collector, history):
    for _ in range(5):
        collector.record_success("api_health")
        history.record("api_health", 120.0)

    report = build_status_report(collector, history, {"api_health": "http://example.com/health"})
    assert report.total_routes == 1
    assert report.healthy_routes == 1
    assert report.unhealthy_routes == 0
    assert report.all_healthy is True


def test_unhealthy_when_consecutive_failures_exceed_threshold(collector, history):
    for _ in range(4):
        collector.record_failure("api_users")

    report = build_status_report(
        collector, history, {"api_users": "http://example.com/users"}, failure_threshold=3
    )
    summary = report.routes[0]
    assert summary.is_healthy is False
    assert report.unhealthy_routes == 1
    assert report.all_healthy is False


def test_avg_latency_computed_from_history(collector, history):
    latencies = [100.0, 200.0, 300.0]
    for lat in latencies:
        history.record("api_health", lat)
        collector.record_success("api_health")

    report = build_status_report(collector, history, {"api_health": "http://example.com/health"})
    assert report.routes[0].avg_latency_ms == pytest.approx(200.0, rel=1e-2)


def test_zero_latency_for_unknown_history_route(collector, history):
    collector.record_success("api_health")
    report = build_status_report(collector, history, {"api_health": "http://example.com/health"})
    assert report.routes[0].avg_latency_ms == 0.0


def test_multiple_routes_mixed_health(collector, history):
    collector.record_success("api_health")
    for _ in range(5):
        collector.record_failure("api_users")

    report = build_status_report(collector, history, ROUTE_URLS, failure_threshold=3)
    assert report.total_routes == 2
    assert report.healthy_routes == 1
    assert report.unhealthy_routes == 1


def test_route_summary_includes_url(collector, history):
    """Each RouteSummary should carry the URL from the provided route mapping."""
    collector.record_success("api_health")
    report = build_status_report(collector, history, {"api_health": "http://example.com/health"})
    assert report.routes[0].url == "http://example.com/health"


def test_route_summary_includes_name(collector, history):
    """Each RouteSummary should carry the route name key."""
    collector.record_success("api_health")
    report = build_status_report(collector, history, {"api_health": "http://example.com/health"})
    assert report.routes[0].name == "api_health"
