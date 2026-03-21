"""Image preprocessing for bill photos.

Provides a gentle enhancement path that preserves the original colour
image structure (important for PaddleOCR's internal preprocessing)
while still improving readability of noisy mobile-camera captures.
"""

from __future__ import annotations

from typing import List

import cv2
import numpy as np


def preprocess_image(image_bytes: bytes) -> np.ndarray:
    """Return a lightly-enhanced **colour** image for primary OCR pass.

    The previous implementation converted to grayscale and applied
    aggressive histogram equalisation which destroyed colour-coded
    document structure.  PaddleOCR works best on the original colour
    image with only light denoising.
    """
    arr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Unsupported or corrupted image")

    # Light bilateral denoise — preserves edges and text.
    denoised = cv2.bilateralFilter(image, d=9, sigmaColor=50, sigmaSpace=50)
    return denoised


def preprocess_image_enhanced(image_bytes: bytes) -> np.ndarray:
    """Return a more aggressively enhanced image for a fallback OCR pass.

    Uses adaptive thresholding on a grayscale conversion to maximise
    text contrast.  Useful when the primary colour pass misses faint
    text.
    """
    arr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Unsupported or corrupted image")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # CLAHE gives better local contrast than plain equalizeHist.
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    # Light sharpen.
    blurred = cv2.GaussianBlur(enhanced, (0, 0), 1.0)
    sharpened = cv2.addWeighted(enhanced, 1.5, blurred, -0.5, 0)
    # Convert back to 3-channel so PaddleOCR accepts it.
    return cv2.cvtColor(sharpened, cv2.COLOR_GRAY2BGR)


def get_preprocessed_images(image_bytes: bytes) -> List[np.ndarray]:
    """Return a list of preprocessed image variants for multi-pass OCR."""
    images = [preprocess_image(image_bytes)]
    try:
        images.append(preprocess_image_enhanced(image_bytes))
    except ValueError:
        pass  # If the enhanced path fails, just use the primary.
    return images
