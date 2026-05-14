"""Persistent latency history store backed by a simple JSON file."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Dict, List

from routewatch.logging_config import get_logger

logger = get_logger(__name__)

_DEFAULT_MAX_ENTRIES = 500


class LatencyHistory:
    """Thread-safe, file-backed store of per-route latency samples (ms)."""

    def __init__(
        self,
        path: str | Path = "latency_history.json",
        max_entries: int = _DEFAULT_MAX_ENTRIES,
    ) -> None:
        self._path = Path(path)
        self._max_entries = max_entries
        self._lock = threading.Lock()
        self._data: Dict[str, List[float]] = self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record(self, route_id: str, latency_ms: float) -> None:
        """Append *latency_ms* for *route_id* and persist to disk."""
        with self._lock:
            bucket = self._data.setdefault(route_id, [])
            bucket.append(latency_ms)
            if len(bucket) > self._max_entries:
                self._data[route_id] = bucket[-self._max_entries :]
            self._save()

    def get(self, route_id: str) -> List[float]:
        """Return a copy of the stored samples for *route_id*."""
        with self._lock:
            return list(self._data.get(route_id, []))

    def clear(self, route_id: str | None = None) -> None:
        """Clear samples for *route_id*, or all routes if *None*."""
        with self._lock:
            if route_id is None:
                self._data.clear()
            else:
                self._data.pop(route_id, None)
            self._save()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> Dict[str, List[float]]:
        if not self._path.exists():
            return {}
        try:
            with self._path.open() as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not load history from %s: %s", self._path, exc)
            return {}

    def _save(self) -> None:
        try:
            with self._path.open("w") as fh:
                json.dump(self._data, fh)
        except OSError as exc:
            logger.error("Could not persist history to %s: %s", self._path, exc)
