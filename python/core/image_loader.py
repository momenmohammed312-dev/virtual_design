import os
import cv2
import numpy as np
from PIL import Image


def load_image_safely(path: str) -> np.ndarray:
    """Load image robustly from path, not relying on extension.
    Tries OpenCV first, then PIL as a fallback. Returns BGR numpy array.
    """
    path_norm = os.path.normpath(path)
    img = cv2.imread(path_norm)
    if img is not None:
        return img
    pil = Image.open(path_norm).convert('RGB')
    arr = np.array(pil)
    img = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    return img
