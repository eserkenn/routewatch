"""Tests for routewatch.route_snapshot."""
from __future__ import annotations

import time
import pytest

from routewatch.metrics import MetricsCollector
from routewatch.history import LatencyHistory
from routewatch.route_snapshot import (
    RouteSnapshot,
    SnapshotDiff,
    take_snapshot,
    diff_snapshots,
    take_all_snapshots,
)


@pytest.fixture
def collector(tmp_path):
    return MetricsCollector()


@pytest.fixture
def history(tmp_path):
    return LatencyHistory(storage_path=str(tmp_path / "hist.json"))


URL = "http://example.com/api"


def test_take_snapshot_zero_latency(collector, history):
    snap = take_snapshot(collector, history, URL)
    assert snap.url == URL
    assert snap.avg_latency_ms == 0.0
    assert snap.total_checks == 0


def test_take_snapshot_with_history(collector, history):
    history.record(URL, 120.0)
    history.record(URL, 80.0)
    snap = take_snapshot(collector, history, URL)
    assert snap.avg_latency_ms == pytest.approx(100.0)


def test_take_snapshot_reflects_metrics(collector, history):
    collector.record_success(URL, 50.0)
    collector.record_success(URL, 50.0)
    collector.record_failure(URL)
    snap = take_snapshot(collector, history, URL)
    assert snap.total_checks == 3
    assert snap.success_rate == pytest.approx(2 / 3)


def test_take_snapshot_timestamp_is_recent(collector, history):
    """Snapshot timestamp should be set at the time of creation."""
    before = time.time()
    snap = take_snapshot(collector, history, URL)
    after = time.time()
    assert before <= snap.timestamp <= after


def test_diff_snapshots_no_change():
    t = time.time()
    before = RouteSnapshot(URL, t, 1.0, 0.0, 10, 50.0, 0)
    after = RouteSnapshot(URL, t + 60, 1.0, 0.0, 10, 50.0, 0)
    diff = diff_snapshots(before, after)
    assert diff.success_rate_delta == pytest.approx(0.0)
    assert diff.avg_latency_delta_ms == pytest.approx(0.0)
    assert not diff.degraded


def test_diff_detects_latency_spike():
    t = time.time()
    before = RouteSnapshot(URL, t, 1.0, 0.0, 5, 50.0, 0)
    after = RouteSnapshot(URL, t + 60, 1.0, 0.0, 5, 200.0, 0)
    diff = diff_snapshots(before, after)
    assert diff.avg_latency_delta_ms == pytest.approx(150.0)
    assert diff.degraded


def test_diff_detects_success_rate_drop():
    t = time.time()
    before = RouteSnapshot(URL, t, 1.0, 0.0, 10, 50.0, 0)
    after = RouteSnapshot(URL, t + 60, 0.8, 0.2, 10, 50.0, 0)
    diff = diff_snapshots(before, after)
    assert diff.success_rate_delta == pytest.approx(-0.2)
    assert diff.degraded


def test_diff_raises_on_url_mismatch():
    t = time.time()
    a = RouteSnapshot("http://a.com", t, 1.0, 0.0, 1, 10.0, 0)
    b = RouteSnapshot("http://b.com", t, 1.0, 0.0, 1, 10.0, 0)
    with pytest.raises(ValueError, match="Cannot diff"):
        diff_snapshots(a, b)


def test_take_all_snapshots_returns_all(collector, history):
    collector.record_success("http://a.com", 10.0)
    collector.record_success("http://b.com", 20.0)
    snaps = take_all_snapshots(collector, history)
    assert set(snaps.keys()) == {"http://a.com", "http://b.com"}


def test_take_all_snapshots_empty(collector, history):
    assert take_all_snapshots(collector, history) == {}
