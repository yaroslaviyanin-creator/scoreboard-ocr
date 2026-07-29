"""
OCRWorker — QThread bridge between the main window and the recognition backend.

Runs in a background thread. Receives crop tasks from the main window,
processes them through the configured Recognizer, and emits results back
via pyqtSignal.

Supports per-zone engine switching:
  - Name mode → always Tesseract rus+eng
  - Standard/Time with engine="light" → TrOCR
  - Standard/Time with engine="heavy" → PaddleOCR
"""

import logging
import time
import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

from .base import Recognizer, RecognitionResult

logger = logging.getLogger(__name__)

# Lazy-init backends — created once per process
_trocr = None
_paddleocr = None


def _get_trocr():
    global _trocr
    if _trocr is None:
        from .trocr_backend import TrOCRRecognizer
        _trocr = TrOCRRecognizer()
    return _trocr


def _get_paddleocr():
    global _paddleocr
    if _paddleocr is None:
        from .paddleocr_backend import PaddleOCRRecognizer
        _paddleocr = PaddleOCRRecognizer()
    return _paddleocr


def _get_recognizer_for(mode: str, params: dict) -> Recognizer:
    """Return the right recognizer for this zone based on mode and engine param."""
    if mode == "Name":
        # Name → Tesseract rus+eng (built into TrOCRRecognizer.recognize)
        return _get_trocr()

    engine = params.get("engine", "light")
    if engine == "heavy":
        return _get_paddleocr()
    else:
        return _get_trocr()


class OCRWorker(QThread):
    """
    Background thread for OCR processing.

    Usage:
        worker = OCRWorker()
        worker.result_signal.connect(main_window.on_ocr_result)
        worker.start()
        ...
        worker.process_crops(crops_list)
    """

    result_signal = pyqtSignal(dict, dict)  # (results_dict, debug_images_dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tasks: list[tuple] = []
        self._running = True
        self._task_count = 0

    def process_crops(self, crops: list) -> None:
        """
        Submit a batch of crops for recognition.

        Args:
            crops: List of (zone_id, name, mode, params, bgr_image) tuples.
        """
        self._tasks = crops
        self._task_count += 1

    def run(self) -> None:
        """Main loop: wait for tasks, process, emit results."""
        while self._running:
            if self._tasks:
                tasks = self._tasks.copy()
                self._tasks.clear()

                results: dict = {}
                debug_imgs: dict = {}

                for z_id, name, mode, params, img in tasks:
                    try:
                        recognizer = _get_recognizer_for(mode, params)
                        result = recognizer.recognize(img, mode, params)
                        results[z_id] = {"text": result.text, "name": name}
                        debug_imgs[z_id] = result.debug_image
                    except Exception as e:
                        logger.exception(
                            "OCR failed for zone %s (name=%s, mode=%s, engine=%s): %s",
                            z_id, name, mode, params.get("engine", "light"), e,
                        )
                        # Emit empty result so the UI knows something happened
                        results[z_id] = {"text": "", "name": name}
                        debug_imgs[z_id] = np.zeros((1, 1, 3), dtype=np.uint8)

                try:
                    self.result_signal.emit(results, debug_imgs)
                except Exception as e:
                    logger.exception("Failed to emit OCR results: %s", e)

            self.msleep(150)

    def stop(self) -> None:
        """Gracefully stop the worker thread."""
        self._running = False
        self.wait()
        logger.info("OCRWorker stopped (processed %d batches)", self._task_count)
