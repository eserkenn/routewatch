"""Groups routes by tag or prefix for aggregated reporting and filtering."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Protocol, Sequence


class HasTagsAndUrl(Protocol):
    url: str
    tags: List[str]


class RouteGrouper:
    """Organises routes into named groups by tag or URL prefix."""

    def __init__(self, routes: Sequence[HasTagsAndUrl]) -> None:
        self._routes = list(routes)

    def by_tag(self) -> Dict[str, List[HasTagsAndUrl]]:
        """Return a mapping of tag -> list of routes that carry that tag.

        Routes with no tags appear under the special key ``'untagged'``.
        """
        groups: Dict[str, List[HasTagsAndUrl]] = defaultdict(list)
        for route in self._routes:
            if route.tags:
                for tag in route.tags:
                    groups[tag].append(route)
            else:
                groups["untagged"].append(route)
        return dict(groups)

    def by_prefix(self, depth: int = 1) -> Dict[str, List[HasTagsAndUrl]]:
        """Return a mapping of URL prefix -> list of routes.

        *depth* controls how many path segments are used as the prefix key.
        For example with ``depth=1`` both ``/api/users`` and ``/api/orders``
        map to the key ``/api``.
        """
        if depth < 1:
            raise ValueError("depth must be >= 1")

        groups: Dict[str, List[HasTagsAndUrl]] = defaultdict(list)
        for route in self._routes:
            prefix = _url_prefix(route.url, depth)
            groups[prefix].append(route)
        return dict(groups)

    def group_names_by_tag(self) -> List[str]:
        """Return sorted list of tag group names."""
        return sorted(self.by_tag().keys())


def _url_prefix(url: str, depth: int) -> str:
    """Extract the first *depth* path segments from *url*."""
    # Strip scheme and host if present
    for scheme in ("https://", "http://"):
        if url.startswith(scheme):
            url = url[len(scheme):]
            # drop host
            slash = url.find("/")
            url = url[slash:] if slash != -1 else "/"
            break

    parts = [p for p in url.split("/") if p]
    prefix_parts = parts[:depth]
    return "/" + "/".join(prefix_parts) if prefix_parts else "/"
