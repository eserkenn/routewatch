"""Tests for routewatch.status_reporter module."""

import time
import pytest

from routewatch.metrics import MetricsCollector
from routewatch.history import LatencyHistory
from routewatch.status_reporter import StatusReporter


@pytest.fixture
def collector():
    return MetricsCollector()


@pytest.fixture
def history(tmp_path):
    return LatencyHistory(persist_path=str(tmp_path / "hist.json"))


ROUTE_URLS = {"api_health": "http://example.com/health"}


def test_reporter_start_stop(collector, history):
    reporter = StatusReporter(collector, history, ROUTE_URLS, interval_seconds=10.0)
    reporter.start()
    assert reporter._thread is not None
    assert reporter._thread.is_alive()
    reporter.stop()
    assert not reporter._thread.is_alive()


def test_reporter_logs_summary(collector, history, caplog):
    import logging
    collector.record_success("api_health")
    history.record("api_health", 150.0)

    reporter = StatusReporter(collector, history, ROUTE_URLS, interval_seconds=0.05)
    with caplog.at_level(logging.INFO):
        reporter.start()
        time.sleep(0.15)
        reporter.stop()

    messages = " ".join(caplog.messages)
    assert "api_health" in messages
    assert "healthy" in messages


def test_reporter_logs_no_routes_message(collector, history, caplog):
    import logging
    reporter = StatusReporter(collector, history, {}, interval_seconds=0.05)
    with caplog.at_level(logging.INFO):
        reporter.start()
        time.sleep(0.15)
        reporter.stop()

    assert any("No routes configured" in m for m in caplog.messages)


def test_reporter_logs_degraded_status(collector, history, caplog):
    import logging
    for _ in range(5):
        collector.record_failure("api_health")

    reporter = StatusReporter(
        collector, history, ROUTE_URLS, interval_seconds=0.05, failure_threshold=3
    )
    with caplog.at_level(logging.INFO):
        reporter.start()
        time.sleep(0.15)
        reporter.stop()

    messages = " ".join(caplog.messages)
    assert "DEGRADED" in messages
