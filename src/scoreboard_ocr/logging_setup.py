"""
Logging setup for Scoreboard OCR Tracker v2.
Configures file (with rotation) and console handlers.
"""

import logging
import logging.handlers
import sys
from pathlib import Path

from .platform_utils import get_log_dir


def setup_logging(
    *,
    level: int = logging.DEBUG,
    console_level: int = logging.INFO,
    max_bytes: int = 5 * 1024 * 1024,  # 5 MB
    backup_count: int = 3,
) -> None:
    """
    Configure root logger with:
    - File handler (rotating) in platform log directory
    - Console handler for stderr

    Call once at application startup.
    """
    log_dir = get_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(level)

    # Clear any existing handlers to avoid duplicates
    root.handlers.clear()

    # Formatter
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler with rotation
    log_file = log_dir / "scoreboard_ocr.log"
    try:
        fh = logging.handlers.RotatingFileHandler(
            str(log_file),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        fh.setLevel(level)
        fh.setFormatter(fmt)
        root.addHandler(fh)
    except OSError as e:
        print(f"WARNING: Cannot create log file at {log_file}: {e}", file=sys.stderr)

    # Console handler
    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(console_level)
    ch.setFormatter(fmt)
    root.addHandler(ch)

    logger = logging.getLogger(__name__)
    logger.info("Logging initialized (dir=%s)", log_dir)
    logger.info("Platform: %s", sys.platform)
    logger.info("Python: %s", sys.version)
