"""Tests for routewatch.alert_history."""

import json
import os
import pytest

from routewatch.alert_history import AlertHistory, AlertRecord


@pytest.fixture
def history(tmp_path):
    path = str(tmp_path / "alert_history.json")
    return AlertHistory(_path=path)


def test_initial_history_is_empty(history):
    assert history.get() == []


def test_record_adds_entry(history):
    history.record("http://example.com/health", "latency_regression", latency_ms=320.5)
    records = history.get()
    assert len(records) == 1
    assert records[0].route_url == "http://example.com/health"
    assert records[0].reason == "latency_regression"
    assert records[0].latency_ms == 320.5


def test_record_stores_iso_timestamp(history):
    history.record("http://example.com/", "error")
    record = history.get()[0]
    # Should parse without raising
    from datetime import datetime
    dt = datetime.fromisoformat(record.sent_at)
    assert dt.tzinfo is not None


def test_get_filters_by_route(history):
    history.record("http://a.com/", "error")
    history.record("http://b.com/", "timeout")
    history.record("http://a.com/", "latency_regression")

    a_records = history.get("http://a.com/")
    assert len(a_records) == 2
    assert all(r.route_url == "http://a.com/" for r in a_records)


def test_get_unknown_route_returns_empty(history):
    history.record("http://a.com/", "error")
    assert history.get("http://unknown.com/") == []


def test_clear_specific_route(history):
    history.record("http://a.com/", "error")
    history.record("http://b.com/", "error")
    history.clear("http://a.com/")

    assert history.get("http://a.com/") == []
    assert len(history.get("http://b.com/")) == 1


def test_clear_all(history):
    history.record("http://a.com/", "error")
    history.record("http://b.com/", "error")
    history.clear()
    assert history.get() == []


def test_persists_to_disk(tmp_path):
    path = str(tmp_path / "alert_history.json")
    h1 = AlertHistory(_path=path)
    h1.record("http://example.com/", "latency_regression", latency_ms=500.0)

    assert os.path.exists(path)
    h2 = AlertHistory(_path=path)
    records = h2.get()
    assert len(records) == 1
    assert records[0].route_url == "http://example.com/"
    assert records[0].latency_ms == 500.0


def test_handles_missing_file_gracefully(tmp_path):
    path = str(tmp_path / "nonexistent.json")
    h = AlertHistory(_path=path)
    assert h.get() == []


def test_handles_corrupt_file_gracefully(tmp_path):
    path = str(tmp_path / "corrupt.json")
    with open(path, "w") as fh:
        fh.write("not valid json{{{")
    h = AlertHistory(_path=path)
    assert h.get() == []
