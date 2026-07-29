"""Template-based segment recognizer — port of the original prototyp OCR logic.

Supports:
- Template matching (digit images stored as .png files)
- 7-segment heuristic recognition
- Tesseract fallback (limited to 3 calls per crop, as in original)
- Template learning (save_template mode)
"""

import logging
import os
import cv2
import numpy as np
from pathlib import Path

from .base import Recognizer, RecognitionResult
from .preprocessing import preprocess_digit_crop, preprocess_name_crop

logger = logging.getLogger(__name__)


class TemplateSegmentRecognizer(Recognizer):
    """
    Port of the original OCR logic: template matching + 7-segment heuristic
    + limited Tesseract fallback.

    This is the baseline for comparison; TesseractRecognizer is the
    alternative backend for pure-Tesseract recognition.
    """

    def __init__(self, templates_dir: str | Path | None = None):
        """
        Args:
            templates_dir: Path to the template images folder (0.png .. 9.png).
                           If None, defaults to `templates/` next to the source.
        """
        if templates_dir is None:
            templates_dir = Path(__file__).resolve().parent.parent.parent.parent / "templates"
        self.tpl_folder = Path(templates_dir)
        self.templates: dict[str, np.ndarray] = {}
        self._load_templates()

    def _load_templates(self) -> None:
        """Load digit template images (0.png .. 9.png) from the templates folder."""
        self.templates.clear()
        try:
            self.tpl_folder.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.warning("Cannot create templates dir %s: %s", self.tpl_folder, e)
            return
        for i in range(10):
            fpath = self.tpl_folder / f"{i}.png"
            if fpath.exists():
                img = cv2.imread(str(fpath), cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    self.templates[str(i)] = img
        logger.info("Loaded %d templates from %s", len(self.templates), self.tpl_folder)

    def load_templates(self) -> None:
        """Public method to reload templates (called when new ones are saved)."""
        self._load_templates()

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
                return self._recognize_digits(crop, mode, params)
        except Exception as e:
            logger.exception("TemplateSegmentRecognizer failed (mode=%s): %s", mode, e)
            return RecognitionResult(
                text="",
                debug_image=np.zeros((1, 1, 3), dtype=np.uint8),
            )

    # ------------------------------------------------------------------
    # Template matching
    # ------------------------------------------------------------------

    def _match_template(self, digit_img: np.ndarray) -> str | None:
        """Match a digit image against stored templates. Returns digit char or None."""
        if not self.templates:
            return None
        best_score = 0.82
        best_digit: str | None = None
        h, w = digit_img.shape[:2]
        for d, tpl in self.templates.items():
            try:
                resized = cv2.resize(tpl, (w, h))
                res = cv2.matchTemplate(digit_img, resized, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(res)
                if max_val > best_score:
                    best_score = max_val
                    best_digit = d
            except Exception as e:
                logger.warning("Template match failed for digit %s: %s", d, e)
                continue
        return best_digit

    # ------------------------------------------------------------------
    # 7-segment heuristic
    # ------------------------------------------------------------------

    @staticmethod
    def _recognize_7seg(
        img: np.ndarray,
        debug_roi: np.ndarray,
        sens: int = 35,
    ) -> str:
        """
        Recognize a digit from a binary 7-segment display image.

        Divides the image into 7 segment regions, checks which are "on"
        (above sensitivity threshold), and maps the pattern to a digit.

        Args:
            img: Binary image (single digit, white segments on black background).
            debug_roi: Color debug image to draw segment overlays on.
            sens: Sensitivity divisor — higher = more sensitive.
        """
        try:
            h, w = img.shape
            # Narrow images are likely "1"
            if w / h < 0.42:
                return "1"

            min_px = (h * w) // sens

            # Segment regions (idx, y_start, y_end, x_start, x_end)
            segments = [
                (0, 0.0, 0.2, 0.2, 0.8),    # top
                (1, 0.1, 0.45, 0.7, 1.0),   # upper-right
                (2, 0.55, 0.9, 0.7, 1.0),   # lower-right
                (3, 0.8, 1.0, 0.2, 0.8),    # bottom
                (4, 0.55, 0.9, 0.0, 0.3),   # lower-left
                (5, 0.1, 0.45, 0.0, 0.3),   # upper-left
                (6, 0.4, 0.6, 0.2, 0.8),    # middle
            ]

            on = [0] * 7
            for idx, ys, ye, xs, xe in segments:
                y1, y2 = int(ys * h), int(ye * h)
                x1, x2 = int(xs * w), int(xe * w)
                if cv2.countNonZero(img[y1:y2, x1:x2]) > min_px:
                    on[idx] = 1
                    cv2.rectangle(debug_roi, (x1, y1), (x2, y2), (0, 255, 255), -1)
                else:
                    cv2.rectangle(debug_roi, (x1, y1), (x2, y2), (255, 0, 0), 1)

            patterns = {
                (1, 1, 1, 1, 1, 1, 0): "0",
                (0, 1, 1, 0, 0, 0, 0): "1",
                (1, 1, 0, 1, 1, 0, 1): "2",
                (1, 1, 1, 1, 0, 0, 1): "3",
                (0, 1, 1, 0, 0, 1, 1): "4",
                (1, 0, 1, 1, 0, 1, 1): "5",
                (1, 0, 1, 1, 1, 1, 1): "6",
                (1, 1, 1, 0, 0, 0, 0): "7",
                (1, 1, 1, 1, 1, 1, 1): "8",
                (1, 1, 1, 1, 0, 1, 1): "9",
            }
            return patterns.get(tuple(on), "")
        except Exception as e:
            logger.warning("7-segment recognition failed: %s", e)
            return ""

    # ------------------------------------------------------------------
    # Full digit recognition pipeline
    # ------------------------------------------------------------------

    def _recognize_digits(
        self,
        crop: np.ndarray,
        mode: str,
        params: dict,
    ) -> RecognitionResult:
        binary, debug = preprocess_digit_crop(
            crop,
            blur=params.get("blur", 3),
            thresh=params.get("thresh", 130),
            tilt=params.get("tilt", 0),
        )

        # --- Template learning mode ---
        if params.get("save_template"):
            digit_char = params["save_template"]
            try:
                contours, _ = cv2.findContours(
                    binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )
                if contours:
                    largest = max(contours, key=cv2.contourArea)
                    x, y, w, h = cv2.boundingRect(largest)
                    tpl_img = binary[y:y + h, x:x + w]
                    out_path = self.tpl_folder / f"{digit_char}.png"
                    cv2.imwrite(str(out_path), tpl_img)
                    logger.info("Saved template: %s", out_path)
                    self._load_templates()
            except Exception as e:
                logger.exception("Failed to save template for digit %s: %s", digit_char, e)

        # --- Contour-based digit extraction ---
        debug_color = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
        contours, _ = cv2.findContours(
            binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        # Sort left-to-right
        contours = sorted(contours, key=lambda c: cv2.boundingRect(c)[0])

        digits: list[str] = []
        tess_calls = 0

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if h < binary.shape[0] * 0.25 or w < 2:
                continue

            roi = binary[y:y + h, x:x + w]
            digit = None

            # Step 1: Template match (skip for 7-segment mode)
            if mode != "7-segment":
                digit = self._match_template(roi)

            # Step 2: Heuristic fallbacks
            if digit is None:
                pw_ratio = w / h
                if pw_ratio < 0.4:
                    # Narrow contour → likely "1"
                    digit = "1"
                    cv2.rectangle(debug_color, (x, y), (x + w, y + h), (0, 255, 255), -1)
                elif mode == "7-segment":
                    digit = self._recognize_7seg(
                        roi,
                        debug_color[y:y + h, x:x + w],
                        params.get("sens", 35),
                    )
                elif tess_calls < 3:
                    # Step 3: Tesseract fallback (max 3 calls per zone)
                    tess_calls += 1
                    digit = self._tesseract_digit(roi)
                else:
                    logger.debug("Tesseract call limit reached for this crop")

            if digit:
                digits.append(digit)
                cv2.rectangle(debug_color, (x, y), (x + w, y + h), (0, 255, 0), 1)

        # --- Format output ---
        raw = "".join(digits)
        if mode == "Time":
            result = self._format_time(raw)
        else:
            result = raw

        return RecognitionResult(text=result, debug_image=debug_color)

    # ------------------------------------------------------------------
    # Text recognition (Name mode)
    # ------------------------------------------------------------------

    def _recognize_name(self, crop: np.ndarray, params: dict) -> RecognitionResult:
        """Recognize text using Tesseract (rus+eng, PSM 7)."""
        import pytesseract
        padded, debug = preprocess_name_crop(
            crop,
            blur=params.get("blur", 3),
            thresh=params.get("thresh", 130),
            tilt=params.get("tilt", 0),
        )
        try:
            text = pytesseract.image_to_string(
                padded,
                lang="rus+eng",
                config="--psm 7",
            ).strip()
        except Exception:
            try:
                text = pytesseract.image_to_string(
                    padded,
                    config="--psm 7",
                ).strip()
            except Exception as e:
                logger.warning("Name recognition failed: %s", e)
                text = ""
        return RecognitionResult(text=text, debug_image=debug)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _tesseract_digit(roi: np.ndarray) -> str | None:
        """Run Tesseract on a single digit contour (PSM 10, digits only)."""
        import pytesseract
        try:
            padded = cv2.copyMakeBorder(
                cv2.bitwise_not(roi), 30, 30, 30, 30,
                cv2.BORDER_CONSTANT, value=255,
            )
            text = pytesseract.image_to_string(
                padded,
                config="--psm 10 -c tessedit_char_whitelist=0123456789",
            ).strip()
            return text[0] if text and text[0].isdigit() else None
        except Exception as e:
            logger.debug("Tesseract digit fallback failed: %s", e)
            return None

    @staticmethod
    def _format_time(raw: str) -> str:
        """Format raw digits string as HH:MM (or similar)."""
        if len(raw) >= 2:
            if len(raw) == 4:
                return f"{raw[:2]}:{raw[2:]}"
            elif len(raw) == 3:
                return f"{raw[0]}:{raw[1:]}"
            else:
                return f"0:{raw}"
        return raw
