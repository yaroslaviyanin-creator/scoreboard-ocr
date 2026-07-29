"""TrOCR backend — Microsoft's Transformer-based OCR (tiny, accurate, no preprocessing).

Name mode → EasyOCR (ru+en, handles mixed Cyrillic/Latin text).
Standard/Time → TrOCR digit recognition (fast, lightweight).
"""

import logging
import cv2
import numpy as np
from PIL import Image
from .base import Recognizer, RecognitionResult

logger = logging.getLogger(__name__)

_MODEL_NAME = "microsoft/trocr-small-printed"
_processor = None
_model = None
_easyocr_reader = None


def _init_model():
    global _processor, _model
    if _processor is None:
        logger.info("Loading TrOCR model: %s (this happens once)...", _MODEL_NAME)
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel
        _processor = TrOCRProcessor.from_pretrained(_MODEL_NAME, use_fast=False)
        _model = VisionEncoderDecoderModel.from_pretrained(_MODEL_NAME)
        logger.info("TrOCR model loaded (61M params)")


def _get_easyocr():
    global _easyocr_reader
    if _easyocr_reader is None:
        logger.info("Loading EasyOCR reader for ru+en name recognition...")
        import easyocr
        _easyocr_reader = easyocr.Reader(['ru', 'en'], gpu=False)
        logger.info("EasyOCR reader ready")
    return _easyocr_reader


class TrOCRRecognizer(Recognizer):
    """TrOCR — Microsoft's Transformer OCR for digits. Name mode → EasyOCR ru+en."""

    def __init__(self):
        _init_model()

    def recognize(self, crop: np.ndarray, mode: str, params: dict) -> RecognitionResult:
        # Name mode → EasyOCR ru+en (handles mixed Cyrillic/Latin text)
        if mode == "Name":
            return self._recognize_name_easyocr(crop)

        # Standard / Time / 7-segment → TrOCR (light, fast)
        try:
            raw_text = _run_trocr(crop)
            return self._recognize_digits(raw_text, crop, mode)
        except Exception as e:
            logger.exception("TrOCR failed (mode=%s): %s", mode, e)
            return RecognitionResult(text="", debug_image=crop)

    def _recognize_name_easyocr(self, crop: np.ndarray) -> RecognitionResult:
        """EasyOCR ru+en — handles mixed Cyrillic/Latin text natively."""
        try:
            reader = _get_easyocr()
            rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            results = reader.readtext(rgb, detail=0)
            text = " ".join(results).strip()
            return RecognitionResult(text=text, debug_image=self._debug_img(crop, text))
        except Exception as e:
            logger.exception("EasyOCR name recognition failed: %s", e)
            return RecognitionResult(text="", debug_image=crop)

    def _recognize_digits(self, raw_text: str, crop: np.ndarray, mode: str) -> RecognitionResult:
        digits = "".join(c for c in raw_text if c.isdigit())
        if not digits:
            return RecognitionResult(text="", debug_image=self._debug_img(crop, ""))

        if mode == "Time":
            digits = self._format_time(digits)

        return RecognitionResult(text=digits, debug_image=self._debug_img(crop, digits))

    @staticmethod
    def _format_time(raw: str) -> str:
        if len(raw) >= 4:
            return f"{raw[:2]}:{raw[2:4]}"
        elif len(raw) == 3:
            return f"{raw[0]}:{raw[1:]}"
        elif len(raw) == 2:
            return f"0:{raw}"
        return raw

    @staticmethod
    def _debug_img(img: np.ndarray, text: str) -> np.ndarray:
        d = img.copy()
        cv2.putText(d, text, (5, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        return d


def _run_trocr(img: np.ndarray) -> str:
    h, w = img.shape[:2]
    if h < 16 or w < 16:
        return ""
    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    pixel_values = _processor(pil_img, return_tensors="pt").pixel_values
    generated_ids = _model.generate(pixel_values, max_new_tokens=16)
    text = _processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    return text
