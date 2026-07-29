"""Recognition — abstractions and backends for OCR.

v2 improvements:
- Auto-binarization (Otsu → adaptive → mean)
- Tesseract-first digit recognition with contour fallback
"""

from .base import Recognizer, RecognitionResult

__all__ = ["Recognizer", "RecognitionResult"]
