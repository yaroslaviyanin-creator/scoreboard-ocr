"""Camera device enumeration using QMediaDevices — the single source of truth."""

import logging
from PyQt6.QtMultimedia import QMediaDevices, QCameraDevice

logger = logging.getLogger(__name__)


class CameraInfo:
    """Lightweight camera info dataclass for UI consumption."""

    def __init__(self, index: int, description: str, device_id: str = ""):
        self.index = index
        self.description = description
        self.device_id = device_id

    def __repr__(self) -> str:
        return f"CameraInfo(index={self.index}, description={self.description!r})"


def get_video_inputs() -> list[CameraInfo]:
    """
    Enumerate available camera devices exclusively via QMediaDevices.

    Never opens cv2.VideoCapture for enumeration — that triggers
    system camera permission prompts and is slow.

    Returns:
        List of CameraInfo objects for all detected video inputs.
    """
    devices: list[CameraInfo] = []
    try:
        qt_cams = QMediaDevices.videoInputs()
    except Exception as e:
        logger.exception("QMediaDevices.videoInputs() failed: %s", e)
        return devices

    for idx, device in enumerate(qt_cams):
        try:
            desc = device.description()
        except Exception:
            desc = f"Camera {idx}"
        device_id = device.id() if hasattr(device, "id") else ""
        cam = CameraInfo(index=idx, description=desc, device_id=device_id)
        devices.append(cam)
        logger.debug("Camera[%d]: %s (id=%s)", idx, desc, device_id)

    logger.info("Found %d camera(s) via QMediaDevices", len(devices))
    return devices
