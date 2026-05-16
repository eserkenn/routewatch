"""Tests for routewatch.route_exporter."""

from __future__ import annotations

import csv
import io
import json
import tempfile
from pathlib import Path

import pytest

from routewatch.history import LatencyHistory
from routewatch.metrics import MetricsCollector
from routewatch.route_exporter import (
    ExportRow,
    build_export_rows,
    export_csv,
    export_json,
)


@pytest.fixture()
def collector() -> MetricsCollector:
    return MetricsCollector()


@pytest.fixture()
def history(tmp_path: Path) -> LatencyHistory:
    return LatencyHistory(storage_path=str(tmp_path / "lat.json"))


def _populate(collector: MetricsCollector, history: LatencyHistory) -> None:
    collector.record_success("GET", "http://example.com/a", 120.0)
    collector.record_success("GET", "http://example.com/a", 80.0)
    history.record("http://example.com/a", 120.0)
    history.record("http://example.com/a", 80.0)


def test_build_export_rows_returns_list(collector, history):
    _populate(collector, history)
    rows = build_export_rows(collector, history)
    assert len(rows) == 1
    assert isinstance(rows[0], ExportRow)


def test_export_row_fields(collector, history):
    _populate(collector, history)
    row = build_export_rows(collector, history)[0]
    assert row.route_url == "http://example.com/a"
    assert row.method == "GET"
    assert row.success_rate == 1.0
    assert row.failure_rate == 0.0
    assert row.consecutive_failures == 0
    assert row.avg_latency_ms == pytest.approx(100.0, abs=0.1)


def test_export_json_valid(collector, history):
    _populate(collector, history)
    rows = build_export_rows(collector, history)
    output = export_json(rows)
    parsed = json.loads(output)
    assert isinstance(parsed, list)
    assert parsed[0]["route_url"] == "http://example.com/a"


def test_export_csv_has_header(collector, history):
    _populate(collector, history)
    rows = build_export_rows(collector, history)
    output = export_csv(rows)
    reader = csv.DictReader(io.StringIO(output))
    data = list(reader)
    assert len(data) == 1
    assert "route_url" in data[0]
    assert "healthy" in data[0]


def test_export_csv_empty_rows():
    assert export_csv([]) == ""


def test_build_export_rows_empty(collector, history):
    rows = build_export_rows(collector, history)
    assert rows == []


def test_failure_reflected_in_row(collector, history):
    collector.record_failure("POST", "http://example.com/b")
    collector.record_failure("POST", "http://example.com/b")
    rows = build_export_rows(collector, history, failure_threshold=2)
    assert len(rows) == 1
    row = rows[0]
    assert row.failure_rate == 1.0
    assert not row.healthy
