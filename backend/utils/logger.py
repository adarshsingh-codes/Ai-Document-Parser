"""
Centralized logging setup for the whole backend.
Import get_logger(__name__) anywhere you need to log instead of using print().
"""
import logging
import sys

_CONFIGURED = False


def _configure_root_logger() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Get a module-scoped logger with consistent formatting.

    Usage:
        from backend.utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Parsed %s pages", page_count)
    """
    _configure_root_logger()
    return logging.getLogger(name)
