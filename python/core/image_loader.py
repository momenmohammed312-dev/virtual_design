import os
import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError


def load_image_safely(path: str) -> np.ndarray:
    """Load image robustly from path, not relying on extension.
    Tries OpenCV first, then PIL as a fallback. Returns BGR numpy array.
    Performs sanity checks and normalizes alpha channels if present.
    """
    path_norm = os.path.normpath(path)
    # Basic existence check
    if not os.path.exists(path_norm):
        raise FileNotFoundError(f"Image not found: {path_norm}")

    # Try OpenCV first (supports many formats including PNG/JPEG/TIFF)
    img = cv2.imread(path_norm, cv2.IMREAD_UNCHANGED)
    if img is not None:
        # If image has alpha channel, drop it to keep 3 channels (BGR)
        if img.ndim == 3 and img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        return img

    # Fall back to PIL (RGB) then convert to BGR for consistency with rest of pipeline
    try:
        pil = Image.open(path_norm).convert('RGB')
        arr = np.array(pil)
        img = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        return img
    except UnidentifiedImageError:
        # Most likely an unsupported image format
        raise ValueError("Invalid image format")
    except Exception as e:
        raise ValueError(f"Cannot read image: {e}")
