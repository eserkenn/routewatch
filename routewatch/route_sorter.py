"""Sort routes by various criteria for display and processing order."""

from __future__ import annotations

from typing import Callable, List, Protocol, runtime_checkable


@runtime_checkable
class HasUrlAndInterval(Protocol):
    url: str
    interval_seconds: int


class RouteSorter:
    """Sorts a list of route-like objects by configurable criteria."""

    # Supported sort keys and their extractor functions
    _KEYS: dict[str, Callable[[HasUrlAndInterval], object]] = {
        "url": lambda r: r.url,
        "interval": lambda r: r.interval_seconds,
    }

    def __init__(self, key: str = "url", reverse: bool = False) -> None:
        if key not in self._KEYS:
            raise ValueError(
                f"Unsupported sort key '{key}'. "
                f"Valid keys: {sorted(self._KEYS)}"
            )
        self._key = key
        self._reverse = reverse

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def sort(self, routes: List[HasUrlAndInterval]) -> List[HasUrlAndInterval]:
        """Return a new list of routes sorted by the configured key."""
        return sorted(
            routes,
            key=self._KEYS[self._key],
            reverse=self._reverse,
        )

    def sort_by_priority(self
        , routes: List[HasUrlAndInterval]
    ) -> List[HasUrlAndInterval]:
        """Sort by interval ascending (shortest interval = highest priority)."""
        return sorted(routes, key=lambda r: r.interval_seconds)

    @staticmethod
    def deduplicate(routes: List[HasUrlAndInterval]) -> List[HasUrlAndInterval]:
        """Remove duplicate routes by URL, preserving first occurrence order."""
        seen: set[str] = set()
        result: List[HasUrlAndInterval] = []
        for route in routes:
            if route.url not in seen:
                seen.add(route.url)
                result.append(route)
        return result
