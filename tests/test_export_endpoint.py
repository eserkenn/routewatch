"""Tests for routewatch.export_endpoint."""

from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

import pytest

from routewatch.export_endpoint import ExportEndpoint
from routewatch.history import LatencyHistory
from routewatch.metrics import MetricsCollector

_PORT = 19092


@pytest.fixture()
def collector() -> MetricsCollector:
    return MetricsCollector()


@pytest.fixture()
def history(tmp_path: Path) -> LatencyHistory:
    return LatencyHistory(storage_path=str(tmp_path / "lat.json"))


@pytest.fixture()
def endpoint(collector, history):
    ep = ExportEndpoint(collector, history, port=_PORT)
    ep.start()
    time.sleep(0.05)
    yield ep
    ep.stop()


def test_export_json_returns_200(endpoint):
    with urllib.request.urlopen(f"http://127.0.0.1:{_PORT}/export/json") as resp:
        assert resp.status == 200


def test_export_json_content_type(endpoint):
    with urllib.request.urlopen(f"http://127.0.0.1:{_PORT}/export/json") as resp:
        assert "application/json" in resp.headers.get("Content-Type", "")


def test_export_json_empty_when_no_routes(endpoint):
    with urllib.request.urlopen(f"http://127.0.0.1:{_PORT}/export/json") as resp:
        data = json.loads(resp.read())
    assert data == []


def test_export_csv_returns_200(endpoint):
    with urllib.request.urlopen(f"http://127.0.0.1:{_PORT}/export/csv") as resp:
        assert resp.status == 200


def test_export_csv_content_type(endpoint):
    with urllib.request.urlopen(f"http://127.0.0.1:{_PORT}/export/csv") as resp:
        assert "text/csv" in resp.headers.get("Content-Type", "")


def test_export_json_reflects_metrics(endpoint, collector, history):
    collector.record_success("GET", "http://svc/ping", 55.0)
    history.record("http://svc/ping", 55.0)
    time.sleep(0.02)
    with urllib.request.urlopen(f"http://127.0.0.1:{_PORT}/export/json") as resp:
        data = json.loads(resp.read())
    assert len(data) == 1
    assert data[0]["route_url"] == "http://svc/ping"
    assert data[0]["success_rate"] == 1.0
