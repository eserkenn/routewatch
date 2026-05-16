"""Tests for routewatch.snapshot_reporter."""
from __future__ import annotations

import time
import pytest

from routewatch.metrics import MetricsCollector
from routewatch.history import LatencyHistory
from routewatch.snapshot_reporter import SnapshotReporter


URL = "http://example.com/health"


@pytest.fixture
def collector():
    return MetricsCollector()


@pytest.fixture
def history(tmp_path):
    return LatencyHistory(storage_path=str(tmp_path / "hist.json"))


@pytest.fixture
def reporter(collector, history):
    r = SnapshotReporter(collector, history, interval=60.0)
    yield r
    r.stop()


def test_reporter_start_stop(reporter):
    reporter.start()
    assert reporter._thread is not None
    assert reporter._thread.is_alive()
    reporter.stop()
    assert not reporter._thread.is_alive()


def test_report_builds_baseline(reporter, collector, history):
    collector.record_success(URL, 30.0)
    reporter._report()
    assert URL in reporter._previous


def test_report_logs_regression(reporter, collector, history, caplog):
    import logging
    collector.record_success(URL, 30.0)
    reporter._report()  # baseline

    # Simulate degradation: inject a worse snapshot directly
    from routewatch.route_snapshot import RouteSnapshot
    t = time.time()
    reporter._previous[URL] = RouteSnapshot(URL, t - 60, 1.0, 0.0, 5, 30.0, 0)

    history.record(URL, 300.0)
    history.record(URL, 300.0)
    with caplog.at_level(logging.WARNING):
        reporter._report()

    assert any("regression detected" in r.message for r in caplog.records)


def test_report_no_routes_does_nothing(reporter, caplog):
    import logging
    with caplog.at_level(logging.DEBUG):
        reporter._report()
    assert any("no routes" in r.message for r in caplog.records)


def test_reporter_fires_periodically(collector, history, tmp_path):
    calls = []
    r = SnapshotReporter(collector, history, interval=0.05)
    original = r._report

    def _patched():
        calls.append(1)
        original()

    r._report = _patched
    r.start()
    time.sleep(0.25)
    r.stop()
    assert len(calls) >= 2
