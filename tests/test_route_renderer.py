"""Tests for routewatch.route_renderer."""

from dataclasses import dataclass
from routewatch.route_renderer import render_routes, RenderedTable


@dataclass
class _FakeRoute:
    url: str
    success_rate: float
    failure_rate: float
    average_latency_ms: float
    consecutive_failures: int


def _make_route(
    url="http://example.com/api",
    success_rate=1.0,
    failure_rate=0.0,
    average_latency_ms=42.5,
    consecutive_failures=0,
) -> _FakeRoute:
    return _FakeRoute(
        url=url,
        success_rate=success_rate,
        failure_rate=failure_rate,
        average_latency_ms=average_latency_ms,
        consecutive_failures=consecutive_failures,
    )


def test_render_returns_rendered_table():
    result = render_routes([_make_route()])
    assert isinstance(result, RenderedTable)


def test_as_text_contains_url():
    route = _make_route(url="http://example.com/health")
    text = render_routes([route]).as_text()
    assert "http://example.com/health" in text


def test_as_text_contains_success_percentage():
    route = _make_route(success_rate=0.95)
    text = render_routes([route]).as_text()
    assert "95.0%" in text


def test_as_text_contains_latency():
    route = _make_route(average_latency_ms=123.4)
    text = render_routes([route]).as_text()
    assert "123.4 ms" in text


def test_as_text_contains_consecutive_failures():
    route = _make_route(consecutive_failures=3)
    text = render_routes([route]).as_text()
    assert "3" in text


def test_footer_shows_healthy_count():
    routes = [
        _make_route(url="http://a.com", consecutive_failures=0),
        _make_route(url="http://b.com", consecutive_failures=2),
        _make_route(url="http://c.com", consecutive_failures=0),
    ]
    text = render_routes(routes).as_text()
    assert "2/3 routes healthy" in text


def test_empty_routes_renders_zero_counts():
    text = render_routes([]).as_text()
    assert "0/0 routes healthy" in text


def test_url_truncated_to_column_width():
    long_url = "http://" + "x" * 60
    route = _make_route(url=long_url)
    table = render_routes([route])
    for row in table.rows:
        # row must not exceed header width (separator length)
        assert len(row) == len(table.header.splitlines()[0])


def test_header_contains_column_labels():
    text = render_routes([]).as_text()
    assert "URL" in text
    assert "SUCCESS %" in text
    assert "AVG LATENCY" in text
    assert "CONSEC FAIL" in text
