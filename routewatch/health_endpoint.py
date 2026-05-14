"""Simple HTTP health endpoint exposing current route status."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional

from routewatch.logging_config import get_logger
from routewatch.status import StatusReport, build_status_report
from routewatch.metrics import MetricsCollector
from routewatch.history import LatencyHistory

logger = get_logger(__name__)


class _HealthHandler(BaseHTTPRequestHandler):
    collector: MetricsCollector
    history: LatencyHistory

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            report: StatusReport = build_status_report(self.collector, self.history)
            body = json.dumps({
                "healthy": report.all_healthy,
                "total_routes": report.total_routes,
                "healthy_routes": report.healthy_routes,
                "unhealthy_routes": report.unhealthy_routes,
                "routes": [
                    {
                        "route": s.route,
                        "healthy": s.healthy,
                        "success_rate": round(s.success_rate, 4),
                        "avg_latency_ms": round(s.avg_latency_ms, 2),
                        "consecutive_failures": s.consecutive_failures,
                    }
                    for s in report.summaries
                ],
            }).encode()
            self._respond(200, body)
        else:
            self._respond(404, b"{\"error\": \"not found\"}")

    def _respond(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:  # noqa: D401
        logger.debug("health endpoint: " + fmt, *args)


class HealthEndpoint:
    """Runs a lightweight HTTP server exposing /health in a background thread."""

    def __init__(
        self,
        collector: MetricsCollector,
        history: LatencyHistory,
        host: str = "127.0.0.1",
        port: int = 9090,
    ) -> None:
        self._collector = collector
        self._history = history
        self._host = host
        self._port = port
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        handler = _HealthHandler
        handler.collector = self._collector  # type: ignore[attr-defined]
        handler.history = self._history  # type: ignore[attr-defined]
        self._server = HTTPServer((self._host, self._port), handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        logger.info("Health endpoint listening on %s:%s", self._host, self._port)

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            logger.info("Health endpoint stopped")
