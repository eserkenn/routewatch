"""HTTP endpoint that exposes per-route health scores as JSON."""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

from routewatch.logging_config import get_logger
from routewatch.metrics import MetricsCollector
from routewatch.route_scorer import RouteScore, RouteScorer

logger = get_logger(__name__)


class _ScoreHandler(BaseHTTPRequestHandler):
    collector: MetricsCollector
    scorer: RouteScorer

    def do_GET(self) -> None:
        if self.path not in ("/scores", "/scores/"):
            self._respond(404, {"error": "not found"})
            return

        scores: list[RouteScore] = []
        for url, metrics in self.collector.all().items():
            scores.append(self.scorer.score_route(url, metrics))

        scores.sort(key=lambda s: s.score)
        payload = [
            {
                "url": s.url,
                "score": s.score,
                "grade": s.grade,
                "reason": s.reason,
            }
            for s in scores
        ]
        self._respond(200, payload)

    def _respond(self, status: int, body) -> None:
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args) -> None:  # silence default stderr logging
        logger.debug(fmt, *args)


class ScoreEndpoint:
    def __init__(self, collector: MetricsCollector, host: str = "127.0.0.1", port: int = 9105) -> None:
        self._collector = collector
        self._scorer = RouteScorer()
        self._host = host
        self._port = port
        self._server: HTTPServer | None = None
        self._thread: Thread | None = None

    def start(self) -> None:
        scorer = self._scorer
        collector = self._collector

        class _Handler(_ScoreHandler):
            pass

        _Handler.collector = collector  # type: ignore[attr-defined]
        _Handler.scorer = scorer        # type: ignore[attr-defined]

        self._server = HTTPServer((self._host, self._port), _Handler)
        self._thread = Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        logger.info("ScoreEndpoint listening on %s:%s", self._host, self._port)

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            logger.info("ScoreEndpoint stopped")
