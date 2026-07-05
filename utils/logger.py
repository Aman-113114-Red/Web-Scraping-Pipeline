"""
Logging Module
==============
Provides a centralized, rotating logger with:
  • Console output (coloured level tags)
  • Rotating file output (10 MB per file, 5 backups)
  • Custom SUCCESS level (25)
  • Timestamp on every entry

Usage
-----
    from utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Starting scraper …")
    logger.success("Scraping complete!")   # custom level
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import List, Optional

from config.settings import Settings

# ---------------------------------------------------------------------------
# Custom SUCCESS level (between INFO=20 and WARNING=30)
# ---------------------------------------------------------------------------
SUCCESS_LEVEL = 25
logging.addLevelName(SUCCESS_LEVEL, "SUCCESS")


def _success(self: logging.Logger, message: str, *args, **kwargs) -> None:  # type: ignore[override]
    """Log a message with severity 'SUCCESS'."""
    if self.isEnabledFor(SUCCESS_LEVEL):
        self._log(SUCCESS_LEVEL, message, args, **kwargs)


logging.Logger.success = _success  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# In-memory log buffer (used by the /api/logs endpoint)
# ---------------------------------------------------------------------------
_log_buffer: List[dict] = []
MAX_BUFFER_SIZE = 500


class BufferHandler(logging.Handler):
    """Stores log records in an in-memory list for the dashboard."""

    def emit(self, record: logging.LogRecord) -> None:
        entry = {
            "timestamp": self.format(record).split(" | ")[0] if " | " in self.format(record) else "",
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
        }
        _log_buffer.append(entry)
        if len(_log_buffer) > MAX_BUFFER_SIZE:
            _log_buffer.pop(0)


def get_log_buffer() -> List[dict]:
    """Return the current in-memory log buffer."""
    return list(_log_buffer)


def clear_log_buffer() -> None:
    """Clear the in-memory log buffer."""
    _log_buffer.clear()


# ---------------------------------------------------------------------------
# Formatter
# ---------------------------------------------------------------------------
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ---------------------------------------------------------------------------
# Logger factory
# ---------------------------------------------------------------------------
_configured_loggers: set = set()


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Create or retrieve a logger with console + file + buffer handlers.

    Parameters
    ----------
    name : str, optional
        Logger name (typically ``__name__``). Defaults to ``"pipeline"``.

    Returns
    -------
    logging.Logger
        Configured logger instance with a custom ``.success()`` method.
    """
    name = name or "pipeline"

    if name in _configured_loggers:
        return logging.getLogger(name)

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, Settings.LOG_LEVEL, logging.INFO))
    logger.propagate = False

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # --- Console handler --------------------------------------------------
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # --- Rotating file handler --------------------------------------------
    log_file = Settings.LOG_FOLDER / "pipeline.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # --- In-memory buffer handler -----------------------------------------
    buffer_handler = BufferHandler()
    buffer_handler.setFormatter(formatter)
    logger.addHandler(buffer_handler)

    _configured_loggers.add(name)
    return logger
