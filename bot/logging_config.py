"""
Logging configuration for the trading bot.
Sets up structured logging to both file and console.
"""

import logging
import logging.handlers
import os
from datetime import datetime


LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
LOG_FILE = os.path.join(LOG_DIR, "trading_bot.log")


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Configure logging to write to both a rotating file and the console.

    Args:
        log_level: Logging level string (DEBUG, INFO, WARNING, ERROR).

    Returns:
        Configured root logger.
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    logger = logging.getLogger("trading_bot")
    logger.setLevel(logging.DEBUG)  # capture everything; handlers filter

    # ── File handler (rotating, keeps last 5 × 5 MB) ──────────────────────
    file_fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_fmt)

    # ── Console handler ────────────────────────────────────────────────────
    console_fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(console_fmt)

    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the 'trading_bot' namespace."""
    return logging.getLogger(f"trading_bot.{name}")
