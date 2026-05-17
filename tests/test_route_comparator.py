"""Tests for routewatch.route_comparator."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from routewatch.route_comparator import RouteComparator, RouteComparison


@dataclass
class _FakeRoute:
    url: str


@pytest.fixture()
def comparator() -> RouteComparator:
    return RouteComparator()


def test_all_routes_unchanged(comparator: RouteComparator) -> None:
    routes = [_FakeRoute("http://a.com"), _FakeRoute("http://b.com")]
    result = comparator.compare(routes, routes)
    assert result.added == []
    assert result.removed == []
    assert sorted(result.unchanged) == ["http://a.com", "http://b.com"]
    assert not result.has_changes


def test_new_routes_detected(comparator: RouteComparator) -> None:
    prev = [_FakeRoute("http://a.com")]
    curr = [_FakeRoute("http://a.com"), _FakeRoute("http://b.com")]
    result = comparator.compare(prev, curr)
    assert result.added == ["http://b.com"]
    assert result.removed == []
    assert result.has_changes


def test_removed_routes_detected(comparator: RouteComparator) -> None:
    prev = [_FakeRoute("http://a.com"), _FakeRoute("http://b.com")]
    curr = [_FakeRoute("http://a.com")]
    result = comparator.compare(prev, curr)
    assert result.removed == ["http://b.com"]
    assert result.added == []
    assert result.has_changes


def test_added_and_removed_simultaneously(comparator: RouteComparator) -> None:
    prev = [_FakeRoute("http://old.com"), _FakeRoute("http://shared.com")]
    curr = [_FakeRoute("http://new.com"), _FakeRoute("http://shared.com")]
    result = comparator.compare(prev, curr)
    assert result.added == ["http://new.com"]
    assert result.removed == ["http://old.com"]
    assert result.unchanged == ["http://shared.com"]


def test_empty_previous(comparator: RouteComparator) -> None:
    curr = [_FakeRoute("http://a.com")]
    result = comparator.compare([], curr)
    assert result.added == ["http://a.com"]
    assert result.removed == []
    assert result.unchanged == []


def test_empty_current(comparator: RouteComparator) -> None:
    prev = [_FakeRoute("http://a.com")]
    result = comparator.compare(prev, [])
    assert result.removed == ["http://a.com"]
    assert result.added == []


def test_both_empty(comparator: RouteComparator) -> None:
    result = comparator.compare([], [])
    assert not result.has_changes
    assert result.total_unchanged == 0


def test_summary_no_changes(comparator: RouteComparator) -> None:
    routes = [_FakeRoute("http://a.com")]
    result = comparator.compare(routes, routes)
    assert "no changes" in result.summary()
    assert "1 routes" in result.summary()


def test_summary_with_changes(comparator: RouteComparator) -> None:
    prev = [_FakeRoute("http://old.com")]
    curr = [_FakeRoute("http://new.com")]
    result = comparator.compare(prev, curr)
    summary = result.summary()
    assert "+1 added" in summary
    assert "-1 removed" in summary


def test_counts(comparator: RouteComparator) -> None:
    prev = [_FakeRoute("http://a.com"), _FakeRoute("http://b.com")]
    curr = [_FakeRoute("http://b.com"), _FakeRoute("http://c.com")]
    result = comparator.compare(prev, curr)
    assert result.total_added == 1
    assert result.total_removed == 1
    assert result.total_unchanged == 1
