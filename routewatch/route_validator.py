"""Validates RouteConfig entries for correctness before scheduling."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

from routewatch.config import RouteConfig
from routewatch.logging_config import get_logger

logger = get_logger(__name__)

_URL_RE = re.compile(r"^https?://[^\s]+$")
_VALID_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}


@dataclass
class ValidationError:
    route_name: str
    field: str
    message: str

    def __str__(self) -> str:
        return f"[{self.route_name}] {self.field}: {self.message}"


@dataclass
class ValidationResult:
    errors: List[ValidationError] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return len(self.errors) == 0

    def add(self, route_name: str, field_name: str, message: str) -> None:
        self.errors.append(ValidationError(route_name, field_name, message))


def validate_route(route: RouteConfig) -> ValidationResult:
    """Validate a single RouteConfig and return a ValidationResult."""
    result = ValidationResult()
    name = route.name or "<unnamed>"

    if not route.url or not _URL_RE.match(route.url):
        result.add(name, "url", f"Invalid or missing URL: {route.url!r}")

    if route.method.upper() not in _VALID_METHODS:
        result.add(name, "method", f"Unsupported HTTP method: {route.method!r}")

    if route.interval_seconds <= 0:
        result.add(name, "interval_seconds", "Must be a positive integer")

    if route.timeout_seconds <= 0:
        result.add(name, "timeout_seconds", "Must be a positive number")

    if route.latency_threshold_ms is not None and route.latency_threshold_ms <= 0:
        result.add(name, "latency_threshold_ms", "Must be a positive number if set")

    if not route.expected_status or not isinstance(route.expected_status, list):
        result.add(name, "expected_status", "Must be a non-empty list of status codes")
    else:
        for code in route.expected_status:
            if not isinstance(code, int) or not (100 <= code <= 599):
                result.add(name, "expected_status", f"Invalid status code: {code!r}")

    return result


def validate_routes(routes: List[RouteConfig]) -> List[ValidationResult]:
    """Validate all routes. Logs and returns results with errors only."""
    results = []
    for route in routes:
        result = validate_route(route)
        if not result.valid:
            for err in result.errors:
                logger.warning("Route validation error: %s", err)
            results.append(result)
    return results
