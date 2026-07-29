"""
OCRWorker — QThread bridge between the main window and the recognition backend.

Runs in a background thread. Receives crop tasks from the main window,
processes them through the configured Recognizer, and emits results back
via pyqtSignal.
"""

import logging
import time
import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

from .base import Recognizer, RecognitionResult
from .template_backend import TemplateSegmentRecognizer

logger = logging.getLogger(__name__)


class OCRWorker(QThread):
    """
    Background thread for OCR processing.

    Usage:
        worker = OCRWorker(recognizer=TemplateSegmentRecognizer())
        worker.result_signal.connect(main_window.on_ocr_result)
        worker.start()
        ...
        worker.process_crops(crops_list)
    """

    result_signal = pyqtSignal(dict, dict)  # (results_dict, debug_images_dict)

    def __init__(
        self,
        recognizer: Recognizer | None = None,
        parent=None,
    ):
        """
        Args:
            recognizer: Recognizer backend. Defaults to TemplateSegmentRecognizer.
            parent: Parent QObject.
        """
        super().__init__(parent)
        self._recognizer = recognizer or TemplateSegmentRecognizer()
        self._tasks: list[tuple] = []
        self._running = True
        self._task_count = 0

    @property
    def recognizer(self) -> Recognizer:
        return self._recognizer

    @recognizer.setter
    def recognizer(self, value: Recognizer) -> None:
        self._recognizer = value

    def load_templates(self) -> None:
        """Reload digit templates (delegates to TemplateSegmentRecognizer if active)."""
        if isinstance(self._recognizer, TemplateSegmentRecognizer):
            self._recognizer.load_templates()

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
                        result = self._recognizer.recognize(img, mode, params)
                        results[z_id] = {"text": result.text, "name": name}
                        debug_imgs[z_id] = result.debug_image
                    except Exception as e:
                        logger.exception(
                            "OCR failed for zone %s (name=%s, mode=%s): %s",
                            z_id, name, mode, e,
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
