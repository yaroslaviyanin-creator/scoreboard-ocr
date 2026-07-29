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
        """Recognize text via Tesseract with rus+eng language.

        Uses multiple preprocessing passes: Otsu binarization, adaptive threshold,
        and raw grayscale — takes the best (non-empty) result.
        """
        # Upscale small crops for better Tesseract accuracy
        h, w = crop.shape[:2]
        scale = max(1.0, 60.0 / h)  # at least ~60px height
        if scale > 1.0:
            crop = cv2.resize(crop, (int(w * scale), int(h * scale)))

        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

        # Try multiple binarization strategies, pick best result
        candidates = []

        # Strategy 1: Otsu (works great for bimodal images)
        blur1 = cv2.medianBlur(gray, max(3, (gray.shape[0] // 20) | 1))
        _, otsu = cv2.threshold(blur1, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        white_pct = cv2.countNonZero(otsu) / otsu.size
        if 0.05 < white_pct < 0.90:
            candidates.append(("otsu", cv2.copyMakeBorder(
                cv2.bitwise_not(otsu), 20, 20, 20, 20,
                cv2.BORDER_CONSTANT, value=255,
            )))

        # Strategy 2: Adaptive threshold
        block = max(11, (min(gray.shape[0], gray.shape[1]) // 4) | 1)
        adapt = cv2.adaptiveThreshold(
            cv2.medianBlur(gray, 3), 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block, 4,
        )
        candidates.append(("adaptive", cv2.copyMakeBorder(
            cv2.bitwise_not(adapt), 20, 20, 20, 20,
            cv2.BORDER_CONSTANT, value=255,
        )))

        # Strategy 3: Raw grayscale (sometimes Tesseract handles it best)
        gray_padded = cv2.copyMakeBorder(
            gray, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255,
        )
        candidates.append(("gray", gray_padded))

        # Try each and pick the best (longest result, ignoring garbage)
        best_text = ""
        debug_img = cv2.cvtColor(otsu if 'otsu' in [c[0] for c in candidates] else gray, cv2.COLOR_GRAY2BGR)

        for name, img in candidates:
            try:
                text = pytesseract.image_to_string(
                    img,
                    lang="rus+eng",
                    config="--psm 7",
                ).strip()
            except pytesseract.TesseractError:
                try:
                    text = pytesseract.image_to_string(
                        img, config="--psm 7",
                    ).strip()
                except Exception:
                    continue

            # Prefer longer results (more confident)
            if len(text) > len(best_text):
                best_text = text
                debug_img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                logger.debug("Name via %s: %r", name, text)

        return RecognitionResult(text=best_text, debug_image=debug_img)
