"""Application entry point — creates QApplication and launches MainWindow."""

import sys
import logging
from PyQt6.QtWidgets import QApplication

from .logging_setup import setup_logging
from .ui.main_window import MainWindow

logger = logging.getLogger(__name__)


def main() -> None:
    """Main entry point for Scoreboard OCR Tracker v2."""
    setup_logging()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("Scoreboard OCR Tracker")
    app.setApplicationVersion("2.0.0")

    logger.info("Starting Scoreboard OCR Tracker v2")
    logger.info("Platform: %s", sys.platform)

    win = MainWindow()
    win.show()

    exit_code = app.exec()
    logger.info("Application exited with code %d", exit_code)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
