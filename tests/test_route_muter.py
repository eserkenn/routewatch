"""Tests for RouteMuter."""
from datetime import datetime, timedelta, timezone

import pytest

from routewatch.route_muter import MuteEntry, RouteMuter


URL = "https://example.com/api/health"


@pytest.fixture
def muter() -> RouteMuter:
    return RouteMuter()


def _future(seconds: int = 300) -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=seconds)


def _past(seconds: int = 300) -> datetime:
    return datetime.now(timezone.utc) - timedelta(seconds=seconds)


def test_new_muter_has_no_active_mutes(muter: RouteMuter) -> None:
    assert muter.active_mutes() == []


def test_mute_makes_route_muted(muter: RouteMuter) -> None:
    muter.mute(URL, _future())
    assert muter.is_muted(URL)


def test_expired_mute_is_not_active(muter: RouteMuter) -> None:
    muter.mute(URL, _past())
    assert not muter.is_muted(URL)


def test_unknown_route_is_not_muted(muter: RouteMuter) -> None:
    assert not muter.is_muted("https://other.example.com/")


def test_unmute_removes_entry(muter: RouteMuter) -> None:
    muter.mute(URL, _future())
    removed = muter.unmute(URL)
    assert removed is True
    assert not muter.is_muted(URL)


def test_unmute_nonexistent_returns_false(muter: RouteMuter) -> None:
    assert muter.unmute(URL) is False


def test_active_mutes_filters_expired(muter: RouteMuter) -> None:
    muter.mute(URL, _future(), reason="deploy")
    muter.mute("https://other.example.com/", _past())
    active = muter.active_mutes()
    assert len(active) == 1
    assert active[0].route_url == URL


def test_purge_expired_removes_old_entries(muter: RouteMuter) -> None:
    muter.mute(URL, _past())
    muter.mute("https://keep.example.com/", _future())
    count = muter.purge_expired()
    assert count == 1
    assert not muter.is_muted(URL)
    assert muter.is_muted("https://keep.example.com/")


def test_mute_entry_is_active_with_future_time() -> None:
    entry = MuteEntry(route_url=URL, muted_until=_future())
    assert entry.is_active()


def test_mute_entry_not_active_with_past_time() -> None:
    entry = MuteEntry(route_url=URL, muted_until=_past())
    assert not entry.is_active()


def test_overwrite_mute_updates_deadline(muter: RouteMuter) -> None:
    muter.mute(URL, _past())
    assert not muter.is_muted(URL)
    muter.mute(URL, _future())
    assert muter.is_muted(URL)
