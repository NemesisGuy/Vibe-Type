"""Centralised logging configuration for VibeType."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from core.utils import get_config_path


def configure_logging() -> Path | None:
    """Configure application-wide logging to both console and a rotating file.

    Returns
    -------
    Path | None
        The path to the log file if it could be created, otherwise ``None``.
    """

    config_path = Path(get_config_path())
    logs_dir = config_path.parent / "logs"
    log_file: Path | None = None

    handlers: list[logging.Handler] = [logging.StreamHandler()]

    try:
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_file = logs_dir / "vibetype.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,  # 5 MB per file
            backupCount=3,
            encoding="utf-8",
        )
        handlers.append(file_handler)
    except OSError:
        # Fall back to console-only logging if the file cannot be created.
        log_file = None

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )

    logging.getLogger(__name__).debug("Logging configured. File handler active: %s", bool(log_file))

    return log_file
