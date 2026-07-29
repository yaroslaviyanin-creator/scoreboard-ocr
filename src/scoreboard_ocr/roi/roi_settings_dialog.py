"""ROI settings dialog — mode, parameters, template learning, and deletion."""

import logging
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QPushButton, QHBoxLayout, QSlider, QLabel,
)
from PyQt6.QtCore import Qt

logger = logging.getLogger(__name__)


class ROISettingsDialog(QDialog):
    """
    Modal-less settings dialog for a single ROI.
    Changes are applied live so the user sees them in the debug panel immediately.
    """

    def __init__(self, roi_obj, parent=None):
        super().__init__(parent)
        self.roi = roi_obj
        self.setWindowTitle(f"Settings: {self.roi.name}")
        self.setModal(False)
        self.resize(380, 480)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        # Name
        self.name_input = QLineEdit(self.roi.name)
        self.name_input.textChanged.connect(self._apply_live)

        # Mode
        self.mode_input = QComboBox()
        self.mode_input.addItems(["Standard", "Time", "Name", "7-segment"])
        self.mode_input.setCurrentText(self.roi.mode)
        self.mode_input.currentTextChanged.connect(self._apply_live)

        # Sliders
        self.sld_blur = self._make_slider(1, 21, self.roi.params.get("blur", 5))
        self.sld_thresh = self._make_slider(0, 255, self.roi.params.get("thresh", 130))
        self.sld_morph = self._make_slider(0, 10, self.roi.params.get("morph", 1))
        self.sld_sens = self._make_slider(5, 100, self.roi.params.get("sens", 35))
        self.sld_tilt = self._make_slider(-45, 45, self.roi.params.get("tilt", 0))

        form.addRow("Name (output file):", self.name_input)
        form.addRow("Mode:", self.mode_input)
        form.addRow("Blur (LED):", self.sld_blur)
        form.addRow("Threshold:", self.sld_thresh)
        form.addRow("Dilate (sticking):", self.sld_morph)
        form.addRow("Sensitivity:", self.sld_sens)
        form.addRow("Tilt correction:", self.sld_tilt)
        layout.addLayout(form)

        # Template learning
        layout.addWidget(QLabel("<hr><b>TEMPLATE LEARNING (0-9):</b>"))
        learn_layout = QHBoxLayout()
        self.learn_input = QLineEdit()
        self.learn_input.setPlaceholderText("Digit")
        self.learn_input.setFixedWidth(60)
        self.btn_learn = QPushButton("📸 Save as template")
        self.btn_learn.setStyleSheet(
            "background: #006400; color: white; font-weight: bold;"
        )
        self.btn_learn.clicked.connect(self._on_learn_click)
        learn_layout.addWidget(self.learn_input)
        learn_layout.addWidget(self.btn_learn)
        layout.addLayout(learn_layout)

        # Bottom buttons
        btns = QHBoxLayout()
        self.btn_del = QPushButton("🗑 Delete zone")
        self.btn_del.setStyleSheet(
            "background: #8b0000; color: white; padding: 5px;"
        )
        self.btn_ok = QPushButton("Close")
        btns.addWidget(self.btn_del)
        btns.addStretch()
        btns.addWidget(self.btn_ok)
        layout.addLayout(btns)

        self.btn_ok.clicked.connect(self.accept)
        self.btn_del.clicked.connect(self._on_delete)

    @staticmethod
    def _make_slider(min_val: int, max_val: int, value: int) -> QSlider:
        s = QSlider(Qt.Orientation.Horizontal)
        s.setRange(min_val, max_val)
        s.setValue(value)
        return s

    def _apply_live(self) -> None:
        """Sync all parameters back to the ROI object immediately."""
        self.roi.name = self.name_input.text()
        self.roi.mode = self.mode_input.currentText()
        self.roi.params["blur"] = self.sld_blur.value()
        self.roi.params["thresh"] = self.sld_thresh.value()
        self.roi.params["morph"] = self.sld_morph.value()
        self.roi.params["sens"] = self.sld_sens.value()
        self.roi.params["tilt"] = self.sld_tilt.value()
        self.roi.update_label()

    def _on_learn_click(self) -> None:
        """Request the main window to capture a template for this ROI."""
        digit = self.learn_input.text().strip()
        if not digit or len(digit) != 1:
            logger.warning("Invalid template digit: %r", digit)
            return
        try:
            view = self.roi.scene().views()[0]
            main_win = view.window()
            if hasattr(main_win, "learn_digit_request"):
                main_win.learn_digit_request(self.roi.id, digit)
                self.learn_input.clear()
        except Exception as e:
            logger.exception("Failed to send learn request: %s", e)

    def _on_delete(self) -> None:
        """Safely remove this ROI via the main window."""
        try:
            view = self.roi.scene().views()[0]
            main_win = view.window()
            if hasattr(main_win, "remove_roi_external"):
                main_win.remove_roi_external(self.roi)
            self.accept()
        except Exception as e:
            logger.exception("Failed to delete ROI: %s", e)
