"""Tests for routewatch.history.LatencyHistory."""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from routewatch.history import LatencyHistory


@pytest.fixture()
def store(tmp_path: Path) -> LatencyHistory:
    return LatencyHistory(path=tmp_path / "hist.json", max_entries=5)


def test_record_and_get(store: LatencyHistory) -> None:
    store.record("GET /health", 42.0)
    store.record("GET /health", 55.5)
    samples = store.get("GET /health")
    assert samples == [42.0, 55.5]


def test_unknown_route_returns_empty(store: LatencyHistory) -> None:
    assert store.get("GET /missing") == []


def test_max_entries_enforced(store: LatencyHistory) -> None:
    for i in range(10):
        store.record("r", float(i))
    samples = store.get("r")
    assert len(samples) == 5
    assert samples == [5.0, 6.0, 7.0, 8.0, 9.0]


def test_persists_to_disk(tmp_path: Path) -> None:
    path = tmp_path / "hist.json"
    s1 = LatencyHistory(path=path)
    s1.record("GET /api", 10.0)

    s2 = LatencyHistory(path=path)
    assert s2.get("GET /api") == [10.0]


def test_clear_single_route(store: LatencyHistory) -> None:
    store.record("r1", 1.0)
    store.record("r2", 2.0)
    store.clear("r1")
    assert store.get("r1") == []
    assert store.get("r2") == [2.0]


def test_clear_all(store: LatencyHistory) -> None:
    store.record("r1", 1.0)
    store.record("r2", 2.0)
    store.clear()
    assert store.get("r1") == []
    assert store.get("r2") == []


def test_corrupted_file_returns_empty(tmp_path: Path) -> None:
    path = tmp_path / "hist.json"
    path.write_text("not valid json")
    store = LatencyHistory(path=path)
    assert store.get("anything") == []


def test_thread_safety(store: LatencyHistory) -> None:
    errors: list[Exception] = []

    def worker(n: int) -> None:
        try:
            for _ in range(20):
                store.record(f"route-{n % 3}", float(n))
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
