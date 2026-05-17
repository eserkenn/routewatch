"""HTTP endpoint for browsing the route changelog."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from typing import Optional
from urllib.parse import parse_qs, urlparse

from routewatch.route_changelog import RouteChangelog


class _ChangelogHandler(BaseHTTPRequestHandler):
    changelog: RouteChangelog

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/changelog":
            self._respond(404, {"error": "not found"})
            return

        params = parse_qs(parsed.query)
        route_url: Optional[str] = params.get("route", [None])[0]  # type: ignore[assignment]

        entries = self.changelog.get(route_url)
        self._respond(200, [e.to_dict() for e in entries])

    def _respond(self, status: int, body: object) -> None:
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *_: object) -> None:  # silence access logs
        pass


class ChangelogEndpoint:
    def __init__(self, changelog: RouteChangelog, host: str = "127.0.0.1", port: int = 9107) -> None:
        self._changelog = changelog
        self._host = host
        self._port = port
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[Thread] = None

    def start(self) -> None:
        handler = _ChangelogHandler
        handler.changelog = self._changelog
        self._server = HTTPServer((self._host, self._port), handler)
        self._thread = Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
