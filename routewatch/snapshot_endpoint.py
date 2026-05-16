"""HTTP endpoint that exposes the latest route snapshots as JSON."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional

from routewatch.metrics import MetricsCollector
from routewatch.history import LatencyHistory
from routewatch.route_snapshot import take_all_snapshots
from routewatch.logging_config import get_logger

logger = get_logger(__name__)


class _SnapshotHandler(BaseHTTPRequestHandler):
    collector: MetricsCollector
    history: LatencyHistory

    def do_GET(self) -> None:
        if self.path != "/snapshots":
            self._respond(404, {"error": "not found"})
            return
        snaps = take_all_snapshots(self.collector, self.history)
        payload = [
            {
                "url": s.url,
                "timestamp": s.timestamp,
                "success_rate": s.success_rate,
                "failure_rate": s.failure_rate,
                "total_checks": s.total_checks,
                "avg_latency_ms": s.avg_latency_ms,
                "consecutive_failures": s.consecutive_failures,
            }
            for s in snaps.values()
        ]
        self._respond(200, payload)

    def _respond(self, code: int, body: object) -> None:
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args: object) -> None:  # silence default stderr logs
        pass


class SnapshotEndpoint:
    """Thin wrapper that runs _SnapshotHandler in a daemon thread."""

    def __init__(
        self,
        collector: MetricsCollector,
        history: LatencyHistory,
        host: str = "127.0.0.1",
        port: int = 9102,
    ) -> None:
        handler = type(
            "_BoundHandler",
            (_SnapshotHandler,),
            {"collector": collector, "history": history},
        )
        self._server = HTTPServer((host, port), handler)
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._server.serve_forever, daemon=True, name="snapshot-endpoint"
        )
        self._thread.start()
        logger.info("SnapshotEndpoint listening on %s:%d", *self._server.server_address)

    def stop(self) -> None:
        self._server.shutdown()
        if self._thread:
            self._thread.join(timeout=5.0)
        logger.info("SnapshotEndpoint stopped")
