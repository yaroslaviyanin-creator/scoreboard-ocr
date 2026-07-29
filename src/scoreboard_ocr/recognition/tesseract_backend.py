"""Tesseract OCR backend — uses pytesseract for text recognition."""

import logging
import cv2
import numpy as np
import pytesseract

from .base import Recognizer, RecognitionResult
from .preprocessing import preprocess_name_crop, preprocess_digit_crop

logger = logging.getLogger(__name__)


class TesseractRecognizer(Recognizer):
    """
    Pure Tesseract-based OCR backend.

    Used as the primary backend for "Name" mode and as a fallback
    for digit modes when template matching fails.
    """

    def __init__(self, tesseract_cmd: str | None = None):
        """
        Args:
            tesseract_cmd: Path to tesseract binary. If None, uses what's in PATH.
        """
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
            logger.info("Tesseract configured: %s", tesseract_cmd)

    def recognize(
        self,
        crop: np.ndarray,
        mode: str,
        params: dict,
    ) -> RecognitionResult:
        try:
            if mode == "Name":
                return self._recognize_name(crop, params)
            else:
                return self._recognize_digit(crop, params)
        except Exception as e:
            logger.exception("Tesseract recognize failed (mode=%s): %s", mode, e)
            return RecognitionResult(text="", debug_image=crop)

    def _recognize_digit(self, crop: np.ndarray, params: dict) -> RecognitionResult:
        """Recognize a single digit via Tesseract (PSM 10)."""
        binary, debug_img = preprocess_digit_crop(
            crop,
            blur=params.get("blur", 3),
            thresh=params.get("thresh", 130),
            tilt=params.get("tilt", 0),
        )
        # Tesseract needs dark text on white
        padded = cv2.copyMakeBorder(
            cv2.bitwise_not(binary), 30, 30, 30, 30,
            cv2.BORDER_CONSTANT, value=255,
        )
        text = pytesseract.image_to_string(
            padded,
            config="--psm 10 -c tessedit_char_whitelist=0123456789",
        ).strip()
        digit = text[0] if text and text[0].isdigit() else ""
        return RecognitionResult(text=digit, debug_image=debug_img)

    def _recognize_name(self, crop: np.ndarray, params: dict) -> RecognitionResult:
        """Recognize text via Tesseract with rus+eng language (PSM 7).

        Uses ALL user-adjustable parameters from ROI settings:
          blur (1-21)  — median blur to remove noise
          thresh (0-255) — binarization threshold
          morph (0-10) — morphological dilation (fattens text)
          sens (5-100) — sensitivity, adjusts threshold proportionally
          tilt (-45..45) — deskew angle
        """
        padded, debug_img = preprocess_name_crop(
            crop,
            blur=params.get("blur", 3),
            thresh=params.get("thresh", 130),
            tilt=params.get("tilt", 0),
            morph=params.get("morph", 1),
            sens=params.get("sens", 35),
        )
        try:
            text = pytesseract.image_to_string(
                padded,
                lang="rus+eng",
                config="--psm 7",
            ).strip()
        except pytesseract.TesseractError:
            logger.warning("Tesseract rus+eng failed, falling back to eng only")
            text = pytesseract.image_to_string(
                padded,
                config="--psm 7",
            ).strip()
        return RecognitionResult(text=text, debug_image=debug_img)
