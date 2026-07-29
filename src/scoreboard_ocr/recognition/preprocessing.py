"""Common image preprocessing routines shared across all OCR backends.

v2 improvements:
- Auto-threshold using Otsu's method (no manual tuning needed for most scoreboards)
- Multi-pass: tries Otsu first, falls back to adaptive, then to user-specified thresh
- Invert detection: always ensures white pixels = content, black = background
- Morph and sensitivity controls for Name mode manual tuning
"""

import logging
import cv2
import numpy as np

logger = logging.getLogger(__name__)


def apply_deskew(img: np.ndarray, angle_deg: float) -> np.ndarray:
    """
    Apply horizontal shear (deskew) to compensate for camera tilt.
    """
    if angle_deg == 0:
        return img

    try:
        h, w = img.shape[:2]
        tan_a = np.tan(np.deg2rad(angle_deg))
        M = np.float32([[1, -tan_a, 0], [0, 1, 0]])
        pad = int(abs(tan_a * h))
        img_padded = cv2.copyMakeBorder(
            img, 0, 0, pad, pad, cv2.BORDER_CONSTANT, value=[0, 0, 0]
        )
        M[0, 2] = pad
        return cv2.warpAffine(img_padded, M, (w + pad * 2, h))
    except Exception as e:
        logger.warning("Deskew failed (angle=%s): %s", angle_deg, e)
        return img


