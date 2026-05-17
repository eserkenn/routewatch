"""Tests for RouteScorer."""

import pytest

from routewatch.metrics import MetricsCollector
from routewatch.route_scorer import RouteScore, RouteScorer


@pytest.fixture()
def scorer() -> RouteScorer:
    return RouteScorer()


@pytest.fixture()
def collector() -> MetricsCollector:
    return MetricsCollector()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _metrics_with(collector: MetricsCollector, url: str, successes: int, failures: int):
    for _ in range(successes):
        collector.record_success(url)
    for _ in range(failures):
        collector.record_failure(url)
    return collector.get(url)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_perfect_route_scores_one(scorer, collector):
    m = _metrics_with(collector, "http://a", successes=10, failures=0)
    result = scorer.score_route("http://a", m)
    assert result.score == 1.0
    assert result.grade == "A"
    assert result.reason == "healthy"


def test_all_failures_scores_near_zero(scorer, collector):
    m = _metrics_with(collector, "http://b", successes=0, failures=10)
    result = scorer.score_route("http://b", m)
    assert result.score < 0.2
    assert result.grade == "F"


def test_grade_b_range(scorer, collector):
    # 80 % success, no latency penalty → 0.60*0.8 + 0.40*1.0 = 0.88 → A
    m = _metrics_with(collector, "http://c", successes=8, failures=2)
    result = scorer.score_route("http://c", m)
    # consecutive_failures resets on success, so last recorded is success → cf=0
    assert result.grade in ("A", "B")


def test_reason_includes_success_rate_when_below_100(scorer, collector):
    m = _metrics_with(collector, "http://d", successes=5, failures=5)
    result = scorer.score_route("http://d", m)
    assert "success_rate" in result.reason


def test_reason_healthy_when_perfect(scorer, collector):
    m = _metrics_with(collector, "http://e", successes=5, failures=0)
    result = scorer.score_route("http://e", m)
    assert result.reason == "healthy"


def test_score_clamped_between_0_and_1(scorer, collector):
    m = _metrics_with(collector, "http://f", successes=0, failures=100)
    result = scorer.score_route("http://f", m)
    assert 0.0 <= result.score <= 1.0


def test_score_all_returns_one_entry_per_route(scorer):
    class FakeRoute:
        def __init__(self, url, m):
            self.url = url
            self.metrics = m

    c = MetricsCollector()
    routes = [
        FakeRoute("http://x", _metrics_with(c, "http://x", 3, 0)),
        FakeRoute("http://y", _metrics_with(c, "http://y", 1, 2)),
    ]
    results = scorer.score_all(routes)
    assert len(results) == 2
    assert all(isinstance(r, RouteScore) for r in results)


def test_url_preserved_in_score(scorer, collector):
    m = _metrics_with(collector, "http://myservice/api", successes=1, failures=0)
    result = scorer.score_route("http://myservice/api", m)
    assert result.url == "http://myservice/api"
