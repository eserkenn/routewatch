"""Tests for routewatch.route_validator."""

import pytest

from routewatch.config import RouteConfig
from routewatch.route_validator import (
    ValidationResult,
    validate_route,
    validate_routes,
)


def _make_route(**overrides) -> RouteConfig:
    defaults = dict(
        name="test-route",
        url="http://example.com/health",
        method="GET",
        interval_seconds=30,
        timeout_seconds=5.0,
        expected_status=[200],
        latency_threshold_ms=None,
        tags=[],
        headers={},
    )
    defaults.update(overrides)
    return RouteConfig(**defaults)


def test_valid_route_has_no_errors():
    result = validate_route(_make_route())
    assert result.valid
    assert result.errors == []


def test_invalid_url_flagged():
    result = validate_route(_make_route(url="not-a-url"))
    assert not result.valid
    fields = [e.field for e in result.errors]
    assert "url" in fields


def test_empty_url_flagged():
    result = validate_route(_make_route(url=""))
    assert not result.valid


def test_invalid_method_flagged():
    result = validate_route(_make_route(method="FETCH"))
    assert not result.valid
    assert any(e.field == "method" for e in result.errors)


def test_valid_methods_accepted():
    for method in ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"):
        result = validate_route(_make_route(method=method))
        assert result.valid, f"Expected {method} to be valid"


def test_negative_interval_flagged():
    result = validate_route(_make_route(interval_seconds=-1))
    assert not result.valid
    assert any(e.field == "interval_seconds" for e in result.errors)


def test_zero_timeout_flagged():
    result = validate_route(_make_route(timeout_seconds=0))
    assert not result.valid
    assert any(e.field == "timeout_seconds" for e in result.errors)


def test_negative_latency_threshold_flagged():
    result = validate_route(_make_route(latency_threshold_ms=-100))
    assert not result.valid
    assert any(e.field == "latency_threshold_ms" for e in result.errors)


def test_none_latency_threshold_is_valid():
    result = validate_route(_make_route(latency_threshold_ms=None))
    assert result.valid


def test_invalid_status_code_flagged():
    result = validate_route(_make_route(expected_status=[999]))
    assert not result.valid
    assert any(e.field == "expected_status" for e in result.errors)


def test_empty_expected_status_flagged():
    result = validate_route(_make_route(expected_status=[]))
    assert not result.valid


def test_validate_routes_returns_only_invalid(caplog):
    good = _make_route(name="good")
    bad = _make_route(name="bad", url="oops", interval_seconds=-5)
    results = validate_routes([good, bad])
    assert len(results) == 1
    assert any(e.route_name == "bad" for e in results[0].errors)


def test_validation_error_str():
    result = validate_route(_make_route(url="bad"))
    assert not result.valid
    err_str = str(result.errors[0])
    assert "test-route" in err_str
    assert "url" in err_str
