"""Tests for RouteChangelog and ChangelogEndpoint."""
from __future__ import annotations

import json
from io import BytesIO
from unittest.mock import MagicMock

import pytest

from routewatch.route_changelog import ChangelogEntry, RouteChangelog
from routewatch.changelog_endpoint import _ChangelogHandler


@pytest.fixture()
def changelog() -> RouteChangelog:
    return RouteChangelog()


def test_initial_changelog_is_empty(changelog: RouteChangelog) -> None:
    assert changelog.get() == []


def test_record_adds_entry(changelog: RouteChangelog) -> None:
    entry = changelog.record("http://example.com", "interval", "30", "60")
    assert isinstance(entry, ChangelogEntry)
    assert len(changelog.get()) == 1


def test_entry_to_dict_has_expected_keys(changelog: RouteChangelog) -> None:
    entry = changelog.record("http://a.com", "timeout", "5", "10")
    d = entry.to_dict()
    assert set(d.keys()) == {"route_url", "field", "old_value", "new_value", "changed_at"}


def test_get_filters_by_route(changelog: RouteChangelog) -> None:
    changelog.record("http://a.com", "interval", "10", "20")
    changelog.record("http://b.com", "timeout", "5", "10")
    assert len(changelog.get("http://a.com")) == 1
    assert changelog.get("http://a.com")[0].route_url == "http://a.com"


def test_clear_all(changelog: RouteChangelog) -> None:
    changelog.record("http://a.com", "interval", "1", "2")
    changelog.clear()
    assert changelog.get() == []


def test_clear_by_route(changelog: RouteChangelog) -> None:
    changelog.record("http://a.com", "interval", "1", "2")
    changelog.record("http://b.com", "timeout", "3", "4")
    changelog.clear("http://a.com")
    assert changelog.get("http://a.com") == []
    assert len(changelog.get("http://b.com")) == 1


def test_max_entries_enforced() -> None:
    cl = RouteChangelog(max_entries=3)
    for i in range(5):
        cl.record("http://x.com", "field", str(i), str(i + 1))
    assert len(cl.get()) == 3


def test_diff_and_record_detects_changes(changelog: RouteChangelog) -> None:
    old = {"interval": "30", "timeout": "5"}
    new = {"interval": "60", "timeout": "5"}
    entries = changelog.diff_and_record("http://a.com", old, new)
    assert len(entries) == 1
    assert entries[0].field == "interval"
    assert entries[0].old_value == "30"
    assert entries[0].new_value == "60"


def test_diff_and_record_no_changes(changelog: RouteChangelog) -> None:
    cfg = {"interval": "30"}
    entries = changelog.diff_and_record("http://a.com", cfg, cfg)
    assert entries == []


def _make_handler(changelog: RouteChangelog, path: str) -> _ChangelogHandler:
    handler = _ChangelogHandler.__new__(_ChangelogHandler)
    handler.changelog = changelog
    handler.path = path
    handler.wfile = BytesIO()
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()
    return handler


def test_endpoint_returns_200(changelog: RouteChangelog) -> None:
    changelog.record("http://a.com", "interval", "10", "20")
    handler = _make_handler(changelog, "/changelog")
    handler.do_GET()
    handler.send_response.assert_called_once_with(200)


def test_endpoint_filters_by_route_param(changelog: RouteChangelog) -> None:
    changelog.record("http://a.com", "interval", "10", "20")
    changelog.record("http://b.com", "timeout", "5", "10")
    handler = _make_handler(changelog, "/changelog?route=http%3A%2F%2Fa.com")
    handler.do_GET()
    handler.wfile.seek(0)
    data = json.loads(handler.wfile.read())
    assert len(data) == 1
    assert data[0]["route_url"] == "http://a.com"


def test_endpoint_unknown_path_returns_404(changelog: RouteChangelog) -> None:
    handler = _make_handler(changelog, "/unknown")
    handler.do_GET()
    handler.send_response.assert_called_once_with(404)
