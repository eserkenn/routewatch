"""Entry point: load config and run the scheduler."""

import asyncio
import logging
import signal
import sys
from pathlib import Path

from routewatch.config import AppConfig
from routewatch.scheduler import RouteScheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("routewatch")


def _load_config(path: str) -> AppConfig:
    config_path = Path(path)
    if not config_path.exists():
        logger.error("Config file not found: %s", path)
        sys.exit(1)
    return AppConfig.from_file(config_path)


async def _main(config_path: str) -> None:
    config = _load_config(config_path)
    scheduler = RouteScheduler(config)

    loop = asyncio.get_running_loop()

    def _handle_signal():
        logger.info("Shutdown signal received.")
        scheduler.stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _handle_signal)

    await scheduler.run()


def main() -> None:
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.json"
    asyncio.run(_main(config_path))


if __name__ == "__main__":
    main()
