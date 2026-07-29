"""Video capture thread — reads frames from a camera using OpenCV."""

import logging
import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

from ..platform_utils import capture_backend

logger = logging.getLogger(__name__)


class VideoThread(QThread):
    """
    Background thread that continuously reads frames from the selected camera.

    Emits change_pixmap_signal with each new frame as a numpy BGR array.
    """

    change_pixmap_signal = pyqtSignal(np.ndarray)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._run_flag = False
        self._camera_index = 0
        self._cap: cv2.VideoCapture | None = None

    @property
    def camera_index(self) -> int:
        return self._camera_index

    @camera_index.setter
    def camera_index(self, value: int) -> None:
        self._camera_index = value

    def run(self) -> None:
        self._run_flag = True
        backend = capture_backend()

        logger.info(
            "Opening camera index=%d with backend=%s",
            self._camera_index, backend,
        )

        self._cap = cv2.VideoCapture(self._camera_index, backend)

        if not self._cap.isOpened():
            logger.error(
                "Failed to open camera index=%d (backend=%s)",
                self._camera_index, backend,
            )
            self._run_flag = False
            return

        logger.info("Camera opened successfully: index=%d", self._camera_index)

        while self._run_flag:
            ret, cv_img = self._cap.read()
            if ret:
                self.change_pixmap_signal.emit(cv_img)
            else:
                logger.debug("Camera read returned False, sleeping 10ms")
                self.msleep(10)

    def stop(self) -> None:
        """Stop capture and release the camera."""
        self._run_flag = False
        self.wait()
        if self._cap is not None:
            self._cap.release()
            self._cap = None
            logger.info("Camera released")