def binarize_auto(
    gray: np.ndarray,
    blur_val: int = 3,
    user_thresh: int | None = None,
) -> np.ndarray:
    """
    Auto-binarize a grayscale image. Tries multiple strategies:

    1. If user_thresh is provided and not 130 (default), use it directly.
    2. Otsu's threshold — works great for clear bimodal images (dark text on light bg).
    3. Adaptive mean threshold — good for uneven lighting.
    4. Simple mean threshold as last resort.

    Returns binary image where white = foreground content, black = background.
    """
    blur_val = blur_val if blur_val % 2 != 0 else blur_val + 1
    blurred = cv2.medianBlur(gray, blur_val)

    # Always try Otsu first — it's the most reliable for scoreboard digits
    otsu_thresh, otsu_bin = cv2.threshold(
        blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )
    white_ratio = cv2.countNonZero(otsu_bin) / otsu_bin.size

    # Good Otsu: white pixels between 5% and 90%
    if 0.05 < white_ratio < 0.90:
        binary = otsu_bin
        logger.debug("binarize: Otsu thresh=%d, white=%.1f%%", otsu_thresh, 100 * white_ratio)
    else:
        # Fallback: user thresh or adaptive
        if user_thresh is not None and 10 < user_thresh < 245:
            _, binary = cv2.threshold(blurred, user_thresh, 255, cv2.THRESH_BINARY)
            logger.debug("binarize: user_thresh=%d, white=%.1f%%",
                         user_thresh, 100 * cv2.countNonZero(binary) / binary.size)
        else:
            # Adaptive as last resort
            block_size = max(11, (min(gray.shape[0], gray.shape[1]) // 4) | 1)
            binary = cv2.adaptiveThreshold(
                blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, block_size, 4,
            )
            logger.debug("binarize: adaptive block=%d, white=%.1f%%",
                         block_size, 100 * cv2.countNonZero(binary) / binary.size)

    # Ensure white = content (invert if more than 60% is white)
    if cv2.countNonZero(binary) > binary.size * 0.6:
        binary = cv2.bitwise_not(binary)

    return binary


def preprocess_digit_crop(
    img_bgr: np.ndarray,
    *,
    target_height: int = 100,
    blur: int = 3,
    thresh: int = 130,
    tilt: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Preprocessing pipeline for digit/7-segment crops.

    1. Resize to target height.
    2. Deskew.
    3. Convert to grayscale.
    4. Auto-binarize (Otsu → adaptive → mean).
    5. Ensure white = foreground.

    Returns:
        (binary_image, debug_color_image)
    """
    scale = target_height / img_bgr.shape[0]
    new_w = int(img_bgr.shape[1] * scale)
    img_resized = cv2.resize(img_bgr, (new_w, target_height))

    img_deskewed = apply_deskew(img_resized, tilt)

    gray = cv2.cvtColor(img_deskewed, cv2.COLOR_BGR2GRAY)

    binary = binarize_auto(gray, blur_val=blur, user_thresh=thresh)

    debug_img = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)

    return binary, debug_img


def preprocess_name_crop(
    img_bgr: np.ndarray,
    *,
    target_height: int = 100,
    blur: int = 3,
    thresh: int = 130,
    tilt: int = 0,
    morph: int = 1,
    sens: int = 35,
    padding: int = 40,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Preprocessing for text/name zones (Tesseract).

    ALL user-adjustable parameters are used:
      blur  — median blur (noise removal, higher = more blur)
      thresh — binarization threshold (lower = darker, higher = whiter)
      morph  — morphological closing iterations (fattens text, joins broken chars)
      sens   — sensitivity, adjusts threshold proportionally (lower = more contrast)
      tilt   — deskew angle

    Returns:
        (tesseract_ready_image, debug_color_image)
    """
    # Scale up small crops
    h, w = img_bgr.shape[:2]
    scale = max(1.0, target_height / h) if h < target_height else 1.0
    if scale > 1.0:
        img = cv2.resize(img_bgr, (int(w * scale), int(h * scale)))
    else:
        img = img_bgr

    # Deskew
    img = apply_deskew(img, tilt)

    # Grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Apply blur (user-controlled: 1-21, odd values)
    blur_val = blur if blur % 2 != 0 else blur + 1
    blurred = cv2.medianBlur(gray, max(1, blur_val))

    # Apply sensitivity: lower sens = more contrast (multiply difference from mean)
    # sens range: 5-100, map to 0.5-5.0 contrast factor
    contrast = max(0.5, min(5.0, 100.0 / max(5, sens)))
    mean = cv2.mean(blurred)[0]
    contrasted = np.clip((blurred.astype(np.float32) - mean) * contrast + mean, 0, 255).astype(np.uint8)

    # Binarization with user thresh
    user_thresh = max(10, min(245, thresh))
    _, binary = cv2.threshold(contrasted, user_thresh, 255, cv2.THRESH_BINARY)

    # Ensure white = content (invert if needed)
    white_pct = cv2.countNonZero(binary) / binary.size
    if white_pct > 0.6:
        binary = cv2.bitwise_not(binary)
        white_pct = 1.0 - white_pct

    # Morphological closing — fattens text, joins broken characters
    if morph > 0:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (max(1, morph), max(1, morph)))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=min(3, morph))

    # Tesseract: dark text on white background + generous padding
    inverted = cv2.bitwise_not(binary)
    padded = cv2.copyMakeBorder(
        inverted, padding, padding, padding, padding,
        cv2.BORDER_CONSTANT, value=255,
    )

    logger.debug(
        "preprocess_name: blur=%d thresh=%d morph=%d sens=%d tilt=%d → "
        "white=%.1f%% size=%dx%d",
        blur, thresh, morph, sens, tilt,
        100 * white_pct, padded.shape[1], padded.shape[0],
    )

    # Debug image: show binary result (ЧБ) so user can see what Tesseract gets
    debug_binary = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
    return padded, debug_binary


def auto_calibrate_threshold(
    img_bgr: np.ndarray,
) -> dict:
    """
    Analyze a crop and suggest optimal preprocessing parameters.

    Call this once when a new ROI is created, using the current frame.
    Returns a dict with suggested blur, thresh, morph, sens values.
    """
    if img_bgr is None or img_bgr.size == 0:
        return {"blur": 3, "thresh": 130, "morph": 1, "sens": 35, "tilt": 0}

    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # Compute Otsu threshold
    otsu_val, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Estimate noise level (std dev of the image)
    std_dev = float(np.std(gray))

    # Suggested parameters
    blur_suggest = max(1, min(21, int(std_dev / 10))) | 1  # odd, 1-21
    thresh_suggest = max(10, min(245, int(otsu_val)))
    morph_suggest = 1 if std_dev < 30 else 2  # more dilate for noisy images
    sens_suggest = max(10, min(100, int(35 * (std_dev / 25))))

    logger.info(
        "Auto-calibrate: otsu=%d, std=%.1f → blur=%d, thresh=%d, morph=%d, sens=%d",
        otsu_val, std_dev, blur_suggest, thresh_suggest, morph_suggest, sens_suggest,
    )

    return {
        "blur": blur_suggest,
        "thresh": thresh_suggest,
        "morph": morph_suggest,
        "sens": sens_suggest,
        "tilt": 0,
    }
