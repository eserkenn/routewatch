"""HTTP endpoint that exposes route metrics as JSON or CSV on demand."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional

from routewatch.history import LatencyHistory
from routewatch.logging_config import get_logger
from routewatch.metrics import MetricsCollector
from routewatch.route_exporter import build_export_rows, export_csv, export_json

logger = get_logger(__name__)


class _ExportHandler(BaseHTTPRequestHandler):
    collector: MetricsCollector
    history: LatencyHistory
    failure_threshold: int

    def do_GET(self) -> None:  # noqa: N802
        rows = build_export_rows(
            self.__class__.collector,
            self.__class__.history,
            self.__class__.failure_threshold,
        )
        if self.path == "/export/csv":
            body = export_csv(rows).encode()
            content_type = "text/csv"
        else:
            body = export_json(rows).encode()
            content_type = "application/json"
        self._respond(200, content_type, body)

    def _respond(self, code: int, content_type: str, body: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:  # noqa: D401
        logger.debug("export_endpoint: " + fmt, *args)


class ExportEndpoint:
    def __init__(
        self,
        collector: MetricsCollector,
        history: LatencyHistory,
        port: int = 9091,
        failure_threshold: int = 3,
    ) -> None:
        self._port = port
        _ExportHandler.collector = collector
        _ExportHandler.history = history
        _ExportHandler.failure_threshold = failure_threshold
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._server = HTTPServer(("0.0.0.0", self._port), _ExportHandler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        logger.info("Export endpoint listening on port %d", self._port)

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server = None
        logger.info("Export endpoint stopped")
