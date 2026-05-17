"""Tests for routewatch.route_priority."""
import pytest
from dataclasses import dataclass

from routewatch.route_priority import Priority, RoutePriorityStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@dataclass
class _FakeRoute:
    url: str


@pytest.fixture()
def store() -> RoutePriorityStore:
    return RoutePriorityStore()


# ---------------------------------------------------------------------------
# Priority enum
# ---------------------------------------------------------------------------

def test_from_str_known_values():
    assert Priority.from_str("critical") is Priority.CRITICAL
    assert Priority.from_str("HIGH") is Priority.HIGH
    assert Priority.from_str("medium") is Priority.MEDIUM
    assert Priority.from_str("low") is Priority.LOW


def test_from_str_unknown_raises():
    with pytest.raises(ValueError, match="Unknown priority"):
        Priority.from_str("urgent")


def test_ordering_critical_less_than_low():
    assert Priority.CRITICAL < Priority.LOW


def test_label_is_capitalised():
    assert Priority.HIGH.label() == "High"


# ---------------------------------------------------------------------------
# RoutePriorityStore
# ---------------------------------------------------------------------------

def test_default_priority_is_medium(store):
    assert store.get("https://example.com/api") is Priority.MEDIUM


def test_set_and_get_priority(store):
    store.set("https://example.com/api", Priority.CRITICAL)
    assert store.get("https://example.com/api") is Priority.CRITICAL


def test_trailing_slash_normalised(store):
    store.set("https://example.com/api/", Priority.HIGH)
    assert store.get("https://example.com/api") is Priority.HIGH


def test_remove_existing_entry(store):
    store.set("https://example.com/x", Priority.LOW)
    removed = store.remove("https://example.com/x")
    assert removed is True
    assert store.get("https://example.com/x") is Priority.MEDIUM


def test_remove_nonexistent_returns_false(store):
    assert store.remove("https://example.com/missing") is False


def test_all_returns_copy(store):
    store.set("https://a.com", Priority.HIGH)
    snapshot = store.all()
    snapshot["https://b.com"] = Priority.LOW  # mutating copy should not affect store
    assert "https://b.com" not in store.all()


def test_sorted_routes_orders_by_priority(store):
    routes = [
        _FakeRoute("https://example.com/low"),
        _FakeRoute("https://example.com/critical"),
        _FakeRoute("https://example.com/high"),
    ]
    store.set("https://example.com/low", Priority.LOW)
    store.set("https://example.com/critical", Priority.CRITICAL)
    store.set("https://example.com/high", Priority.HIGH)

    sorted_routes = store.sorted_routes(routes)
    urls = [r.url for r in sorted_routes]
    assert urls == [
        "https://example.com/critical",
        "https://example.com/high",
        "https://example.com/low",
    ]


def test_sorted_routes_uses_default_for_unset(store):
    routes = [
        _FakeRoute("https://example.com/a"),  # default MEDIUM
        _FakeRoute("https://example.com/b"),  # CRITICAL
    ]
    store.set("https://example.com/b", Priority.CRITICAL)
    sorted_routes = store.sorted_routes(routes)
    assert sorted_routes[0].url == "https://example.com/b"
