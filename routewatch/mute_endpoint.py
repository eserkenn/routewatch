"""HTTP endpoint for managing route mutes (/mute)."""
from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional

from routewatch.logging_config import get_logger
from routewatch.route_muter import RouteMuter

_log = get_logger(__name__)


class _MuteHandler(BaseHTTPRequestHandler):
    muter: RouteMuter  # injected by MuteEndpoint

    def do_GET(self) -> None:  # list active mutes
        if self.path != "/mute":
            self._respond(404, {"error": "not found"})
            return
        payload = [
            {
                "route_url": e.route_url,
                "muted_until": e.muted_until.isoformat(),
                "reason": e.reason,
            }
            for e in self.muter.active_mutes()
        ]
        self._respond(200, payload)

    def do_POST(self) -> None:  # add a mute
        if self.path != "/mute":
            self._respond(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length))
            url: str = body["route_url"]
            seconds: int = int(body.get("seconds", 300))
            reason: str = body.get("reason", "")
        except Exception as exc:
            self._respond(400, {"error": str(exc)})
            return
        until = datetime.now(timezone.utc) + timedelta(seconds=seconds)
        self.muter.mute(url, until, reason)
        self._respond(200, {"muted_until": until.isoformat()})

    def do_DELETE(self) -> None:  # remove a mute
        if not self.path.startswith("/mute/"):
            self._respond(404, {"error": "not found"})
            return
        url = self.path[len("/mute/"):]
        removed = self.muter.unmute(url)
        self._respond(200, {"removed": removed})

    def _respond(self, status: int, body: object) -> None:
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args: object) -> None:  # silence default stderr
        _log.debug(fmt, *args)


class MuteEndpoint:
    def __init__(self, muter: RouteMuter, host: str = "127.0.0.1", port: int = 9102) -> None:
        _MuteHandler.muter = muter
        self._server = HTTPServer((host, port), _MuteHandler)
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        _log.info("MuteEndpoint listening on %s:%s", *self._server.server_address)

    def stop(self) -> None:
        self._server.shutdown()
        if self._thread:
            self._thread.join(timeout=5)
