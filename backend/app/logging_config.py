"""Centralized logging configuration for Pacioli."""

import logging
import os
from pathlib import Path


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure application logging.

    Logs go to ``<XDG data dir>/pacioli/logs/pacioli.log`` plus the
    console (WARNING and above only).

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).

    Returns:
        The configured logger.
    """
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    log_dir = Path(base) / "pacioli" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("pacioli")
    logger.setLevel(getattr(logging, level.upper()))

    # Avoid duplicated handlers on repeated calls
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(log_dir / "pacioli.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


logger = setup_logging()
