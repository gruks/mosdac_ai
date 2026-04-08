"""Structured logging configuration using structlog."""

import logging
import sys
from typing import Optional

import structlog

from src.gateway.config import settings


def setup_logging(level: Optional[str] = None) -> None:
    """Configure structured logging with JSON output.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               Defaults to settings.log_level.
    """
    log_level = level or settings.log_level or "INFO"

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            # JSON output - handles both console and file output
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard logging to work with structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a logger instance with the given name.

    Args:
        name: The name for the logger (typically __name__).

    Returns:
        A configured structlog logger.
    """
    return structlog.get_logger(name)


# Initialize logging on module import
setup_logging()
