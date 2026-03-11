"""
Structured logging: console + file, subprocess-friendly.
Creates logs directory automatically.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

from config.settings import LOG_LEVEL


def setup_logging(
    name: str = "flashvsr_app",
    log_dir: Optional[Path] = None,
    level: Optional[str] = None,
    log_filename: Optional[str] = None,
) -> logging.Logger:
    """
    Configure root logger and return a named logger.
    Logs to both console and file (if log_dir is set).
    """
    level = level or LOG_LEVEL
    numeric = getattr(logging, level.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(numeric)

    # Avoid duplicate handlers when called multiple times
    if root.handlers:
        return logging.getLogger(name)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(numeric)
    console.setFormatter(fmt)
    root.addHandler(console)

    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        fname = log_filename or "flashvsr_app.log"
        file_handler = logging.FileHandler(log_dir / fname, encoding="utf-8")
        file_handler.setLevel(numeric)
        file_handler.setFormatter(fmt)
        root.addHandler(file_handler)

    return logging.getLogger(name)


def get_logger(name: str = "flashvsr_app") -> logging.Logger:
    """Return the application logger (call setup_logging first if you need file logging)."""
    return logging.getLogger(name)
