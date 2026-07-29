"""Main window — the central UI controller for Scoreboard OCR Tracker v2."""

import os
import time
import logging
import cv2
import numpy as np
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QGraphicsView, QGraphicsScene,
    QGraphicsPixmapItem, QLabel, QScrollArea, QFileDialog,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QImage, QPixmap, QIcon

from ..platform_utils import resource_path, find_tesseract
from ..video import CameraInfo, get_video_inputs
from ..video.video_thread import VideoThread
from ..roi import ROIRect
from ..recognition.worker import OCRWorker
from ..recognition.paddleocr_backend import PaddleOCRRecognizer
from ..presets import save_preset, load_preset, write_templates
from ..output import write_value_atomic
from .debug_panel import DebugPanel

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("YY-tracker v2")
        self.resize(1350, 850)

        # Try to load window icon
        icon_path = resource_path("icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # --- State ---
        self.output_folder = ""
        self.latest_frame: np.ndarray | None = None
        self.is_camera_running = False
        self.roi_history: dict[str, list] = {}
        self.last_stable_values: dict[str, str] = {}
        self.ocr_busy = False
        self.pending_learning: dict | None = None
        self.last_text_check: dict[str, float] = {}

        # --- UI ---
        self._init_ui()

        # --- OCR Worker ---
        logger.info("Using PaddleOCR backend")
        backend = PaddleOCRRecognizer()
        self.ocr_thread = OCRWorker(recognizer=backend, parent=self)

        self.ocr_thread.result_signal.connect(self.on_ocr_result)
        self.ocr_thread.start()

        # --- Video Thread ---
        self.vid_thread = VideoThread(parent=self)
        self.vid_thread.change_pixmap_signal.connect(self.update_image)

        # --- Main Timer ---
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.send_to_ocr)
        self.timer.start(250)

        # --- Camera list ---
        self.refresh_cameras()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _init_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        self.main_layout = QVBoxLayout(central)

        # 1. Top toolbar
        self._init_toolbar()

        # 2. Video + Debug panel
        work = QHBoxLayout()
        self.main_layout.addLayout(work)

        # Graphics scene
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setStyleSheet("background: #111;")
        self.view.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        work.addWidget(self.view, stretch=4)

        # Debug panel (right)
        debug_container = QWidget()
        self.debug_layout = QVBoxLayout(debug_container)
        self.debug_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(300)
        scroll.setWidget(debug_container)
        work.addWidget(scroll, stretch=1)
        self.debug_layout.addWidget(QLabel("<b>DEBUG OCR:</b>"))

        # Video pixmap item
        self.video_item = QGraphicsPixmapItem()
        self.scene.addItem(self.video_item)

        # Debug panel manager
        self.debug_panel = DebugPanel(debug_container, self.debug_layout)

    def _init_toolbar(self) -> None:
        top = QHBoxLayout()

        self.cam_sel = QComboBox()
        btn_ref = QPushButton("🔄")
        btn_ref.setFixedWidth(40)
        btn_ref.clicked.connect(self.refresh_cameras)

        self.btn_start = QPushButton("Start Camera")
        self.btn_start.clicked.connect(self.toggle_camera)

        btn_add = QPushButton("➕ Zone")
        btn_add.clicked.connect(self.add_roi)
        btn_add.setStyleSheet(
            "background: #8b0000; color: white; font-weight: bold; padding: 5px 15px;"
        )

        btn_load = QPushButton("📂 Load Preset")
        btn_load.clicked.connect(self.load_preset_dialog)

        btn_save = QPushButton("💾 Save Preset")
        btn_save.clicked.connect(self.save_preset_dialog)

        self.btn_folder = QPushButton("📁 vMix Folder")
        self.btn_folder.clicked.connect(self.select_folder)

        top.addWidget(self.cam_sel)
        top.addWidget(btn_ref)
        top.addWidget(self.btn_start)
        top.addSpacing(15)
        top.addWidget(btn_add)
        top.addSpacing(15)
        top.addWidget(btn_load)
        top.addWidget(btn_save)
        top.addStretch()
        top.addWidget(self.btn_folder)
        self.main_layout.addLayout(top)

    # ------------------------------------------------------------------
    # Camera
    # ------------------------------------------------------------------

    def refresh_cameras(self) -> None:
        """Refresh the camera list using QMediaDevices only."""
        self.cam_sel.clear()
        try:
            cameras = get_video_inputs()
        except Exception as e:
            logger.exception("Failed to enumerate cameras: %s", e)
            self.cam_sel.addItem("No cameras found")
            return

        if not cameras:
            self.cam_sel.addItem("No cameras found")
            return

        for cam in cameras:
            self.cam_sel.addItem(f"[{cam.index}] {cam.description}", userData=cam.index)

    def toggle_camera(self) -> None:
        """Start or stop the camera capture."""
        if not self.is_camera_running:
            idx = self.cam_sel.currentData()
            if idx is not None:
                self.vid_thread.camera_index = idx
                self.vid_thread.start()
                self.btn_start.setText("Stop")
                self.is_camera_running = True
                logger.info("Camera started: index=%d", idx)
        else:
            self.vid_thread.stop()
            self.btn_start.setText("Start Camera")
            self.is_camera_running = False
            logger.info("Camera stopped")

    @pyqtSlot(np.ndarray)
    def update_image(self, img: np.ndarray) -> None:
        """Display a new frame from the camera."""
        self.latest_frame = img.copy()
        height, width = img.shape[:2]
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        bytes_per_line = width * 3
        q_img = QImage(rgb.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
        self.video_item.setPixmap(QPixmap.fromImage(q_img))
        self.scene.setSceneRect(0, 0, width, height)

    # ------------------------------------------------------------------
    # ROI management
    # ------------------------------------------------------------------

    def add_roi(self) -> None:
        """Add a new ROI zone to the scene."""
        name = f"Zone_{int(time.time() % 1000)}"
        roi = ROIRect(100, 100, 150, 80, name=name)
        self.scene.addItem(roi)
        logger.info("ROI added: %s (%s)", name, roi.id)

    def remove_roi_external(self, roi_obj: ROIRect) -> None:
        """Remove an ROI from the scene and its debug panel."""
        z_id = roi_obj.id
        self.scene.removeItem(roi_obj)
        self.debug_panel.remove_zone(z_id)
        self.roi_history.pop(z_id, None)
        self.last_stable_values.pop(z_id, None)
        self.last_text_check.pop(z_id, None)
        logger.info("ROI removed: %s (%s)", roi_obj.name, z_id)

    @property
    def _all_rois(self) -> list[ROIRect]:
        return [item for item in self.scene.items() if isinstance(item, ROIRect)]

    # ------------------------------------------------------------------
    # Template learning
    # ------------------------------------------------------------------

    def learn_digit_request(self, roi_id: str, digit_char: str) -> None:
        """Queue a template learning request for the next OCR cycle."""
        self.pending_learning = {"id": str(roi_id), "char": str(digit_char)}
        logger.info("Template learning queued: zone=%s digit=%s", roi_id, digit_char)

    # ------------------------------------------------------------------
    # Preset I/O
    # ------------------------------------------------------------------

    def save_preset_dialog(self) -> None:
        """Save current configuration to a JSON preset file."""
        fpath, _ = QFileDialog.getSaveFileName(
            self, "Save Preset", "", "JSON (*.json)",
        )
        if not fpath:
            return

        try:
            rois = self._all_rois
            # Determine templates dir relative to project root
            templates_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..", "..", "templates",
            )
            save_preset(fpath, rois, self.output_folder, templates_dir)
        except Exception as e:
            logger.exception("Failed to save preset: %s", e)

    def load_preset_dialog(self) -> None:
        """Load configuration from a JSON preset file."""
        fpath, _ = QFileDialog.getOpenFileName(
            self, "Load Preset", "", "JSON (*.json)",
        )
        if not fpath:
            return

        try:
            data = load_preset(fpath)

            # Restore templates
            if data["templates"]:
                tpl_dir = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "..", "..", "templates",
                )
                os.makedirs(tpl_dir, exist_ok=True)
                write_templates(data["templates"], tpl_dir)
                self.ocr_thread.load_templates()

            # Clear existing ROIs
            for roi in self._all_rois:
                self.remove_roi_external(roi)

            # Restore output folder
            self.output_folder = data.get("output_folder", "")
            if self.output_folder:
                self.btn_folder.setText(f"📁 {os.path.basename(self.output_folder)}")

            # Create new ROIs
            for r_data in data["rois"]:
                roi = ROIRect(
                    r_data["pos"][0], r_data["pos"][1],
                    r_data["size"][0], r_data["size"][1],
                    name=r_data["name"],
                )
                roi.mode = r_data.get("mode", "Standard")
                roi.params = r_data.get("params", {
                    "blur": 5, "thresh": 130, "morph": 1, "sens": 35, "tilt": 0,
                })
                roi.update_label()
                self.scene.addItem(roi)

            # Restore camera index if present
            if data.get("camera_index") is not None:
                idx = self.cam_sel.findData(data["camera_index"])
                if idx >= 0:
                    self.cam_sel.setCurrentIndex(idx)

            logger.info("Preset loaded successfully: %d ROIs", len(data["rois"]))
        except Exception as e:
            logger.exception("Failed to load preset: %s", e)

    # ------------------------------------------------------------------
    # Output folder
    # ------------------------------------------------------------------

    def select_folder(self) -> None:
        """Choose output folder for .txt files."""
        path = QFileDialog.getExistingDirectory(self, "vMix Output Folder")
        if path:
            self.output_folder = path
            self.btn_folder.setText(f"📁 {os.path.basename(path)}")
            logger.info("Output folder set: %s", path)

    # ------------------------------------------------------------------
    # OCR cycle
    # ------------------------------------------------------------------

    def send_to_ocr(self) -> None:
        """Collect crops from all ROIs and submit to OCR worker (every 250ms)."""
        if self.ocr_busy or self.latest_frame is None or not self.is_camera_running:
            return

        current_time = time.time()
        crops = []
        cur_learn = self.pending_learning

        for roi in self._all_rois:
            # Rate-limit Name mode: once every 5 seconds
            if roi.mode == "Name":
                last_check = self.last_text_check.get(roi.id, 0)
                if current_time - last_check < 5.0:
                    continue
                self.last_text_check[roi.id] = current_time

            try:
                r = roi.sceneBoundingRect()
                ih, iw = self.latest_frame.shape[:2]

                x1 = max(0, int(r.x()))
                y1 = max(0, int(r.y()))
                x2 = min(iw, int(r.x() + r.width()))
                y2 = min(ih, int(r.y() + r.height()))

                if x2 > x1 and y2 > y1:
                    p = roi.params.copy()

                    # Inject template learning if pending for this zone
                    if cur_learn and str(roi.id) == cur_learn["id"]:
                        p["save_template"] = cur_learn["char"]
                        self.pending_learning = None

                    crop = self.latest_frame[y1:y2, x1:x2].copy()
                    crops.append((roi.id, roi.name, roi.mode, p, crop))
            except Exception as e:
                logger.warning(
                    "Failed to prepare crop for ROI %s (%s): %s",
                    roi.name, roi.id, e,
                )
                continue

        if crops:
            self.ocr_busy = True
            self.ocr_thread.process_crops(crops)

    @pyqtSlot(dict, dict)
    def on_ocr_result(self, results: dict, debug_imgs: dict) -> None:
        """Handle OCR results: update debug panel and write stable values to .txt."""
        self.ocr_busy = False

        if not self.is_camera_running:
            return

        active_ids = {roi.id for roi in self._all_rois}

        for z_id, img in debug_imgs.items():
            if z_id not in active_ids:
                continue

            d = results.get(z_id, {"text": "", "name": "???"})
            val = d["text"]
            name = d["name"]

            # Stabilization: require same value for 2 consecutive cycles
            history = self.roi_history.setdefault(z_id, [])
            history.append(val)
            if len(history) > 2:
                history.pop(0)
            is_stable = (len(history) == 2 and history[0] == history[1] and val != "")

            # Show last stable value to avoid flickering
            display_val = self.last_stable_values.get(z_id, val) if not is_stable else val
            if is_stable:
                self.last_stable_values[z_id] = val

            self.debug_panel.update_result(z_id, name, display_val, img)

            # Write to output file when stable
            if self.output_folder and is_stable:
                ok = write_value_atomic(self.output_folder, name, display_val)
                if not ok:
                    logger.warning("Failed to write output for zone %s", name)

        # Clean up debug panels for removed zones
        self.debug_panel.cleanup_missing(active_ids)

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:
        """Clean up threads on window close."""
        logger.info("Shutting down...")
        self.vid_thread.stop()
        self.ocr_thread.stop()
        event.accept()
