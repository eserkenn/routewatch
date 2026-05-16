"""HTTP endpoint that exposes label index queries over a simple JSON API.

GET /labels              -> {"keys": [...]}
GET /labels/{key}        -> {"key": "...", "values": [...]}
GET /labels/{key}/{value}-> {"key": "...", "value": "...", "urls": [...]}
"""
from __future__ import annotations

import json
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from typing import Optional

from routewatch.route_labels import RouteLabelIndex

_RE_KEY = re.compile(r"^/labels/([^/]+)$")
_RE_KEY_VALUE = re.compile(r"^/labels/([^/]+)/([^/]+)$")


class _LabelHandler(BaseHTTPRequestHandler):
    index: RouteLabelIndex  # injected by LabelEndpoint

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.rstrip("/")
        if path == "/labels":
            keys = list(self.index._index.keys())
            self._respond(200, {"keys": keys})
            return
        m = _RE_KEY_VALUE.match(path)
        if m:
            key, value = m.group(1), m.group(2)
            urls = self.index.lookup(key, value)
            self._respond(200, {"key": key, "value": value, "urls": urls})
            return
        m = _RE_KEY.match(path)
        if m:
            key = m.group(1)
            values = self.index.all_values(key)
            self._respond(200, {"key": key, "values": values})
            return
        self._respond(404, {"error": "not found"})

    def _respond(self, code: int, body: object) -> None:
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *_args: object) -> None:  # silence access logs
        pass


class LabelEndpoint:
    """Thin wrapper that owns the HTTPServer thread."""

    def __init__(self, index: RouteLabelIndex, host: str = "127.0.0.1", port: int = 9105) -> None:
        self._index = index

        def factory(*args, **kwargs):  # type: ignore[no-untyped-def]
            handler = _LabelHandler(*args, **kwargs)
            handler.index = index
            return handler

        self._server = HTTPServer((host, port), factory)
        self._thread: Optional[Thread] = None

    def start(self) -> None:
        self._thread = Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._server.shutdown()
        if self._thread:
            self._thread.join(timeout=5)
