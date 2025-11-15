"""Logging configuration for the backend application."""

import logging
from logging.config import dictConfig

from .settings import get_settings


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["console"],
    },
}


def configure_logging() -> None:
    """Configure logging based on settings."""

    settings = get_settings()
    dictConfig(LOGGING_CONFIG)
    logging.getLogger(__name__).info(
        "Logging configured for %s in %s mode",
        settings.app_name,
        settings.environment,
    )
