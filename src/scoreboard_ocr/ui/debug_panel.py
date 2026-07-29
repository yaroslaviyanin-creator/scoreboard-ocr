"""Debug panel — right-side panel showing OCR debug images and results."""

import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
import numpy as np

logger = logging.getLogger(__name__)


class DebugPanel:
    """
    Manages the right-side debug panel widgets for each ROI.

    Each ROI gets a container with:
    - A title label showing zone name and recognized value
    - An image label showing the debug (preprocessed) image
    """

    def __init__(self, parent_widget: QWidget, layout: QVBoxLayout):
        self._parent = parent_widget
        self._layout = layout
        self._widgets: dict[str, dict] = {}

    def ensure_widget(self, z_id: str, name: str) -> None:
        """Create debug widgets for a zone if they don't exist yet."""
        if z_id in self._widgets:
            return

        container = QWidget()
        vb = QVBoxLayout(container)
        vb.setContentsMargins(0, 5, 0, 5)

        title = QLabel()
        title.setWordWrap(True)

        img_lbl = QLabel()
        img_lbl.setFixedSize(260, 130)
        img_lbl.setStyleSheet("border: 1px solid #555; background: black;")
        img_lbl.setScaledContents(False)

        vb.addWidget(title)
        vb.addWidget(img_lbl)

        self._layout.addWidget(container)
        self._widgets[z_id] = {
            "container": container,
            "title": title,
            "img": img_lbl,
        }

    def update_result(self, z_id: str, name: str, display_val: str, debug_img: np.ndarray) -> None:
        """Update title and debug image for a zone."""
        if z_id not in self._widgets:
            self.ensure_widget(z_id, name)

        w = self._widgets[z_id]
        w["title"].setText(
            f"<b>{name}: <span style='color:yellow;'>{display_val}</span></b>"
        )

        try:
            h, w_img = debug_img.shape[:2]
            if debug_img.ndim == 2:
                # Grayscale → convert to RGB for QImage
                rgb = debug_img
                bytes_per_line = w_img
                fmt = QImage.Format.Format_Grayscale8
            else:
                # BGR → RGB
                rgb = debug_img[:, :, ::-1].copy()
                bytes_per_line = w_img * 3
                fmt = QImage.Format.Format_RGB888

            q_img = QImage(rgb.data, w_img, h, bytes_per_line, fmt)
            pixmap = QPixmap.fromImage(q_img).scaled(
                260, 130,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            w["img"].setPixmap(pixmap)
        except Exception as e:
            logger.warning("Failed to update debug image for zone %s: %s", z_id, e)

    def remove_zone(self, z_id: str) -> None:
        """Remove debug widgets for a zone."""
        if z_id in self._widgets:
            self._widgets[z_id]["container"].setParent(None)
            del self._widgets[z_id]

    def cleanup_missing(self, active_ids: set) -> None:
        """Remove debug widgets for zones that no longer exist."""
        stale = set(self._widgets.keys()) - active_ids
        for z_id in stale:
            self.remove_zone(z_id)
