"""Tests for routewatch.route_grouper."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import pytest

from routewatch.route_grouper import RouteGrouper, _url_prefix


@dataclass
class _FakeRoute:
    url: str
    tags: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# by_tag
# ---------------------------------------------------------------------------

def test_by_tag_groups_correctly():
    routes = [
        _FakeRoute("http://example.com/a", tags=["web", "critical"]),
        _FakeRoute("http://example.com/b", tags=["web"]),
        _FakeRoute("http://example.com/c", tags=["internal"]),
    ]
    groups = RouteGrouper(routes).by_tag()
    assert set(groups["web"]) == {routes[0], routes[1]}
    assert groups["critical"] == [routes[0]]
    assert groups["internal"] == [routes[2]]


def test_untagged_routes_grouped_under_untagged_key():
    routes = [
        _FakeRoute("http://example.com/x"),
        _FakeRoute("http://example.com/y", tags=["api"]),
    ]
    groups = RouteGrouper(routes).by_tag()
    assert routes[0] in groups["untagged"]
    assert routes[1] not in groups.get("untagged", [])


def test_by_tag_empty_routes_returns_empty_dict():
    assert RouteGrouper([]).by_tag() == {}


# ---------------------------------------------------------------------------
# by_prefix
# ---------------------------------------------------------------------------

def test_by_prefix_depth_1():
    routes = [
        _FakeRoute("http://example.com/api/users"),
        _FakeRoute("http://example.com/api/orders"),
        _FakeRoute("http://example.com/health"),
    ]
    groups = RouteGrouper(routes).by_prefix(depth=1)
    assert set(groups["/api"]) == {routes[0], routes[1]}
    assert groups["/health"] == [routes[2]]


def test_by_prefix_depth_2():
    routes = [
        _FakeRoute("http://example.com/api/v1/users"),
        _FakeRoute("http://example.com/api/v2/users"),
    ]
    groups = RouteGrouper(routes).by_prefix(depth=2)
    assert "/api/v1" in groups
    assert "/api/v2" in groups


def test_by_prefix_invalid_depth_raises():
    with pytest.raises(ValueError, match="depth must be"):
        RouteGrouper([]).by_prefix(depth=0)


def test_by_prefix_root_url():
    routes = [_FakeRoute("http://example.com/")]
    groups = RouteGrouper(routes).by_prefix(depth=1)
    assert "/" in groups


# ---------------------------------------------------------------------------
# group_names_by_tag
# ---------------------------------------------------------------------------

def test_group_names_by_tag_sorted():
    routes = [
        _FakeRoute("http://example.com/a", tags=["zebra"]),
        _FakeRoute("http://example.com/b", tags=["alpha"]),
    ]
    names = RouteGrouper(routes).group_names_by_tag()
    assert names == ["alpha", "zebra"]


# ---------------------------------------------------------------------------
# _url_prefix helper
# ---------------------------------------------------------------------------

def test_url_prefix_strips_scheme_and_host():
    assert _url_prefix("https://example.com/api/users", 1) == "/api"


def test_url_prefix_plain_path():
    assert _url_prefix("/metrics/system", 2) == "/metrics/system"
