"""Centralised logging configuration for routewatch."""

import logging
import logging.config
from typing import Optional

LEVELS = {"debug", "info", "warning", "error", "critical"}

DEFAULT_FORMAT = "%(asctime)s %(levelname)-8s %(name)s %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


def configure_logging(
    level: str = "info",
    fmt: Optional[str] = None,
    datefmt: Optional[str] = None,
) -> None:
    """Apply logging configuration for the whole application.

    Args:
        level: One of debug/info/warning/error/critical (case-insensitive).
        fmt: Optional custom log format string.
        datefmt: Optional custom date format string.

    Raises:
        ValueError: If an unrecognised log level is supplied.
    """
    level_lower = level.lower()
    if level_lower not in LEVELS:
        raise ValueError(
            f"Invalid log level {level!r}. Choose from: {sorted(LEVELS)}"
        )

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": fmt or DEFAULT_FORMAT,
                    "datefmt": datefmt or DEFAULT_DATE_FORMAT,
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "stream": "ext://sys.stdout",
                }
            },
            "root": {
                "handlers": ["console"],
                "level": level_lower.upper(),
            },
        }
    )


def get_logger(name: str) -> logging.Logger:
    """Convenience wrapper around logging.getLogger."""
    return logging.getLogger(name)
