"""Tests for AnnotationEndpoint HTTP handler."""
from __future__ import annotations

import json
from io import BytesIO
from unittest.mock import MagicMock

import pytest

from routewatch.annotation_endpoint import _AnnotationHandler
from routewatch.route_annotations import RouteAnnotations


def _make_handler(method: str, path: str, body: bytes = b"") -> _AnnotationHandler:
    annotations = RouteAnnotations()
    handler = _AnnotationHandler.__new__(_AnnotationHandler)
    handler.annotations = annotations
    handler.path = path
    handler.command = method
    handler.headers = {"Content-Length": str(len(body))}
    handler.rfile = BytesIO(body)
    handler.wfile = BytesIO()
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()
    return handler


def _read_response(handler: _AnnotationHandler) -> object:
    handler.wfile.seek(0)
    return json.loads(handler.wfile.read())


def test_get_all_empty_returns_dict() -> None:
    h = _make_handler("GET", "/annotations")
    h.do_GET()
    data = _read_response(h)
    assert data == {}


def test_post_creates_annotation() -> None:
    body = json.dumps({"route_url": "http://api.test", "note": "slow", "author": "alice"}).encode()
    h = _make_handler("POST", "/annotations", body)
    h.do_POST()
    h.send_response.assert_called_once_with(201)
    data = _read_response(h)
    assert data["note"] == "slow"
    assert data["author"] == "alice"


def test_post_missing_note_returns_400() -> None:
    body = json.dumps({"route_url": "http://api.test"}).encode()
    h = _make_handler("POST", "/annotations", body)
    h.do_POST()
    h.send_response.assert_called_once_with(400)


def test_post_missing_route_url_returns_400() -> None:
    body = json.dumps({"note": "something"}).encode()
    h = _make_handler("POST", "/annotations", body)
    h.do_POST()
    h.send_response.assert_called_once_with(400)


def test_get_with_route_url_filter() -> None:
    h = _make_handler("GET", "/annotations?route_url=http://api.test")
    h.annotations.add("http://api.test", "note", "alice")
    h.do_GET()
    data = _read_response(h)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["note"] == "note"


def test_delete_removes_annotation() -> None:
    h = _make_handler("DELETE", "/annotations",
                      json.dumps({"route_url": "http://api.test", "index": 0}).encode())
    h.annotations.add("http://api.test", "to delete", "bob")
    h.do_DELETE()
    h.send_response.assert_called_once_with(200)
    assert h.annotations.get("http://api.test") == []


def test_delete_invalid_index_returns_404() -> None:
    h = _make_handler("DELETE", "/annotations",
                      json.dumps({"route_url": "http://api.test", "index": 5}).encode())
    h.do_DELETE()
    h.send_response.assert_called_once_with(404)
