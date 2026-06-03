"""Structured logging utilities for ResumeForge AI."""

import logging
import sys
from config.settings import settings


def get_logger(name: str) -> logging.Logger:
    """Create a configured logger with console output."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.setLevel(logging.DEBUG if settings.app_debug else logging.INFO)
    return logger
