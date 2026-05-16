"""Tests for routewatch.route_labels."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

import pytest

from routewatch.route_labels import (
    LabelSelector,
    RouteLabelIndex,
    filter_by_selector,
)


@dataclass
class _FakeRoute:
    url: str
    labels: Dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# LabelSelector
# ---------------------------------------------------------------------------

def test_empty_selector_matches_anything():
    sel = LabelSelector()
    assert sel.matches({"env": "prod", "team": "ops"})
    assert sel.matches({})


def test_selector_matches_exact_pair():
    sel = LabelSelector.from_dict({"env": "prod"})
    assert sel.matches({"env": "prod", "region": "eu"})


def test_selector_rejects_wrong_value():
    sel = LabelSelector.from_dict({"env": "prod"})
    assert not sel.matches({"env": "staging"})


def test_selector_requires_all_pairs():
    sel = LabelSelector.from_dict({"env": "prod", "team": "ops"})
    assert not sel.matches({"env": "prod"})
    assert sel.matches({"env": "prod", "team": "ops"})


def test_selector_missing_key_is_no_match():
    sel = LabelSelector.from_dict({"env": "prod"})
    assert not sel.matches({})


# ---------------------------------------------------------------------------
# RouteLabelIndex
# ---------------------------------------------------------------------------

@pytest.fixture()
def index():
    idx = RouteLabelIndex()
    idx.index_route("http://a.example/", {"env": "prod", "team": "ops"})
    idx.index_route("http://b.example/", {"env": "staging", "team": "ops"})
    idx.index_route("http://c.example/", {"env": "prod", "team": "dev"})
    return idx


def test_lookup_returns_matching_urls(index):
    urls = index.lookup("env", "prod")
    assert set(urls) == {"http://a.example/", "http://c.example/"}


def test_lookup_unknown_key_returns_empty(index):
    assert index.lookup("region", "eu") == []


def test_all_values_returns_distinct(index):
    values = index.all_values("env")
    assert set(values) == {"prod", "staging"}


# ---------------------------------------------------------------------------
# filter_by_selector
# ---------------------------------------------------------------------------

@pytest.fixture()
def routes():
    return [
        _FakeRoute("http://a.example/", {"env": "prod"}),
        _FakeRoute("http://b.example/", {"env": "staging"}),
        _FakeRoute("http://c.example/", {"env": "prod", "critical": "true"}),
    ]


def test_none_selector_returns_all(routes):
    assert filter_by_selector(routes, None) == routes


def test_filter_by_single_label(routes):
    sel = LabelSelector.from_dict({"env": "prod"})
    result = filter_by_selector(routes, sel)
    assert len(result) == 2
    assert all(r.labels["env"] == "prod" for r in result)


def test_filter_by_multiple_labels(routes):
    sel = LabelSelector.from_dict({"env": "prod", "critical": "true"})
    result = filter_by_selector(routes, sel)
    assert len(result) == 1
    assert result[0].url == "http://c.example/"


def test_filter_no_match_returns_empty(routes):
    sel = LabelSelector.from_dict({"env": "canary"})
    assert filter_by_selector(routes, sel) == []
