"""Atomic text file writer — safe for external programs (vMix) that read the file live."""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def write_value_atomic(
    folder: str | Path,
    name: str,
    value: str,
    encoding: str = "utf-8",
) -> bool:
    """
    Atomically write a value to {folder}/{name}.txt.

    Writes to a temp file first, then replaces the target with os.replace().
    os.replace() is atomic on both Windows and macOS — external readers
    will never see a half-written file.

    Args:
        folder: Output directory path.
        name: Base name (without .txt extension).
        value: Text value to write (pure content, no extra newlines).
        encoding: File encoding (default UTF-8).

    Returns:
        True on success, False on failure.
    """
    folder = Path(folder)
    target = folder / f"{name}.txt"

    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error("Cannot create output folder %s: %s", folder, e)
        return False

    tmp = folder / f".{name}.txt.tmp"

    try:
        with open(tmp, "w", encoding=encoding) as f:
            f.write(str(value))
    except OSError as e:
        logger.exception("Failed to write temp file %s: %s", tmp, e)
        return False

    try:
        os.replace(tmp, target)
    except OSError as e:
        logger.exception("Failed atomic replace %s → %s: %s", tmp, target, e)
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        return False

    return True
