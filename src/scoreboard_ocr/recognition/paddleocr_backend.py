"""PaddleOCR backend — fast, no preprocessing, works on raw color crops."""

import logging
import cv2
import numpy as np
from paddleocr import PaddleOCR

from .base import Recognizer, RecognitionResult
from .preprocessing import apply_deskew

logger = logging.getLogger(__name__)

_ocr: PaddleOCR | None = None


def _get_ocr() -> PaddleOCR:
    global _ocr
    if _ocr is None:
        logger.info("Initializing PaddleOCR...")
        _ocr = PaddleOCR(lang="en", use_angle_cls=False)
        # Note: 'en' model handles latin characters well. For Cyrillic (ru) team names,
        # PaddleOCR will attempt recognition with its multilingual en model.
        # For full ru+en support, lang="latin" or a custom model can be loaded later.
        logger.info("PaddleOCR initialized")
    return _ocr


class PaddleOCRRecognizer(Recognizer):
    """PaddleOCR — fast, raw color crops, no extra processing."""

    def __init__(self):
        self.ocr = _get_ocr()

    def recognize(self, crop: np.ndarray, mode: str, params: dict) -> RecognitionResult:
        try:
            if mode == "Name":
                # Delegate Name mode to Tesseract for rus+eng support
                from .tesseract_backend import TesseractRecognizer
                return TesseractRecognizer().recognize(crop, mode, params)
            return self._recognize_digits(crop, mode, params)
        except Exception as e:
            logger.exception("PaddleOCR failed: %s", e)
            return RecognitionResult(text="", debug_image=crop)

    def _recognize_digits(self, crop: np.ndarray, mode: str, params: dict) -> RecognitionResult:
        img = crop  # No resize, no sharpen — raw image

        tilt = params.get("tilt", 0)
        if tilt:
            img = apply_deskew(img, tilt)

        results = self.ocr.ocr(img)
        raw_text = self._extract_text(results)

        digits = "".join(c for c in raw_text if c.isdigit())

        if not digits:
            return RecognitionResult(text="", debug_image=img)

        if mode == "Time":
            digits = self._format_time(digits)

        debug_img = img.copy()
        cv2.putText(debug_img, digits, (5, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        return RecognitionResult(text=digits, debug_image=debug_img)

    def _recognize_name(self, crop: np.ndarray, params: dict) -> RecognitionResult:
        results = self.ocr.ocr(crop)
        text = self._extract_text(results)
        return RecognitionResult(text=text.strip(), debug_image=crop)

    @staticmethod
    def _extract_text(results) -> str:
        if not results or len(results) == 0:
            return ""
        page = results[0]
        if isinstance(page, dict):
            texts = page.get("rec_texts", page.get("rec_text", []))
            return "".join(texts) if isinstance(texts, list) else str(texts or "")
        elif isinstance(page, list):
            return "".join(
                (r[1][0] if isinstance(r[1], (list, tuple)) else str(r[1]))
                for r in page if r and len(r) > 1
            )
        return ""

    @staticmethod
    def _format_time(raw: str) -> str:
        if len(raw) >= 2:
            if len(raw) == 4:
                return f"{raw[:2]}:{raw[2:]}"
            elif len(raw) == 3:
                return f"{raw[0]}:{raw[1:]}"
            else:
                return f"0:{raw}"
        return raw
