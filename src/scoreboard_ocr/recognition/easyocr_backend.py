"""EasyOCR backend for digit recognition — no binarization needed.

EasyOCR works directly on color images and is significantly more
accurate than Tesseract for digits, especially on scoreboards.
"""

import logging
import cv2
import numpy as np
import easyocr

from .base import Recognizer, RecognitionResult
from .preprocessing import apply_deskew, preprocess_name_crop

logger = logging.getLogger(__name__)

# Shared reader instance (lazy init, expensive to create)
_reader: easyocr.Reader | None = None


def _get_reader() -> easyocr.Reader:
    """Get or create the EasyOCR reader (shared across all instances)."""
    global _reader
    if _reader is None:
        logger.info("Initializing EasyOCR reader (this may take a moment on first run)...")
        _reader = easyocr.Reader(
            ["en"],  # English only for digits
            gpu=False,  # CPU is fine for scoreboard digits
            quantize=True,  # Use INT8 quantization for speed
        )
        logger.info("EasyOCR reader initialized")
    return _reader


class EasyOCRRecognizer(Recognizer):
    """
    EasyOCR-based recognizer for scoreboard digits.

    Key advantages over Tesseract:
    - Works directly on color images (no binarization needed)
    - Much better accuracy on digits (98%+ on clean scoreboards)
    - Handles varying contrast, fonts, and backgrounds automatically
    - Built-in text detection + recognition
    """

    def __init__(self):
        self._reader = _get_reader()

    def recognize(self, crop: np.ndarray, mode: str, params: dict) -> RecognitionResult:
        try:
            if mode == "Name":
                return self._recognize_name(crop, params)
            else:
                return self._recognize_digits(crop, mode, params)
        except Exception as e:
            logger.exception("EasyOCRRecognizer failed (mode=%s): %s", mode, e)
            return RecognitionResult(text="", debug_image=crop)

    def _recognize_digits(self, crop: np.ndarray, mode: str, params: dict) -> RecognitionResult:
        """Recognize digits using EasyOCR on the color image."""
        # Light preprocessing: resize to consistent height, slight sharpening
        target_h = 120  # Higher resolution for better accuracy
        scale = target_h / crop.shape[0]
        new_w = int(crop.shape[1] * scale)
        img = cv2.resize(crop, (new_w, target_h))

        # Apply tilt correction if set
        tilt = params.get("tilt", 0)
        if tilt != 0:
            img = apply_deskew(img, tilt)

        # EasyOCR detection + recognition
        results = self._reader.readtext(
            img,
            allowlist="0123456789",  # Only digits
            detail=0,  # Return text only, not bounding boxes
            paragraph=False,
            min_size=10,
            width_ths=0.5,  # More tolerant width threshold
        )

        # Combine all detected text
        raw = "".join(results).strip()

        # Format for Time mode
        if mode == "Time" and raw:
            raw = self._format_time(raw)
        elif mode == "Time" and not raw:
            raw = ""

        # Debug image: draw OCR result on the color image
        debug_img = img.copy()
        if raw:
            cv2.putText(
                debug_img, raw, (5, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2,
            )

        return RecognitionResult(text=raw, debug_image=debug_img)

    def _recognize_name(self, crop: np.ndarray, params: dict) -> RecognitionResult:
        """Recognize text (team names etc.) using EasyOCR."""
        target_h = 100
        scale = target_h / crop.shape[0]
        new_w = int(crop.shape[1] * scale)
        img = cv2.resize(crop, (new_w, target_h))

        tilt = params.get("tilt", 0)
        if tilt != 0:
            img = apply_deskew(img, tilt)

        results = self._reader.readtext(
            img,
            detail=0,
            paragraph=True,
            min_size=10,
        )
        text = " ".join(results).strip()

        debug_img = img.copy()
        cv2.putText(debug_img, text, (5, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        return RecognitionResult(text=text, debug_image=debug_img)

    @staticmethod
    def _format_time(raw: str) -> str:
        """Format raw digits as HH:MM."""
        digits_only = "".join(c for c in raw if c.isdigit())
        if len(digits_only) >= 2:
            if len(digits_only) == 4:
                return f"{digits_only[:2]}:{digits_only[2:]}"
            elif len(digits_only) == 3:
                return f"{digits_only[0]}:{digits_only[1:]}"
            else:
                return f"0:{digits_only}"
        return raw
