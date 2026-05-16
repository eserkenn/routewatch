"""Periodic reporter that logs annotation counts per route."""
from __future__ import annotations

import threading
from typing import Optional

from routewatch.logging_config import get_logger
from routewatch.route_annotations import RouteAnnotations

logger = get_logger(__name__)


class AnnotationReporter:
    """Logs a summary of route annotations at a fixed interval."""

    def __init__(self, annotations: RouteAnnotations, interval: float = 300.0) -> None:
        self._annotations = annotations
        self._interval = interval
        self._timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()
        self._running = False

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
        self._schedule()

    def stop(self) -> None:
        with self._lock:
            self._running = False
            if self._timer:
                self._timer.cancel()
                self._timer = None

    def _schedule(self) -> None:
        with self._lock:
            if not self._running:
                return
            self._timer = threading.Timer(self._interval, self._run)
            self._timer.daemon = True
            self._timer.start()

    def _run(self) -> None:
        try:
            all_annotations = self._annotations.all()
            if not all_annotations:
                logger.info("annotation_reporter: no annotations recorded")
            else:
                for route_url, entries in all_annotations.items():
                    logger.info(
                        "annotation_reporter: route=%s annotations=%d",
                        route_url,
                        len(entries),
                    )
        finally:
            self._schedule()
