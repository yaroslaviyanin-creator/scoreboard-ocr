"""
Scoreboard OCR Tracker v2 — platform utilities.
Single source of truth for OS detection, resource paths, and capture backends.
"""

import sys
import os
from pathlib import Path


def is_windows() -> bool:
    """Return True if running on Windows."""
    return sys.platform == "win32"


def is_macos() -> bool:
    """Return True if running on macOS."""
    return sys.platform == "darwin"


def is_frozen() -> bool:
    """Return True if running from a PyInstaller bundle."""
    return getattr(sys, "frozen", False)


def resource_path(relative_path: str) -> str:
    """
    Resolve a resource path, supporting both source and PyInstaller bundles.
    """
    if is_frozen():
        base = sys._MEIPASS  # type: ignore[attr-defined]
    else:
        base = os.path.abspath(".")
    return os.path.join(base, relative_path)


def capture_backend() -> int:
    """
    Return the OpenCV backend constant for the current platform.
    Never returns cv2.CAP_ANY.
    """
    import cv2
    if is_windows():
        # Prefer MSMF (Media Foundation) on Windows 10+; DSHOW as fallback
        try:
            return cv2.CAP_MSMF
        except AttributeError:
            return cv2.CAP_DSHOW
    elif is_macos():
        return cv2.CAP_AVFOUNDATION
    else:
        return cv2.CAP_ANY


def get_log_dir() -> Path:
    """
    Platform-appropriate log directory.
    macOS: ~/Library/Logs/ScoreboardOCR/
    Windows: %APPDATA%/ScoreboardOCR/logs/
    Other: ~/.scoreboard_ocr/logs/
    """
    if is_macos():
        return Path.home() / "Library" / "Logs" / "ScoreboardOCR"
    elif is_windows():
        try:
            from platformdirs import user_log_dir
            return Path(user_log_dir("ScoreboardOCR", ensure_exists=True))
        except ImportError:
            return Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "ScoreboardOCR" / "logs"
    else:
        return Path.home() / ".scoreboard_ocr" / "logs"


def get_config_dir() -> Path:
    """
    Platform-appropriate config directory.
    """
    if is_macos():
        return Path.home() / "Library" / "Application Support" / "ScoreboardOCR"
    elif is_windows():
        try:
            from platformdirs import user_config_dir
            return Path(user_config_dir("ScoreboardOCR", ensure_exists=True))
        except ImportError:
            return Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "ScoreboardOCR"
    else:
        return Path.home() / ".config" / "scoreboard_ocr"


def find_tesseract() -> str | None:
    """
    Locate the Tesseract binary. Logs which path is chosen and why.

    Windows: check bundled Tesseract-OCR/tesseract.exe, then PATH.
    macOS: check PATH only (assumes brew install tesseract).
    Returns the path as a string, or None if not found.
    """
    import shutil
    import logging
    logger = logging.getLogger(__name__)

    if is_frozen():
        base = sys._MEIPASS  # type: ignore[attr-defined]
        bundled_paths = [
            os.path.join(base, "_internal", "Tesseract-OCR", "tesseract.exe"),
            os.path.join(base, "Tesseract-OCR", "tesseract.exe"),
        ]
        for p in bundled_paths:
            if os.path.exists(p):
                logger.info("Using bundled Tesseract: %s", p)
                return p

    # Check PATH
    tesseract_name = "tesseract.exe" if is_windows() else "tesseract"
    found = shutil.which(tesseract_name)
    if found:
        logger.info("Found Tesseract in PATH: %s", found)
        return found

    if is_windows():
        # Check common install location
        common = os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"),
                              "Tesseract-OCR", "tesseract.exe")
        if os.path.exists(common):
            logger.info("Found Tesseract in Program Files: %s", common)
            return common
        common_x86 = os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"),
                                  "Tesseract-OCR", "tesseract.exe")
        if os.path.exists(common_x86):
            logger.info("Found Tesseract in Program Files (x86): %s", common_x86)
            return common_x86

    logger.warning("Tesseract not found on this system.")
    return None
