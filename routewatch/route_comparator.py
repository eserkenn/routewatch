"""Compare two sets of routes and produce a structured diff summary."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Protocol


class HasUrl(Protocol):
    url: str


@dataclass(frozen=True)
class RouteComparison:
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)

    @property
    def total_added(self) -> int:
        return len(self.added)

    @property
    def total_removed(self) -> int:
        return len(self.removed)

    @property
    def total_unchanged(self) -> int:
        return len(self.unchanged)

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.removed)

    def summary(self) -> str:
        parts = []
        if self.added:
            parts.append(f"+{self.total_added} added")
        if self.removed:
            parts.append(f"-{self.total_removed} removed")
        if not parts:
            return f"no changes ({self.total_unchanged} routes)"
        unchanged_note = f"{self.total_unchanged} unchanged"
        return ", ".join(parts) + f"; {unchanged_note}"


class RouteComparator:
    """Compare two collections of routes by URL."""

    def compare(
        self,
        previous: Iterable[HasUrl],
        current: Iterable[HasUrl],
    ) -> RouteComparison:
        prev_urls = {r.url for r in previous}
        curr_urls = {r.url for r in current}

        added = sorted(curr_urls - prev_urls)
        removed = sorted(prev_urls - curr_urls)
        unchanged = sorted(prev_urls & curr_urls)

        return RouteComparison(
            added=added,
            removed=removed,
            unchanged=unchanged,
        )
