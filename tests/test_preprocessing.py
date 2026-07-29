"""Tests for image preprocessing utilities."""

import cv2
import numpy as np
import pytest
from scoreboard_ocr.recognition.preprocessing import (
    apply_deskew,
    preprocess_digit_crop,
    preprocess_name_crop,
)


class TestDeskew:
    """Deskew (tilt correction) tests."""

    def test_zero_angle_returns_unchanged(self):
        """Deskew with angle=0 should return the original image."""
        img = np.random.randint(0, 255, (100, 200, 3), dtype=np.uint8)
        result = apply_deskew(img, 0.0)
        assert result.shape == img.shape
        assert np.array_equal(result, img)

    def test_nonzero_angle_preserves_channels(self):
        """Deskew should preserve the number of channels."""
        img = np.random.randint(0, 255, (100, 200, 3), dtype=np.uint8)
        result = apply_deskew(img, 15.0)
        assert result.ndim == img.ndim

    def test_grayscale(self):
        """Deskew works on grayscale images."""
        img = np.random.randint(0, 255, (80, 160), dtype=np.uint8)
        result = apply_deskew(img, -10.0)
        assert result.ndim == 2


class TestPreprocessDigitCrop:
    """Preprocessing pipeline tests."""

    def test_basic_pipeline_returns_tuple(self):
        """Preprocessing should return (binary, debug_color) tuple."""
        img = np.random.randint(0, 255, (60, 200, 3), dtype=np.uint8)
        binary, debug = preprocess_digit_crop(img)
        assert isinstance(binary, np.ndarray)
        assert isinstance(debug, np.ndarray)
        assert binary.ndim == 2  # grayscale
        assert debug.ndim == 3   # BGR

    def test_handles_all_zeros(self):
        """Preprocessing should not crash on a flat black image."""
        img = np.zeros((50, 150, 3), dtype=np.uint8)
        binary, debug = preprocess_digit_crop(img)
        assert binary is not None
        assert debug is not None

    def test_handles_all_ones(self):
        """Preprocessing should not crash on a flat white image."""
        img = np.full((50, 150, 3), 255, dtype=np.uint8)
        binary, debug = preprocess_digit_crop(img)
        assert binary is not None
        assert debug is not None

    def test_blur_always_odd(self):
        """Even blur values should be converted to odd (medianBlur requirement)."""
        img = np.random.randint(0, 255, (60, 200, 3), dtype=np.uint8)
        # blur=4 (even) → should become 5 without crash
        binary, debug = preprocess_digit_crop(img, blur=4)
        assert binary is not None


class TestPreprocessNameCrop:
    """Name-mode preprocessing tests."""

    def test_returns_padded_inverted(self):
        """Name preprocessing should return padded, inverted image for Tesseract."""
        img = np.random.randint(0, 255, (40, 180, 3), dtype=np.uint8)
        padded, debug = preprocess_name_crop(img, padding=30)
        assert padded.shape[0] == 40 * (100 / 40) + 2 * 30  # resized + padding
        assert padded.ndim == 2


class TestGeneratedImages:
    """Tests with programmatically generated text images."""

    @staticmethod
    def _make_text_image(text: str, size: tuple = (300, 80)) -> np.ndarray:
        """Generate a synthetic BGR image with white text on dark background."""
        img = np.zeros((size[1], size[0], 3), dtype=np.uint8)
        cv2.putText(
            img, text, (20, 50),
            cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3,
        )
        return img

    def test_synthetic_text_does_not_crash(self):
        """Preprocessing should handle generated text images."""
        img = self._make_text_image("12:34")
        binary, debug = preprocess_digit_crop(img)
        assert binary.size > 0
        assert debug.size > 0

    def test_synthetic_name_does_not_crash(self):
        """Name preprocessing should handle generated text images."""
        img = self._make_text_image("TEAM A")
        padded, debug = preprocess_name_crop(img)
        assert padded.size > 0
        assert debug.size > 0
