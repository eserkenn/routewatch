"""Tag-based route filtering for selective monitoring and alerting."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from routewatch.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class TagFilter:
    """Determines whether a route should be included based on tag rules."""

    include: frozenset[str] = field(default_factory=frozenset)
    exclude: frozenset[str] = field(default_factory=frozenset)

    @classmethod
    def from_config(
        cls,
        include: Iterable[str] | None = None,
        exclude: Iterable[str] | None = None,
    ) -> "TagFilter":
        return cls(
            include=frozenset(include or []),
            exclude=frozenset(exclude or []),
        )

    def matches(self, tags: Iterable[str]) -> bool:
        """Return True if the given tags satisfy include/exclude rules.

        - If *include* is non-empty, the route must share at least one tag.
        - If *exclude* is non-empty, the route must share NO excluded tags.
        """
        tag_set = frozenset(tags)

        if self.exclude and tag_set & self.exclude:
            logger.debug("Route excluded by tags: %s", tag_set & self.exclude)
            return False

        if self.include and not (tag_set & self.include):
            logger.debug("Route not in include list; skipping.")
            return False

        return True


def filter_routes(routes: list, tag_filter: TagFilter) -> list:
    """Return only the routes whose tags satisfy *tag_filter*."""
    kept = [r for r in routes if tag_filter.matches(getattr(r, "tags", []))]
    logger.debug("Tag filter: %d/%d routes kept", len(kept), len(routes))
    return kept
