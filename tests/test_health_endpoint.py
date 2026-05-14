"""Tests for the /health HTTP endpoint."""

import json
import time
import urllib.request
from unittest.mock import MagicMock, patch

import pytest

from routewatch.health_endpoint import HealthEndpoint
from routewatch.metrics import MetricsCollector
from routewatch.history import LatencyHistory
from routewatch.status import StatusReport, RouteSummary


@pytest.fixture()
def collector():
    return MetricsCollector()


@pytest.fixture()
def history(tmp_path):
    return LatencyHistory(persist_path=str(tmp_path / "lat.json"))


@pytest.fixture()
def endpoint(collector, history):
    ep = HealthEndpoint(collector, history, host="127.0.0.1", port=19090)
    ep.start()
    time.sleep(0.05)
    yield ep
    ep.stop()


def test_health_returns_200(endpoint):
    with urllib.request.urlopen("http://127.0.0.1:19090/health") as resp:
        assert resp.status == 200


def test_health_returns_json(endpoint):
    with urllib.request.urlopen("http://127.0.0.1:19090/health") as resp:
        data = json.loads(resp.read())
    assert "healthy" in data
    assert "total_routes" in data
    assert "routes" in data


def test_health_unknown_path_returns_404(endpoint):
    import urllib.error
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen("http://127.0.0.1:19090/unknown")
    assert exc_info.value.code == 404


def test_health_reflects_metrics(collector, history):
    collector.record_success("GET /api")
    collector.record_failure("GET /api")
    ep = HealthEndpoint(collector, history, host="127.0.0.1", port=19091)
    ep.start()
    time.sleep(0.05)
    try:
        with urllib.request.urlopen("http://127.0.0.1:19091/health") as resp:
            data = json.loads(resp.read())
        assert data["total_routes"] == 1
    finally:
        ep.stop()


def test_stop_shuts_down_server(collector, history):
    ep = HealthEndpoint(collector, history, host="127.0.0.1", port=19092)
    ep.start()
    time.sleep(0.05)
    ep.stop()
    time.sleep(0.05)
    import urllib.error
    with pytest.raises((urllib.error.URLError, ConnectionRefusedError)):
        urllib.request.urlopen("http://127.0.0.1:19092/health")


def test_all_healthy_flag_false_when_failures(collector, history):
    for _ in range(5):
        collector.record_failure("GET /bad")
    ep = HealthEndpoint(collector, history, host="127.0.0.1", port=19093)
    ep.start()
    time.sleep(0.05)
    try:
        with urllib.request.urlopen("http://127.0.0.1:19093/health") as resp:
            data = json.loads(resp.read())
        assert data["healthy"] is False
    finally:
        ep.stop()
