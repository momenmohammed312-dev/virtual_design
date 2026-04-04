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
    print(f"[ImageLoader] Attempting to load: {path_norm}", flush=True)

    # Basic existence check
    if not os.path.exists(path_norm):
        raise FileNotFoundError(f"Image not found: {path_norm}")

    # Try OpenCV first (supports many formats including PNG/JPEG/TIFF)
    print("[ImageLoader] Trying OpenCV...", flush=True)
    img = cv2.imread(path_norm, cv2.IMREAD_UNCHANGED)
    if img is not None:
        print(f"[ImageLoader] OpenCV loaded successfully: shape={img.shape}, dtype={img.dtype}", flush=True)
        # If image has alpha channel, drop it to keep 3 channels (BGR)
        if img.ndim == 3 and img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        
        # CRITICAL FIX: Add LANCZOS4 upscale guard for small images
        img = _apply_upscale_if_needed(img)
        return img

    # Fall back to PIL (RGB) then convert to BGR for consistency with rest of pipeline
    print("[ImageLoader] OpenCV failed, trying PIL...", flush=True)
    try:
        pil = Image.open(path_norm).convert('RGB')
        arr = np.array(pil)
        img = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        print(f"[ImageLoader] PIL loaded successfully: shape={img.shape}, dtype={img.dtype}", flush=True)
        
        # CRITICAL FIX: Add LANCZOS4 upscale guard for small images
        img = _apply_upscale_if_needed(img)
        return img
    except UnidentifiedImageError:
        # Most likely an unsupported image format
        print(f"[ImageLoader] Both OpenCV and PIL failed - unsupported format", flush=True)
        raise ValueError("Invalid image format")
    except Exception as e:
        print(f"[ImageLoader] PIL failed with error: {e}", flush=True)
        raise ValueError(f"Cannot read image: {e}")


def _apply_upscale_if_needed(img: np.ndarray) -> np.ndarray:
    """
    CRITICAL FIX: Apply LANCZOS4 upscale guard for small images with Hard Memory Gates.
    - ABSOLUTE_MAX_PX: 3000 (Hard limit on dimensions)
    - MEMORY_SAFE_MP: 8.0 MP (Hard limit on total pixels)
    - TARGET_MIN_DIM: 1200 (Minimum dimension target for analysis)
    """
    TARGET_MIN_DIM  = 1200
    ABSOLUTE_MAX_PX = 3000
    MEMORY_SAFE_MP  = 8.0

    h, w = img.shape[:2]

    # ① ABSOLUTE CAP — Hard Gate 1
    if max(h, w) > ABSOLUTE_MAX_PX:
        scale = ABSOLUTE_MAX_PX / max(h, w)
        new_w, new_h = int(w * scale), int(h * scale)
        print(f"[ImageLoader] HARD CAP: {w}x{h} -> {new_w}x{new_h}", flush=True)
        return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

    # ② MEGAPIXEL CAP — Hard Gate 2
    current_mp = (h * w) / 1_000_000
    if current_mp > MEMORY_SAFE_MP:
        scale = (MEMORY_SAFE_MP / current_mp) ** 0.5
        new_w, new_h = int(w * scale), int(h * scale)
        print(f"[ImageLoader] MP CAP: {current_mp:.1f}MP -> {new_w}x{new_h}", flush=True)
        return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

    # ③ Small-Image Upscale (LANCZOS4)
    min_dim = min(h, w)
    if min_dim < TARGET_MIN_DIM:
        scale = TARGET_MIN_DIM / min_dim
        new_w = int(w * scale)
        new_h = int(h * scale)
        
        # Guard: Upscale must not exceed limits
        if max(new_w, new_h) > ABSOLUTE_MAX_PX:
            scale = ABSOLUTE_MAX_PX / max(new_w, new_h)
            new_w, new_h = int(w * scale), int(h * scale)

        # Final safety check for Megapixel budget
        if (new_w * new_h) / 1_000_000 > MEMORY_SAFE_MP:
            scale = (MEMORY_SAFE_MP * 1_000_000 / (h * w)) ** 0.5
            new_w, new_h = int(w * scale), int(h * scale)

        print(f"[ImageLoader] Upscaling {w}x{h} -> {new_w}x{new_h} (scale: {scale:.2f}x)", flush=True)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
    else:
        print(f"[ImageLoader] Image {w}x{h} is within safe bounds", flush=True)
    
    return img

