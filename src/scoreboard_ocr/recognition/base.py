"""Abstract base class for OCR recognizers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import numpy as np


@dataclass
class RecognitionResult:
    """Result of a single recognition call."""
    text: str = ""
    debug_image: np.ndarray = field(default_factory=lambda: np.zeros((1, 1, 3), dtype=np.uint8))


class Recognizer(ABC):
    """
    Abstract interface for OCR backends.

    Implementations receive a BGR crop image, a mode string
    (Standard / Time / Name / 7-segment), and zone parameters dict.

    They return a RecognitionResult with the recognized text and
    a debug image for the right-side panel.
    """

    @abstractmethod
    def recognize(
        self,
        crop: np.ndarray,
        mode: str,
        params: dict,
    ) -> RecognitionResult:
        """
        Recognize text from a BGR image crop.

        Args:
            crop: BGR image (numpy array) of the ROI.
            mode: One of "Standard", "Time", "Name", "7-segment".
            params: Zone settings dict (blur, thresh, morph, sens, tilt, ...).

        Returns:
            RecognitionResult with text and debug image.
        """
        ...
