"""Tests for recognition backends (without GUI)."""

import cv2
import numpy as np
import pytest
from scoreboard_ocr.recognition.base import RecognitionResult
from scoreboard_ocr.recognition.tesseract_backend import TesseractRecognizer
from scoreboard_ocr.recognition.template_backend import TemplateSegmentRecognizer


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def make_digit_image(digit: str, size: tuple = (200, 100)) -> np.ndarray:
    """Generate a synthetic BGR image with a white digit on dark background."""
    img = np.zeros((size[1], size[0], 3), dtype=np.uint8)
    cv2.putText(
        img, digit, (60, 75),
        cv2.FONT_HERSHEY_SIMPLEX, 2.5, (255, 255, 255), 5,
    )
    return img


def make_text_image(text: str, size: tuple = (400, 80)) -> np.ndarray:
    """Generate a synthetic BGR image with white text on dark background."""
    img = np.zeros((size[1], size[0], 3), dtype=np.uint8)
    cv2.putText(
        img, text, (20, 55),
        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3,
    )
    return img


DEFAULT_PARAMS = {
    "blur": 3,
    "thresh": 130,
    "morph": 1,
    "sens": 35,
    "tilt": 0,
}


# ------------------------------------------------------------------
# TemplateSegmentRecognizer
# ------------------------------------------------------------------

class TestTemplateSegmentRecognizer:
    """Template + 7-segment backend tests."""

    @pytest.fixture
    def recognizer(self):
        return TemplateSegmentRecognizer()

    def test_standard_mode_does_not_crash(self, recognizer):
        """Standard mode on a synthetic digit image returns a result without exception."""
        img = make_digit_image("5")
        result = recognizer.recognize(img, "Standard", DEFAULT_PARAMS)
        assert isinstance(result, RecognitionResult)
        assert result.debug_image is not None

    def test_time_mode_does_not_crash(self, recognizer):
        """Time mode on synthetic digits returns a result."""
        img = make_digit_image("12")
        result = recognizer.recognize(img, "Time", DEFAULT_PARAMS)
        assert isinstance(result, RecognitionResult)

    def test_name_mode_does_not_crash(self, recognizer):
        """Name mode on synthetic text returns a result."""
        img = make_text_image("TEAM A")
        result = recognizer.recognize(img, "Name", DEFAULT_PARAMS)
        assert isinstance(result, RecognitionResult)

    def test_7segment_mode_does_not_crash(self, recognizer):
        """7-segment mode does not crash."""
        img = make_digit_image("8")
        result = recognizer.recognize(img, "7-segment", DEFAULT_PARAMS)
        assert isinstance(result, RecognitionResult)

    def test_format_time_4_digits(self, recognizer):
        """Time formatting with 4 digits."""
        assert recognizer._format_time("1234") == "12:34"

    def test_format_time_3_digits(self, recognizer):
        """Time formatting with 3 digits."""
        assert recognizer._format_time("123") == "1:23"

    def test_format_time_2_digits(self, recognizer):
        """Time formatting with 2 digits."""
        assert recognizer._format_time("12") == "0:12"

    def test_empty_crop_does_not_crash(self, recognizer):
        """An empty/black crop should not raise an exception."""
        img = np.zeros((50, 150, 3), dtype=np.uint8)
        result = recognizer.recognize(img, "Standard", DEFAULT_PARAMS)
        assert isinstance(result, RecognitionResult)


# ------------------------------------------------------------------
# TesseractRecognizer
# ------------------------------------------------------------------

class TestTesseractRecognizer:
    """Tesseract backend tests."""

    @pytest.fixture
    def recognizer(self):
        return TesseractRecognizer()

    def test_standard_mode_returns_result(self, recognizer):
        """Standard mode returns a RecognitionResult."""
        img = make_digit_image("7")
        result = recognizer.recognize(img, "Standard", DEFAULT_PARAMS)
        assert isinstance(result, RecognitionResult)
        assert isinstance(result.text, str)

    def test_name_mode_returns_result(self, recognizer):
        """Name mode returns a RecognitionResult."""
        img = make_text_image("HOME")
        result = recognizer.recognize(img, "Name", DEFAULT_PARAMS)
        assert isinstance(result, RecognitionResult)
        assert isinstance(result.text, str)

    def test_time_mode_does_not_crash(self, recognizer):
        """Time mode does not crash."""
        img = make_digit_image("90")
        result = recognizer.recognize(img, "Time", DEFAULT_PARAMS)
        assert isinstance(result, RecognitionResult)


# ------------------------------------------------------------------
# RecognitionResult
# ------------------------------------------------------------------

class TestRecognitionResult:
    """RecognitionResult dataclass tests."""

    def test_defaults(self):
        r = RecognitionResult()
        assert r.text == ""
        assert r.debug_image.shape == (1, 1, 3)

    def test_custom_values(self):
        img = np.ones((50, 50, 3), dtype=np.uint8) * 128
        r = RecognitionResult(text="42", debug_image=img)
        assert r.text == "42"
        assert r.debug_image.shape == (50, 50, 3)
