"""Tracks configuration changes to routes over time."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class ChangelogEntry:
    route_url: str
    field: str
    old_value: Optional[str]
    new_value: Optional[str]
    changed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "route_url": self.route_url,
            "field": self.field,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "changed_at": self.changed_at,
        }


class RouteChangelog:
    """Records field-level changes to route configurations."""

    def __init__(self, max_entries: int = 200) -> None:
        self._max = max_entries
        self._entries: List[ChangelogEntry] = []

    def record(self, route_url: str, field: str, old_value: Optional[str], new_value: Optional[str]) -> ChangelogEntry:
        entry = ChangelogEntry(
            route_url=route_url,
            field=field,
            old_value=old_value,
            new_value=new_value,
        )
        self._entries.append(entry)
        if len(self._entries) > self._max:
            self._entries = self._entries[-self._max:]
        return entry

    def get(self, route_url: Optional[str] = None) -> List[ChangelogEntry]:
        if route_url is None:
            return list(self._entries)
        return [e for e in self._entries if e.route_url == route_url]

    def clear(self, route_url: Optional[str] = None) -> None:
        if route_url is None:
            self._entries.clear()
        else:
            self._entries = [e for e in self._entries if e.route_url != route_url]

    def diff_and_record(self, route_url: str, old: Dict[str, str], new: Dict[str, str]) -> List[ChangelogEntry]:
        """Compare two field dicts and record any changes."""
        recorded: List[ChangelogEntry] = []
        all_keys = set(old) | set(new)
        for key in sorted(all_keys):
            ov, nv = old.get(key), new.get(key)
            if ov != nv:
                recorded.append(self.record(route_url, key, ov, nv))
        return recorded
