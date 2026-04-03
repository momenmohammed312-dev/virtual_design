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
    CRITICAL FIX: Apply LANCZOS4 upscale guard for small images.
    Industry standard: upscale to 2400px minimum for proper analysis and processing.
    """
    # ─── Stability & Resolution Management ───
    # [FIX] Limit upscale target to 1200px (instead of 2400px) for general analysis
    # [FIX] Cap absolute max dimension to 3500px to prevent OOM/Process crashes
    TARGET_MIN_DIM = 1200 
    MAX_SAFE_DIM = 3500
    
    h, w = img.shape[:2]
    min_dim = min(h, w)
    max_dim = max(h, w)
    
    # Pre-check: if original is already gigantic, downscale it immediately
    if max_dim > MAX_SAFE_DIM:
        scale = MAX_SAFE_DIM / max_dim
        new_w, new_h = int(w * scale), int(h * scale)
        print(f"[ImageLoader] Downscaling GIGANTIC image from {w}x{h} to {new_w}x{new_h} for memory safety", flush=True)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return img

    if min_dim < TARGET_MIN_DIM:
        scale = TARGET_MIN_DIM / min_dim
        new_w = int(w * scale)
        new_h = int(h * scale)
        
        # Guard: Ensure upscale doesn't cross safety limit
        if max(new_w, new_h) > MAX_SAFE_DIM:
            scale = MAX_SAFE_DIM / max(new_w, new_h)
            new_w, new_h = int(new_w * scale), int(new_h * scale)

        print(f"[ImageLoader] Upscaling image from {w}x{h} to {new_w}x{new_h} (scale: {scale:.2f}x)", flush=True)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
        print(f"[ImageLoader] Upscaled image shape: {img.shape}", flush=True)
    else:
        print(f"[ImageLoader] Image size {w}x{h} already meets minimum requirement", flush=True)
    
    return img
