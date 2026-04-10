import os
import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError

# Import centralized geometry synchronizer
try:
    from core.geometry_sync import sync_initialize, sync_upscale
    _HAS_SYNC = True
except ImportError:
    _HAS_SYNC = False


def load_image_safely(path: str) -> tuple:
    """Load image robustly from path, not relying on extension.
    Tries OpenCV first, then PIL as a fallback. Returns BGR numpy array.
    Performs sanity checks and normalizes alpha channels if present.
    
    🔥 FIXED: Now preserves alpha channel and returns it as a separate mask.
    🔥 ARCHITECTURE FIX: Uses centralized GeometrySynchronizer to prevent dimension drift.
    
    Returns:
        tuple: (img, alpha_mask) where:
            - img: BGR image (3 channels)
            - alpha_mask: numpy array (2D) with True=opaque, False=transparent
              Returns None if image has no alpha channel.
    """
    path_norm = os.path.normpath(path)
    print(f"[ImageLoader] Attempting to load: {path_norm}", flush=True)

    # Basic existence check
    if not os.path.exists(path_norm):
        raise FileNotFoundError(f"Image not found: {path_norm}")

    # Try OpenCV first (supports many formats including PNG/JPEG/TIFF)
    print("[ImageLoader] Trying OpenCV...", flush=True)
    img = cv2.imread(path_norm, cv2.IMREAD_UNCHANGED)
    alpha_mask = None
    has_alpha = False
    
    if img is not None:
        print(f"[ImageLoader] OpenCV loaded successfully: shape={img.shape}, dtype={img.dtype}", flush=True)
        # If image has alpha channel, extract it and convert to BGR
        if img.ndim == 3 and img.shape[2] == 4:
            has_alpha = True
            # Extract alpha channel (BGRA format: alpha is last channel)
            alpha_channel = img[:, :, 3]
            # Create mask: alpha > 0 means visible/foreground
            alpha_mask = alpha_channel > 0
            # Convert to BGR (drop alpha)
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            alpha_ratio = np.sum(alpha_mask) / alpha_mask.size
            print(f"[ImageLoader] ✓ Alpha channel preserved: {alpha_ratio:.1%} visible, {1-alpha_ratio:.1%} transparent")
        else:
            print(f"[ImageLoader] No alpha channel (shape={img.shape}), creating full-opaque mask")
            # Create full-opaque mask for non-alpha images
            alpha_mask = np.ones((img.shape[0], img.shape[1]), dtype=bool)
        
        # ARCHITECTURE FIX: Use centralized GeometrySynchronizer
        # This ensures alpha mask stays synchronized through ALL resize operations
        if _HAS_SYNC:
            sync_initialize(img, alpha_mask, source="image_loader_opencv")
            img = sync_upscale(img, target_min_dim=1000, absolute_max_px=2500, memory_safe_mp=6.0)
            # Get the synchronized alpha mask (may have been resized)
            from core.geometry_sync import get_synchronizer
            sync = get_synchronizer()
            if sync._state and sync._state.alpha_mask is not None:
                alpha_mask = sync._state.alpha_mask
        else:
            # Fallback to legacy behavior if synchronizer not available
            img = _apply_upscale_if_needed(img)
            if has_alpha and img.shape[:2] != alpha_mask.shape:
                alpha_mask = cv2.resize(alpha_mask.astype(np.uint8), 
                                        (img.shape[1], img.shape[0]), 
                                        interpolation=cv2.INTER_NEAREST).astype(bool)
        return img, alpha_mask

    # Fall back to PIL (RGB) then convert to BGR for consistency with rest of pipeline
    print("[ImageLoader] OpenCV failed, trying PIL...", flush=True)
    try:
        pil = Image.open(path_norm)
        # Check if image has alpha
        if pil.mode in ('RGBA', 'LA', 'P'):
            has_alpha = True
            if pil.mode == 'P':
                pil = pil.convert('RGBA')
            elif pil.mode == 'LA':
                pil = pil.convert('RGBA')
            # Extract alpha
            arr = np.array(pil)
            alpha_channel = arr[:, :, 3] if arr.ndim == 3 else arr[:, :, 1]
            alpha_mask = alpha_channel > 0
            # Convert to RGB then BGR
            rgb_arr = arr[:, :, :3] if arr.ndim == 3 else np.stack([arr[:, :, 0]]*3, axis=-1)
            img = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2BGR)
            alpha_ratio = np.sum(alpha_mask) / alpha_mask.size
            print(f"[ImageLoader] PIL loaded with alpha: {alpha_ratio:.1%} visible pixels")
        else:
            pil = pil.convert('RGB')
            arr = np.array(pil)
            img = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            alpha_mask = np.ones((img.shape[0], img.shape[1]), dtype=bool)
            print(f"[ImageLoader] PIL loaded successfully: shape={img.shape}, dtype={img.dtype}", flush=True)
        
        # ARCHITECTURE FIX: Use centralized GeometrySynchronizer
        if _HAS_SYNC:
            sync_initialize(img, alpha_mask, source="image_loader_pil")
            img = sync_upscale(img, target_min_dim=1000, absolute_max_px=2500, memory_safe_mp=6.0)
            from core.geometry_sync import get_synchronizer
            sync = get_synchronizer()
            if sync._state and sync._state.alpha_mask is not None:
                alpha_mask = sync._state.alpha_mask
        else:
            img = _apply_upscale_if_needed(img)
        return img, alpha_mask
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
    Also applies to alpha mask if provided separately.
    """
    TARGET_MIN_DIM  = 1000
    ABSOLUTE_MAX_PX = 2500
    MEMORY_SAFE_MP  = 6.0

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

