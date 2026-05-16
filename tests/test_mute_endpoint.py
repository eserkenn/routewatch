"""Tests for MuteEndpoint HTTP handler."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from routewatch.mute_endpoint import _MuteHandler
from routewatch.route_muter import RouteMuter

URL = "https://example.com/api"


def _make_handler(method: str, path: str, body: bytes = b"") -> _MuteHandler:
    muter = RouteMuter()
    handler = _MuteHandler.__new__(_MuteHandler)
    handler.muter = muter
    handler.path = path
    handler.command = method
    handler.headers = {"Content-Length": str(len(body))}
    handler.rfile = BytesIO(body)
    responses: list[bytes] = []
    handler.wfile = MagicMock()
    handler.wfile.write = lambda d: responses.append(d)
    handler._responses = responses
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()
    return handler


def test_get_empty_returns_list() -> None:
    h = _make_handler("GET", "/mute")
    h.do_GET()
    h.send_response.assert_called_with(200)


def test_post_mutes_route() -> None:
    body = json.dumps({"route_url": URL, "seconds": 60, "reason": "test"}).encode()
    h = _make_handler("POST", "/mute", body)
    h.do_POST()
    h.send_response.assert_called_with(200)
    assert h.muter.is_muted(URL)


def test_post_missing_route_url_returns_400() -> None:
    body = json.dumps({"seconds": 60}).encode()
    h = _make_handler("POST", "/mute", body)
    h.do_POST()
    h.send_response.assert_called_with(400)


def test_delete_unmutes_route() -> None:
    muter = RouteMuter()
    muter.mute(URL, datetime.now(timezone.utc) + timedelta(seconds=300))
    h = _make_handler("DELETE", f"/mute/{URL}")
    h.muter = muter
    h.do_DELETE()
    h.send_response.assert_called_with(200)
    assert not muter.is_muted(URL)


def test_get_unknown_path_returns_404() -> None:
    h = _make_handler("GET", "/unknown")
    h.do_GET()
    h.send_response.assert_called_with(404)


def test_get_lists_active_mutes() -> None:
    muter = RouteMuter()
    muter.mute(URL, datetime.now(timezone.utc) + timedelta(seconds=300), reason="ci")
    h = _make_handler("GET", "/mute")
    h.muter = muter
    written: list[bytes] = []
    h.wfile.write = lambda d: written.append(d)
    h.do_GET()
    payload = json.loads(b"".join(written))
    assert len(payload) == 1
    assert payload[0]["route_url"] == URL
    assert payload[0]["reason"] == "ci"
