"""Scores routes by overall health using a weighted combination of metrics."""

from dataclasses import dataclass
from typing import Protocol

from routewatch.metrics import RouteMetrics


class HasUrlAndMetrics(Protocol):
    url: str
    metrics: RouteMetrics


@dataclass(frozen=True)
class RouteScore:
    url: str
    score: float          # 0.0 (worst) – 1.0 (perfect)
    grade: str            # A / B / C / D / F
    reason: str


_GRADE_THRESHOLDS = [
    (0.90, "A"),
    (0.75, "B"),
    (0.60, "C"),
    (0.40, "D"),
    (0.00, "F"),
]


def _grade(score: float) -> str:
    for threshold, letter in _GRADE_THRESHOLDS:
        if score >= threshold:
            return letter
    return "F"


class RouteScorer:
    """Compute a composite health score for each route.

    Weights
    -------
    - success_rate   : 60 %
    - latency_score  : 40 %  (based on consecutive_failures acting as a proxy
                               for recent latency regressions)
    """

    SUCCESS_WEIGHT = 0.60
    LATENCY_WEIGHT = 0.40
    MAX_CONSECUTIVE_FAILURES_FOR_ZERO = 5

    def score_route(self, url: str, metrics: RouteMetrics) -> RouteScore:
        success = metrics.success_rate

        # Latency proxy: fewer consecutive failures → better latency score
        cf = min(metrics.consecutive_failures, self.MAX_CONSECUTIVE_FAILURES_FOR_ZERO)
        latency_score = 1.0 - (cf / self.MAX_CONSECUTIVE_FAILURES_FOR_ZERO)

        composite = (
            self.SUCCESS_WEIGHT * success
            + self.LATENCY_WEIGHT * latency_score
        )
        composite = round(max(0.0, min(1.0, composite)), 4)

        parts = []
        if success < 1.0:
            parts.append(f"success_rate={success:.0%}")
        if cf > 0:
            parts.append(f"consecutive_failures={cf}")
        reason = ", ".join(parts) if parts else "healthy"

        return RouteScore(url=url, score=composite, grade=_grade(composite), reason=reason)

    def score_all(self, routes: list) -> list[RouteScore]:
        """Score a list of objects that expose .url and .metrics."""
        return [self.score_route(r.url, r.metrics) for r in routes]
