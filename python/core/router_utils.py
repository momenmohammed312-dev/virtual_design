import cv2
import numpy as np
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

def preprocess_text_logo(image: np.ndarray) -> np.ndarray:
    """Enhanced sharpening for pure logos/text: Bilateral + Sharpening."""
    bilat = cv2.bilateralFilter(image, 5, 50, 50)
    kernel_sharpen = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    sharpened = cv2.filter2D(bilat, -1, kernel_sharpen)
    return sharpened

def preprocess_artwork(image: np.ndarray) -> np.ndarray:
    """Balanced preprocessing for illustrations: Bilateral + Contrast."""
    bilat = cv2.bilateralFilter(image, 9, 75, 75)
    return cv2.convertScaleAbs(bilat, alpha=1.3, beta=0)

def preprocess_photo(image: np.ndarray) -> np.ndarray:
    """Shadow/Texture-preserving preprocessing for photographs."""
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    bilat = cv2.bilateralFilter(gray, 15, 75, 75)
    blurred = cv2.GaussianBlur(bilat, (5, 5), 1.0)
    unsharp = cv2.addWeighted(bilat, 1.5, blurred, -0.5, 0)
    return unsharp

def _make_single_color_separation(image: np.ndarray, white_threshold: int = 240) -> dict:
    """Bypasses K-means for TEXT_LOGO / monochrome images."""
    h, w = image.shape[:2]
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    label_map = np.full((h, w), -1, dtype=np.int32)
    label_map[gray < white_threshold] = 0
    
    ink_pixels = int(np.sum(label_map == 0))
    coverage = (ink_pixels / label_map.size) * 100 if label_map.size > 0 else 0
    
    if ink_pixels > 0:
        if len(image.shape) == 3:
            center_bgr = np.mean(image[label_map == 0], axis=0).astype(np.float32)
        else:
            center_bgr = np.array([0, 0, 0], dtype=np.float32)
    else:
        center_bgr = np.array([0, 0, 0], dtype=np.float32)
    
    return {
        'label_map': label_map,
        'centers': np.array([center_bgr]),
        'num_colors': 1,
        'colors': [(0, 0, 0)],
        'color_names': ["Black"],
        'compactness': 0.0,
        'color_info': [{'index': 0, 'pixel_count': ink_pixels, 'percentage': coverage}]
    }

def apply_halftone_pipeline(masks: List[np.ndarray], args, halftone_gen=None) -> List[np.ndarray]:
    """
    Decoupled halftone pipeline.
    If halftone_gen is None, it will create one.
    """
    if halftone_gen is None:
        try:
            from core.halftone_generator import HalftoneGenerator
            halftone_gen = HalftoneGenerator()
        except ImportError:
            logger.warning("HalftoneGenerator not available in utils")
            return masks

    # Auto-calc LPI if needed
    effective_lpi = args.lpi
    if effective_lpi == 65: # default
        effective_lpi = min(120, max(55, args.dpi // 5))

    cmyk_angles = [15.0, 75.0, 0.0, 45.0]
    result = []
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    for i, mask in enumerate(masks):
        total_pixels = mask.size
        # design=0 (ink), paper=255
        design_pixels = np.sum(mask < 128)
        coverage_percentage = (design_pixels / total_pixels) * 100
        
        if coverage_percentage > 95.0:
            result.append(mask)
            continue
            
        enhanced = mask.astype(np.uint8) if mask.dtype != np.uint8 else mask.copy()
        if 5.0 <= coverage_percentage <= 85.0:
            enhanced = clahe.apply(enhanced)
            
        angle = cmyk_angles[i] if i < len(cmyk_angles) else getattr(args, 'angle', 45.0)
        dot_shape = getattr(args, 'dot_shape', 'round')
        
        ht = halftone_gen.generate(enhanced, lpi=effective_lpi, angle=angle, 
                                   dot_shape=dot_shape, dpi=args.dpi, gamma=1.6)
        result.append(ht)
        
    return result
