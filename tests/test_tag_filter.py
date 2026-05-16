"""Tests for routewatch.tag_filter."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import pytest

from routewatch.tag_filter import TagFilter, filter_routes


@dataclass
class _FakeRoute:
    name: str
    tags: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# TagFilter.matches
# ---------------------------------------------------------------------------

def test_empty_filter_matches_anything():
    tf = TagFilter.from_config()
    assert tf.matches(["prod", "critical"]) is True
    assert tf.matches([]) is True


def test_include_single_tag_match():
    tf = TagFilter.from_config(include=["prod"])
    assert tf.matches(["prod", "api"]) is True


def test_include_single_tag_no_match():
    tf = TagFilter.from_config(include=["prod"])
    assert tf.matches(["staging"]) is False


def test_exclude_blocks_matching_tag():
    tf = TagFilter.from_config(exclude=["internal"])
    assert tf.matches(["internal", "api"]) is False


def test_exclude_allows_non_matching_tag():
    tf = TagFilter.from_config(exclude=["internal"])
    assert tf.matches(["prod", "api"]) is True


def test_include_and_exclude_combined_passes():
    tf = TagFilter.from_config(include=["prod"], exclude=["internal"])
    assert tf.matches(["prod", "api"]) is True


def test_include_and_exclude_combined_blocked_by_exclude():
    tf = TagFilter.from_config(include=["prod"], exclude=["internal"])
    assert tf.matches(["prod", "internal"]) is False


def test_include_and_exclude_combined_blocked_by_include():
    tf = TagFilter.from_config(include=["prod"], exclude=["internal"])
    assert tf.matches(["staging"]) is False


# ---------------------------------------------------------------------------
# filter_routes
# ---------------------------------------------------------------------------

@pytest.fixture()
def routes():
    return [
        _FakeRoute("home", ["prod", "public"]),
        _FakeRoute("admin", ["prod", "internal"]),
        _FakeRoute("health", ["staging"]),
        _FakeRoute("no-tags"),
    ]


def test_filter_routes_include(routes):
    tf = TagFilter.from_config(include=["prod"])
    result = filter_routes(routes, tf)
    assert [r.name for r in result] == ["home", "admin"]


def test_filter_routes_exclude(routes):
    tf = TagFilter.from_config(exclude=["internal"])
    result = filter_routes(routes, tf)
    names = [r.name for r in result]
    assert "admin" not in names
    assert "home" in names


def test_filter_routes_empty_filter_keeps_all(routes):
    tf = TagFilter.from_config()
    assert filter_routes(routes, tf) == routes


def test_filter_routes_no_match_returns_empty(routes):
    tf = TagFilter.from_config(include=["nonexistent"])
    assert filter_routes(routes, tf) == []
