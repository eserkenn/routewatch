"""Route muter — temporarily silence alerts for specific routes."""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class MuteEntry:
    route_url: str
    muted_until: datetime
    reason: str = ""

    def is_active(self, now: Optional[datetime] = None) -> bool:
        now = now or datetime.now(timezone.utc)
        return now < self.muted_until


class RouteMuter:
    """Thread-safe registry of muted routes."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._entries: Dict[str, MuteEntry] = {}

    def mute(self, route_url: str, until: datetime, reason: str = "") -> None:
        """Add or update a mute entry for *route_url*."""
        with self._lock:
            self._entries[route_url] = MuteEntry(
                route_url=route_url, muted_until=until, reason=reason
            )

    def unmute(self, route_url: str) -> bool:
        """Remove a mute entry.  Returns True if the entry existed."""
        with self._lock:
            return self._entries.pop(route_url, None) is not None

    def is_muted(self, route_url: str, now: Optional[datetime] = None) -> bool:
        """Return True if *route_url* currently has an active mute."""
        with self._lock:
            entry = self._entries.get(route_url)
        if entry is None:
            return False
        return entry.is_active(now)

    def active_mutes(self, now: Optional[datetime] = None) -> List[MuteEntry]:
        """Return all currently active mute entries."""
        now = now or datetime.now(timezone.utc)
        with self._lock:
            snapshot = list(self._entries.values())
        return [e for e in snapshot if e.is_active(now)]

    def purge_expired(self, now: Optional[datetime] = None) -> int:
        """Remove expired entries.  Returns the number removed."""
        now = now or datetime.now(timezone.utc)
        with self._lock:
            expired = [url for url, e in self._entries.items() if not e.is_active(now)]
            for url in expired:
                del self._entries[url]
        return len(expired)
