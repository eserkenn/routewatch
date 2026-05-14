"""Tests for the __main__ entry point."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def test_main_exits_if_config_missing(tmp_path, capsys):
    missing = str(tmp_path / "nonexistent.json")
    with patch("sys.argv", ["routewatch", missing]):
        with pytest.raises(SystemExit) as exc_info:
            from routewatch.__main__ import main
            main()
    assert exc_info.value.code == 1


def test_main_uses_default_config_name(tmp_path):
    """When no argument given, defaults to config.json."""
    import routewatch.__main__ as m

    captured_path = {}

    def fake_load(path):
        captured_path["path"] = path
        raise SystemExit(0)  # abort early

    with patch.object(m, "_load_config", side_effect=fake_load), \
         patch("sys.argv", ["routewatch"]):
        with pytest.raises(SystemExit):
            m.main()

    assert captured_path["path"] == "config.json"


def test_main_uses_provided_config_path(tmp_path):
    import routewatch.__main__ as m

    captured_path = {}

    def fake_load(path):
        captured_path["path"] = path
        raise SystemExit(0)

    with patch.object(m, "_load_config", side_effect=fake_load), \
         patch("sys.argv", ["routewatch", "/etc/rw/config.json"]):
        with pytest.raises(SystemExit):
            m.main()

    assert captured_path["path"] == "/etc/rw/config.json"


@pytest.mark.asyncio
async def test_async_main_runs_scheduler(tmp_path):
    import routewatch.__main__ as m

    fake_config = MagicMock()
    fake_scheduler = MagicMock()
    fake_scheduler.run = AsyncMock()
    fake_scheduler.stop = MagicMock()

    with patch.object(m, "_load_config", return_value=fake_config), \
         patch("routewatch.scheduler.RouteScheduler", return_value=fake_scheduler):
        await m._main("config.json")

    fake_scheduler.run.assert_awaited_once()
