"""Alert suppressor: skip alerts for routes in maintenance windows."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import List, Optional

from routewatch.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class MaintenanceWindow:
    """A named time window during which alerts are suppressed for matching routes."""

    name: str
    route_pattern: str  # regex matched against route URL
    start_time: time    # wall-clock start (UTC)
    end_time: time      # wall-clock end (UTC)
    weekdays: List[int] = field(default_factory=lambda: list(range(7)))  # 0=Mon

    def matches_route(self, url: str) -> bool:
        return bool(re.search(self.route_pattern, url))

    def is_active(self, now: Optional[datetime] = None) -> bool:
        now = now or datetime.utcnow()
        if now.weekday() not in self.weekdays:
            return False
        current = now.time().replace(tzinfo=None)
        start = self.start_time
        end = self.end_time
        if start <= end:
            return start <= current <= end
        # overnight window e.g. 23:00 – 01:00
        return current >= start or current <= end


class AlertSuppressor:
    """Decides whether an alert should be suppressed due to a maintenance window."""

    def __init__(self, windows: Optional[List[MaintenanceWindow]] = None) -> None:
        self._windows: List[MaintenanceWindow] = windows or []

    def add_window(self, window: MaintenanceWindow) -> None:
        self._windows.append(window)

    def is_suppressed(self, url: str, now: Optional[datetime] = None) -> bool:
        """Return True if the alert for *url* should be suppressed right now."""
        for window in self._windows:
            if window.matches_route(url) and window.is_active(now):
                logger.debug(
                    "Alert suppressed for %s by maintenance window '%s'",
                    url,
                    window.name,
                )
                return True
        return False

    def active_windows(self, now: Optional[datetime] = None) -> List[MaintenanceWindow]:
        """Return all windows that are currently active."""
        return [w for w in self._windows if w.is_active(now)]
