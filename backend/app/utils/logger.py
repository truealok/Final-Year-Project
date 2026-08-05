"""Application-wide logging configuration."""

import logging
import logging.config
import sys

from app.core.config import settings

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def configure_logging() -> None:
    """Configure root logging with a console handler."""
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {"format": LOG_FORMAT},
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "stream": sys.stdout,
                },
            },
            "root": {
                "level": settings.LOG_LEVEL.upper(),
                "handlers": ["console"],
            },
            "loggers": {
                "uvicorn.access": {"level": "WARNING"},
                "sqlalchemy.engine": {"level": "WARNING"},
            },
        }
    )


def get_logger(name: str) -> logging.Logger:
    """Return a named logger."""
    return logging.getLogger(name)
