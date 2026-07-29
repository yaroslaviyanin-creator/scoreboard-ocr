"""TrOCR backend — Microsoft's Transformer-based OCR (tiny, accurate, no preprocessing)."""

import logging
import cv2
import numpy as np
from PIL import Image
from .base import Recognizer, RecognitionResult

logger = logging.getLogger(__name__)

_MODEL_NAME = "microsoft/trocr-small-printed"
_processor = None
_model = None


def _init_model():
    global _processor, _model
    if _processor is None:
        logger.info("Loading TrOCR model: %s (this happens once)...", _MODEL_NAME)
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel
        # use_fast=False avoids the sentencepiece→tokenizers conversion issue in transformers v5
        _processor = TrOCRProcessor.from_pretrained(_MODEL_NAME, use_fast=False)
        _model = VisionEncoderDecoderModel.from_pretrained(_MODEL_NAME)
        logger.info("TrOCR model loaded")


class TrOCRRecognizer(Recognizer):
    """TrOCR — Microsoft's Transformer OCR. No binarization, just raw image in."""

    def __init__(self):
        _init_model()

    def recognize(self, crop: np.ndarray, mode: str, params: dict) -> RecognitionResult:
        try:
            raw_text = _run_trocr(crop)
            if mode in ("Standard", "Time", "7-segment"):
                return self._recognize_digits(raw_text, crop, mode)
            else:
                text = raw_text.strip()
                return RecognitionResult(text=text, debug_image=self._debug_img(crop, text))
        except Exception as e:
            logger.exception("TrOCR failed (mode=%s): %s", mode, e)
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
