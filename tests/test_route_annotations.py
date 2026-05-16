"""Tests for RouteAnnotations."""
import pytest
from routewatch.route_annotations import Annotation, RouteAnnotations


@pytest.fixture
def store() -> RouteAnnotations:
    return RouteAnnotations()


def test_initial_store_is_empty(store: RouteAnnotations) -> None:
    assert store.all() == {}


def test_add_returns_annotation(store: RouteAnnotations) -> None:
    ann = store.add("http://example.com", "looks slow", "alice")
    assert isinstance(ann, Annotation)
    assert ann.route_url == "http://example.com"
    assert ann.note == "looks slow"
    assert ann.author == "alice"


def test_get_returns_added_annotations(store: RouteAnnotations) -> None:
    store.add("http://example.com", "note one", "alice")
    store.add("http://example.com", "note two", "bob")
    results = store.get("http://example.com")
    assert len(results) == 2
    assert results[0].note == "note one"
    assert results[1].note == "note two"


def test_get_unknown_route_returns_empty(store: RouteAnnotations) -> None:
    assert store.get("http://unknown.example") == []


def test_delete_removes_by_index(store: RouteAnnotations) -> None:
    store.add("http://example.com", "first", "alice")
    store.add("http://example.com", "second", "bob")
    removed = store.delete("http://example.com", 0)
    assert removed is True
    remaining = store.get("http://example.com")
    assert len(remaining) == 1
    assert remaining[0].note == "second"


def test_delete_invalid_index_returns_false(store: RouteAnnotations) -> None:
    store.add("http://example.com", "only", "alice")
    assert store.delete("http://example.com", 99) is False


def test_clear_specific_route(store: RouteAnnotations) -> None:
    store.add("http://a.com", "note", "alice")
    store.add("http://b.com", "note", "bob")
    store.clear("http://a.com")
    assert store.get("http://a.com") == []
    assert len(store.get("http://b.com")) == 1


def test_clear_all(store: RouteAnnotations) -> None:
    store.add("http://a.com", "note", "alice")
    store.add("http://b.com", "note", "bob")
    store.clear()
    assert store.all() == {}


def test_to_dict_contains_expected_keys(store: RouteAnnotations) -> None:
    ann = store.add("http://example.com", "check this", "carol")
    d = ann.to_dict()
    assert set(d.keys()) == {"route_url", "note", "author", "created_at"}


def test_created_at_is_iso_format(store: RouteAnnotations) -> None:
    ann = store.add("http://example.com", "timing out", "dave")
    # Should not raise
    from datetime import datetime
    datetime.fromisoformat(ann.created_at)
