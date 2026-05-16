"""Tests for routewatch.route_sorter."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from routewatch.route_sorter import RouteSorter


@dataclass
class _FakeRoute:
    url: str
    interval_seconds: int = 60


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def routes() -> list[_FakeRoute]:
    return [
        _FakeRoute(url="https://example.com/c", interval_seconds=30),
        _FakeRoute(url="https://example.com/a", interval_seconds=60),
        _FakeRoute(url="https://example.com/b", interval_seconds=10),
    ]


# ---------------------------------------------------------------------------
# Constructor validation
# ---------------------------------------------------------------------------


def test_invalid_key_raises() -> None:
    with pytest.raises(ValueError, match="Unsupported sort key"):
        RouteSorter(key="nonexistent")


# ---------------------------------------------------------------------------
# sort() — by url
# ---------------------------------------------------------------------------


def test_sort_by_url_ascending(routes: list[_FakeRoute]) -> None:
    sorter = RouteSorter(key="url")
    result = sorter.sort(routes)
    urls = [r.url for r in result]
    assert urls == sorted(urls)


def test_sort_by_url_descending(routes: list[_FakeRoute]) -> None:
    sorter = RouteSorter(key="url", reverse=True)
    result = sorter.sort(routes)
    urls = [r.url for r in result]
    assert urls == sorted(urls, reverse=True)


# ---------------------------------------------------------------------------
# sort() — by interval
# ---------------------------------------------------------------------------


def test_sort_by_interval_ascending(routes: list[_FakeRoute]) -> None:
    sorter = RouteSorter(key="interval")
    result = sorter.sort(routes)
    intervals = [r.interval_seconds for r in result]
    assert intervals == sorted(intervals)


def test_sort_by_interval_descending(routes: list[_FakeRoute]) -> None:
    sorter = RouteSorter(key="interval", reverse=True)
    result = sorter.sort(routes)
    intervals = [r.interval_seconds for r in result]
    assert intervals == sorted(intervals, reverse=True)


# ---------------------------------------------------------------------------
# sort_by_priority()
# ---------------------------------------------------------------------------


def test_sort_by_priority_shortest_first(routes: list[_FakeRoute]) -> None:
    sorter = RouteSorter()
    result = sorter.sort_by_priority(routes)
    assert result[0].interval_seconds == 10
    assert result[-1].interval_seconds == 60


def test_sort_does_not_mutate_original(routes: list[_FakeRoute]) -> None:
    original_urls = [r.url for r in routes]
    RouteSorter().sort(routes)
    assert [r.url for r in routes] == original_urls


# ---------------------------------------------------------------------------
# deduplicate()
# ---------------------------------------------------------------------------


def test_deduplicate_removes_duplicate_urls() -> None:
    dupes = [
        _FakeRoute(url="https://a.com"),
        _FakeRoute(url="https://b.com"),
        _FakeRoute(url="https://a.com"),
    ]
    result = RouteSorter.deduplicate(dupes)
    assert len(result) == 2
    assert result[0].url == "https://a.com"
    assert result[1].url == "https://b.com"


def test_deduplicate_preserves_order() -> None:
    unique = [
        _FakeRoute(url="https://z.com"),
        _FakeRoute(url="https://a.com"),
    ]
    assert RouteSorter.deduplicate(unique) == unique


def test_deduplicate_empty_list() -> None:
    assert RouteSorter.deduplicate([]) == []
