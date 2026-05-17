"""Assigns and manages priority levels for monitored routes."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, List, Protocol


class Priority(IntEnum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4

    @classmethod
    def from_str(cls, value: str) -> "Priority":
        mapping = {
            "critical": cls.CRITICAL,
            "high": cls.HIGH,
            "medium": cls.MEDIUM,
            "low": cls.LOW,
        }
        key = value.strip().lower()
        if key not in mapping:
            raise ValueError(
                f"Unknown priority {value!r}. Valid values: {list(mapping)}"
            )
        return mapping[key]

    def label(self) -> str:
        return self.name.capitalize()


class HasUrl(Protocol):
    url: str


@dataclass
class RoutePriorityStore:
    """Stores explicit priority overrides keyed by route URL."""

    _store: Dict[str, Priority] = field(default_factory=dict)

    def set(self, url: str, priority: Priority) -> None:
        """Assign a priority to a route URL."""
        self._store[url.rstrip("/")] = priority

    def get(self, url: str, default: Priority = Priority.MEDIUM) -> Priority:
        """Return the priority for a URL, falling back to *default*."""
        return self._store.get(url.rstrip("/"), default)

    def remove(self, url: str) -> bool:
        """Remove an explicit override.  Returns True if it existed."""
        return self._store.pop(url.rstrip("/"), None) is not None

    def all(self) -> Dict[str, Priority]:
        """Return a copy of all stored overrides."""
        return dict(self._store)

    def sorted_routes(self, routes: List[HasUrl]) -> List[HasUrl]:
        """Return *routes* ordered from highest (CRITICAL) to lowest priority."""
        return sorted(routes, key=lambda r: self.get(r.url).value)
