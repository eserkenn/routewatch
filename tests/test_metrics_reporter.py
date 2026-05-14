"""Tests for routewatch.metrics_reporter."""

import time
from unittest.mock import patch, call

import pytest

from routewatch.metrics import MetricsCollector
from routewatch.metrics_reporter import MetricsReporter


@pytest.fixture
def collector() -> MetricsCollector:
    c = MetricsCollector()
    c.record_check("https://api.example.com/ping", success=True)
    c.record_check("https://api.example.com/ping", success=False, alerted=True)
    return c


def test_reporter_logs_metrics(collector):
    reporter = MetricsReporter(interval_seconds=60, collector=collector)
    with patch("routewatch.metrics_reporter.logger") as mock_log:
        reporter._report()
    assert mock_log.info.called
    logged_msg = mock_log.info.call_args_list[-1]
    assert "https://api.example.com/ping" in str(logged_msg)


def test_reporter_logs_no_routes_message():
    empty_collector = MetricsCollector()
    reporter = MetricsReporter(interval_seconds=60, collector=empty_collector)
    with patch("routewatch.metrics_reporter.logger") as mock_log:
        reporter._report()
    mock_log.info.assert_called_once_with("[metrics] No routes tracked yet.")


def test_reporter_start_stop(collector):
    reporter = MetricsReporter(interval_seconds=60, collector=collector)
    reporter.start()
    assert reporter._thread is not None
    assert reporter._thread.is_alive()
    reporter.stop()
    assert not reporter._thread.is_alive()


def test_reporter_fires_periodically(collector):
    call_times = []

    original_report = MetricsReporter._report

    def patched_report(self):
        call_times.append(time.monotonic())
        original_report(self)

    with patch.object(MetricsReporter, "_report", patched_report):
        reporter = MetricsReporter(interval_seconds=1, collector=collector)
        reporter.start()
        time.sleep(2.5)
        reporter.stop()

    assert len(call_times) >= 2
