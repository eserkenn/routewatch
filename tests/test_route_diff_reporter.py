"""Tests for RouteDiffReporter."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch, call

import pytest

from routewatch.metrics import MetricsCollector
from routewatch.history import LatencyHistory
from routewatch.route_diff_reporter import RouteDiffReporter
from routewatch.route_snapshot import RouteSnapshot, SnapshotDiff, SnapshotEntry, DiffEntry


@pytest.fixture()
def collector():
    return MetricsCollector()


@pytest.fixture()
def history(tmp_path):
    return LatencyHistory(path=str(tmp_path / "hist.json"))


@pytest.fixture()
def reporter(collector, history):
    return RouteDiffReporter(collector, history, interval_s=0.05, regression_threshold_ms=20.0)


def _make_snapshot(routes: dict) -> RouteSnapshot:
    """Helper: build a RouteSnapshot from {url: avg_latency_ms}."""
    entries = [
        SnapshotEntry(url=url, avg_latency_ms=lat, success_rate=1.0, failure_count=0)
        for url, lat in routes.items()
    ]
    return RouteSnapshot(routes=entries)


def test_reporter_start_stop(reporter):
    reporter.start()
    assert reporter._thread is not None
    assert reporter._thread.is_alive()
    reporter.stop()
    assert not reporter._thread


def test_baseline_captured_on_start(collector, history):
    r = RouteDiffReporter(collector, history, interval_s=60)
    with patch("routewatch.route_diff_reporter.take_snapshot") as mock_snap:
        mock_snap.return_value = _make_snapshot({})
        r.start()
        r.stop()
    mock_snap.assert_called_once_with(collector, history)


def test_no_regression_logs_info(reporter, caplog):
    baseline = _make_snapshot({"http://a.test": 100.0})
    current = _make_snapshot({"http://a.test": 105.0})  # +5 ms < 20 ms threshold

    with patch("routewatch.route_diff_reporter.take_snapshot", side_effect=[baseline, current]):
        with patch("routewatch.route_diff_reporter.diff_snapshots") as mock_diff:
            mock_diff.return_value = SnapshotDiff(changed=[], added=[], removed=[])
            reporter.start()
            time.sleep(0.15)
            reporter.stop()

    assert any("no latency regressions" in r.message for r in caplog.records)


def test_regression_logs_warning(collector, history, caplog):
    r = RouteDiffReporter(collector, history, interval_s=0.05, regression_threshold_ms=20.0)
    baseline = _make_snapshot({"http://slow.test": 100.0})
    current = _make_snapshot({"http://slow.test": 200.0})

    diff_entry = DiffEntry(
        url="http://slow.test",
        baseline_latency_ms=100.0,
        current_latency_ms=200.0,
        latency_delta_ms=100.0,
    )
    fake_diff = SnapshotDiff(changed=[diff_entry], added=[], removed=[])

    with patch("routewatch.route_diff_reporter.take_snapshot", side_effect=[baseline, current, current]):
        with patch("routewatch.route_diff_reporter.diff_snapshots", return_value=fake_diff):
            r.start()
            time.sleep(0.12)
            r.stop()

    warnings = [rec for rec in caplog.records if rec.levelname == "WARNING"]
    assert any("http://slow.test" in w.message for w in warnings)
    assert any("+100.0 ms" in w.message for w in warnings)


def test_stop_without_start_is_safe(reporter):
    """Calling stop before start should not raise."""
    reporter.stop()
