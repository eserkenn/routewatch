"""HTTP endpoint for managing route annotations."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from typing import Optional

from routewatch.route_annotations import RouteAnnotations


class _AnnotationHandler(BaseHTTPRequestHandler):
    annotations: RouteAnnotations

    def do_GET(self) -> None:
        url = self._query_param("route_url")
        if url:
            data = [a.to_dict() for a in self.annotations.get(url)]
        else:
            data = {k: [a.to_dict() for a in v] for k, v in self.annotations.all().items()}
        self._respond(200, data)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        route_url = body.get("route_url", "").strip()
        note = body.get("note", "").strip()
        author = body.get("author", "anonymous").strip()
        if not route_url or not note:
            self._respond(400, {"error": "route_url and note are required"})
            return
        annotation = self.annotations.add(route_url, note, author)
        self._respond(201, annotation.to_dict())

    def do_DELETE(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        route_url = body.get("route_url", "").strip()
        index = body.get("index")
        if not route_url or index is None:
            self._respond(400, {"error": "route_url and index are required"})
            return
        removed = self.annotations.delete(route_url, int(index))
        self._respond(200 if removed else 404, {"removed": removed})

    def _query_param(self, key: str) -> Optional[str]:
        if "?" in self.path:
            qs = self.path.split("?", 1)[1]
            for part in qs.split("&"):
                if "=" in part:
                    k, v = part.split("=", 1)
                    if k == key:
                        return v
        return None

    def _respond(self, code: int, payload: object) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:  # silence default logging
        pass


class AnnotationEndpoint:
    def __init__(self, annotations: RouteAnnotations, host: str = "127.0.0.1", port: int = 9105) -> None:
        handler = type("Handler", (_AnnotationHandler,), {"annotations": annotations})
        self._server = HTTPServer((host, port), handler)
        self._thread: Optional[Thread] = None

    def start(self) -> None:
        self._thread = Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._server.shutdown()
        if self._thread:
            self._thread.join(timeout=5)
