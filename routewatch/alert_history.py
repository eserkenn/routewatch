"""Persistent alert history for tracking sent alerts per route."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from routewatch.logging_config import get_logger

logger = get_logger(__name__)

DEFAULT_PATH = ".routewatch_alert_history.json"


@dataclass
class AlertRecord:
    route_url: str
    sent_at: str  # ISO-8601
    reason: str
    latency_ms: Optional[float] = None


@dataclass
class AlertHistory:
    _path: str = field(default=DEFAULT_PATH, repr=False)
    _records: List[AlertRecord] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        self._load()

    def record(self, route_url: str, reason: str, latency_ms: Optional[float] = None) -> None:
        """Append an alert record and persist to disk."""
        entry = AlertRecord(
            route_url=route_url,
            sent_at=datetime.now(timezone.utc).isoformat(),
            reason=reason,
            latency_ms=latency_ms,
        )
        self._records.append(entry)
        self._save()
        logger.debug("Alert recorded for %s: %s", route_url, reason)

    def get(self, route_url: Optional[str] = None) -> List[AlertRecord]:
        """Return all records, or only those matching route_url."""
        if route_url is None:
            return list(self._records)
        return [r for r in self._records if r.route_url == route_url]

    def clear(self, route_url: Optional[str] = None) -> None:
        """Remove records for a specific route, or all records."""
        if route_url is None:
            self._records.clear()
        else:
            self._records = [r for r in self._records if r.route_url != route_url]
        self._save()

    def _save(self) -> None:
        try:
            data = [
                {
                    "route_url": r.route_url,
                    "sent_at": r.sent_at,
                    "reason": r.reason,
                    "latency_ms": r.latency_ms,
                }
                for r in self._records
            ]
            with open(self._path, "w") as fh:
                json.dump(data, fh, indent=2)
        except OSError as exc:
            logger.warning("Could not save alert history: %s", exc)

    def _load(self) -> None:
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path) as fh:
                data = json.load(fh)
            self._records = [
                AlertRecord(
                    route_url=d["route_url"],
                    sent_at=d["sent_at"],
                    reason=d["reason"],
                    latency_ms=d.get("latency_ms"),
                )
                for d in data
            ]
            logger.debug("Loaded %d alert record(s) from %s", len(self._records), self._path)
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            logger.warning("Could not load alert history: %s", exc)
