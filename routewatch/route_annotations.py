"""Route annotation support — attach freeform notes to monitored routes."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class Annotation:
    route_url: str
    note: str
    author: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "route_url": self.route_url,
            "note": self.note,
            "author": self.author,
            "created_at": self.created_at,
        }


class RouteAnnotations:
    """In-memory store for route annotations."""

    def __init__(self) -> None:
        self._store: Dict[str, List[Annotation]] = {}

    def add(self, route_url: str, note: str, author: str) -> Annotation:
        annotation = Annotation(route_url=route_url, note=note, author=author)
        self._store.setdefault(route_url, []).append(annotation)
        return annotation

    def get(self, route_url: str) -> List[Annotation]:
        return list(self._store.get(route_url, []))

    def delete(self, route_url: str, index: int) -> bool:
        entries = self._store.get(route_url, [])
        if 0 <= index < len(entries):
            entries.pop(index)
            return True
        return False

    def all(self) -> Dict[str, List[Annotation]]:
        return {url: list(notes) for url, notes in self._store.items()}

    def clear(self, route_url: Optional[str] = None) -> None:
        if route_url is None:
            self._store.clear()
        else:
            self._store.pop(route_url, None)
