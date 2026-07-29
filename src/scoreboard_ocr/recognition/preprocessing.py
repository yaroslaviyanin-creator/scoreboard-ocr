"""Common image preprocessing routines shared across all OCR backends."""

import logging
import cv2
import numpy as np

logger = logging.getLogger(__name__)


def apply_deskew(img: np.ndarray, angle_deg: float) -> np.ndarray:
    """
    Apply horizontal shear (deskew) to compensate for camera tilt.

    Args:
        img: Grayscale or BGR image.
        angle_deg: Tilt angle in degrees. 0 = no change.

    Returns:
        Deskewed image (same number of channels).
    """
    if angle_deg == 0:
        return img

    try:
        h, w = img.shape[:2]
        tan_a = np.tan(np.deg2rad(angle_deg))
        M = np.float32([[1, -tan_a, 0], [0, 1, 0]])
        pad = int(abs(tan_a * h))
        img_padded = cv2.copyMakeBorder(
            img, 0, 0, pad, pad, cv2.BORDER_CONSTANT, value=[0, 0, 0]
        )
        M[0, 2] = pad
        result = cv2.warpAffine(img_padded, M, (w + pad * 2, h))
        return result
    except Exception as e:
        logger.warning("Deskew failed (angle=%s): %s", angle_deg, e)
        return img


def preprocess_digit_crop(
    img_bgr: np.ndarray,
    *,
    target_height: int = 100,
    blur: int = 3,
    thresh: int = 130,
    tilt: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Standard preprocessing pipeline for digit/7-segment crops.

    1. Resize to target height while preserving aspect ratio.
    2. Deskew.
    3. Convert to grayscale.
    4. Median blur.
    5. Binary threshold.
    6. Invert if background is mostly white (more white than black).

    Returns:
        (binary_image, debug_color_image)
    """
    scale = target_height / img_bgr.shape[0]
    new_w = int(img_bgr.shape[1] * scale)
    img_resized = cv2.resize(img_bgr, (new_w, target_height))

    img_deskewed = apply_deskew(img_resized, tilt)

    gray = cv2.cvtColor(img_deskewed, cv2.COLOR_BGR2GRAY)

    blur_val = blur if blur % 2 != 0 else blur + 1
    blurred = cv2.medianBlur(gray, blur_val)

    _, binary = cv2.threshold(blurred, thresh, 255, cv2.THRESH_BINARY)

    # Invert if more than 50% white (most scoreboards are dark on light)
    if cv2.countNonZero(binary) > (binary.size / 2):
        binary = cv2.bitwise_not(binary)

    debug_img = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)

    return binary, debug_img


def preprocess_name_crop(
    img_bgr: np.ndarray,
    *,
    target_height: int = 100,
    blur: int = 3,
    thresh: int = 130,
    tilt: int = 0,
    padding: int = 40,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Preprocessing for text/name zones (Tesseract).

    Same pipeline as digits, but the result is padded and inverted for Tesseract
    (Tesseract expects dark text on white background with some margin).

    Returns:
        (tesseract_ready_image, debug_color_image)
    """
    binary, debug_img = preprocess_digit_crop(
        img_bgr, target_height=target_height, blur=blur,
        thresh=thresh, tilt=tilt,
    )
    # Tesseract works best with dark text on white background + generous padding
    inverted = cv2.bitwise_not(binary)
    padded = cv2.copyMakeBorder(
        inverted, padding, padding, padding, padding,
        cv2.BORDER_CONSTANT, value=255,
    )
    return padded, debug_img
