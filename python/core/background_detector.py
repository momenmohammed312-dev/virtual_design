"""
Robust Background Detection for Silk-Screen Printing Pipeline.

Provides multiple background detection strategies:
- auto: Detect background from border sampling
- remove_white: Force white background removal
- remove_black: Force black background removal  
- keep_all: No background removal (keep everything)
"""

import cv2
import numpy as np
from typing import Tuple, Literal
import logging

logger = logging.getLogger(__name__)

# Background detection modes
BackgroundMode = Literal["auto", "remove_white", "remove_black", "keep_all"]


class BackgroundDetector:
    """
    Detects and masks background pixels for clean color separation.
    """
    
    def __init__(self, mode: BackgroundMode = "auto", tolerance: int = 20):
        """
        Args:
            mode: Detection strategy
            tolerance: Color distance tolerance for background matching
        """
        self.mode = mode
        self.tolerance = tolerance
        self.detected_bg_color = None
        self.bg_mask = None
        self.fg_mask = None
        
    def detect(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray, dict]:
        """
        Detect background and return masks.
        
        Args:
            image: BGR image
            
        Returns:
            (bg_mask, fg_mask, stats)
            - bg_mask: Boolean mask of background pixels (True = background)
            - fg_mask: Boolean mask of foreground pixels (True = foreground/design)
            - stats: Detection statistics dict
        """
        logger.info(f"[BackgroundDetector] Starting detection with mode='{self.mode}'")
        
        if self.mode == "keep_all":
            return self._keep_all(image)
        elif self.mode == "remove_white":
            return self._remove_white(image)
        elif self.mode == "remove_black":
            return self._remove_black(image)
        else:  # auto
            return self._detect_auto(image)
    
    def _keep_all(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray, dict]:
        """Keep all pixels (no background removal)."""
        h, w = image.shape[:2]
        bg_mask = np.zeros((h, w), dtype=bool)
        fg_mask = np.ones((h, w), dtype=bool)
        
        stats = {
            "mode": "keep_all",
            "bg_pixels": 0,
            "fg_pixels": h * w,
            "bg_coverage": 0.0,
            "fg_coverage": 100.0,
            "detected_color": None
        }
        
        logger.info(f"[BackgroundDetector] Mode=keep_all: All {h*w} pixels kept as foreground")
        return bg_mask, fg_mask, stats
    
    def _remove_white(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray, dict]:
        """Remove white background (RGB 255,255,255)."""
        # White in BGR is (255, 255, 255)
        white_bgr = np.array([255, 255, 255])
        return self._remove_color(image, white_bgr, "white")
    
    def _remove_black(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray, dict]:
        """Remove black background (RGB 0,0,0)."""
        # Black in BGR is (0, 0, 0)
        black_bgr = np.array([0, 0, 0])
        return self._remove_color(image, black_bgr, "black")
    
    def _remove_color(self, image: np.ndarray, target_color: np.ndarray,
                      color_name: str) -> Tuple[np.ndarray, np.ndarray, dict]:
        """Remove specific color as background."""
        h, w = image.shape[:2]

        # Calculate color distance using TRUE EUCLIDEAN distance (FIX GROUP 1.1)
        diff = image.astype(np.float32) - target_color.astype(np.float32)
        distance = np.sqrt(np.sum(diff ** 2, axis=2))  # True Euclidean distance

        # Background mask: pixels close to target color
        # FIX: Removed *3 factor - tolerance now directly controls Euclidean radius
        bg_mask = distance <= self.tolerance
        fg_mask = ~bg_mask
        
        bg_pixels = np.sum(bg_mask)
        fg_pixels = np.sum(fg_mask)
        total = h * w
        
        stats = {
            "mode": f"remove_{color_name}",
            "bg_pixels": int(bg_pixels),
            "fg_pixels": int(fg_pixels),
            "bg_coverage": (bg_pixels / total) * 100,
            "fg_coverage": (fg_pixels / total) * 100,
            "detected_color": tuple(target_color.tolist()),
            "tolerance": self.tolerance
        }
        
        logger.info(f"[BackgroundDetector] Mode=remove_{color_name}: "
                   f"BG={bg_pixels} ({stats['bg_coverage']:.1f}%), "
                   f"FG={fg_pixels} ({stats['fg_coverage']:.1f}%)")
        
        self.detected_bg_color = target_color
        return bg_mask, fg_mask, stats
    
    def _detect_auto(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray, dict]:
        """
        Auto-detect background using border sampling.
        Samples corners and edges to estimate background color.
        """
        h, w = image.shape[:2]
        
        # Sample border pixels (corners and edges)
        border_samples = self._sample_borders(image)
        
        # Find dominant border color using k-means
        if len(border_samples) > 0:
            border_samples = np.float32(border_samples)
            
            # Use small k to find dominant color
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
            _, labels, centers = cv2.kmeans(border_samples, 2, None, criteria, 3, 
                                             cv2.KMEANS_PP_CENTERS)
            
            # Find largest cluster
            counts = np.bincount(labels.flatten())
            dominant_idx = np.argmax(counts)
            dominant_color = centers[dominant_idx].astype(np.uint8)
            
            # Calculate coverage of this color in borders
            border_coverage = counts[dominant_idx] / len(border_samples)
            
            logger.info(f"[BackgroundDetector] Auto-detected background: "
                       f"BGR={dominant_color}, border_coverage={border_coverage:.1%}")
        else:
            # Fallback: assume white
            dominant_color = np.array([255, 255, 255])
            border_coverage = 0
            logger.warning("[BackgroundDetector] No border samples, defaulting to white")
        
        # Build background mask
        # FIX GROUP 1.1: Use true Euclidean distance instead of L1 sum
        diff = image.astype(np.float32) - dominant_color.astype(np.float32)
        distance = np.sqrt(np.sum(diff ** 2, axis=2))

        # Adaptive tolerance based on image characteristics
        adaptive_tolerance = self._calculate_adaptive_tolerance(image, dominant_color)

        bg_mask = distance <= adaptive_tolerance
        fg_mask = ~bg_mask
        
        # Refine using morphological operations
        bg_mask = self._refine_mask(bg_mask)
        fg_mask = ~bg_mask
        
        bg_pixels = np.sum(bg_mask)
        fg_pixels = np.sum(fg_mask)
        total = h * w
        
        stats = {
            "mode": "auto",
            "bg_pixels": int(bg_pixels),
            "fg_pixels": int(fg_pixels),
            "bg_coverage": (bg_pixels / total) * 100,
            "fg_coverage": (fg_pixels / total) * 100,
            "detected_color": tuple(dominant_color.tolist()),
            "border_coverage": border_coverage * 100,
            "adaptive_tolerance": adaptive_tolerance,
            "border_samples": len(border_samples)
        }
        
        logger.info(f"[BackgroundDetector] Mode=auto: "
                   f"BG={bg_pixels} ({stats['bg_coverage']:.1f}%), "
                   f"FG={fg_pixels} ({stats['fg_coverage']:.1f}%), "
                   f"tolerance={adaptive_tolerance:.1f}")
        
        self.detected_bg_color = dominant_color
        return bg_mask, fg_mask, stats
    
    def _sample_borders(self, image: np.ndarray, border_width: int = 5) -> np.ndarray:
        """Sample pixels from image borders (corners and edges)."""
        h, w = image.shape[:2]
        samples = []
        
        # Sample corners (more weight to corners as they often show background)
        corner_size = min(h, w) // 10  # 10% of smaller dimension
        
        corners = [
            image[:corner_size, :corner_size],  # Top-left
            image[:corner_size, -corner_size:],  # Top-right
            image[-corner_size:, :corner_size],  # Bottom-left
            image[-corner_size:, -corner_size:]  # Bottom-right
        ]
        
        for corner in corners:
            samples.extend(corner.reshape(-1, 3))
        
        # Sample edges
        edge_strip = border_width
        top_edge = image[:edge_strip, :].reshape(-1, 3)
        bottom_edge = image[-edge_strip:, :].reshape(-1, 3)
        left_edge = image[:, :edge_strip].reshape(-1, 3)
        right_edge = image[:, -edge_strip:].reshape(-1, 3)
        
        samples.extend(top_edge)
        samples.extend(bottom_edge)
        samples.extend(left_edge)
        samples.extend(right_edge)
        
        return np.array(samples, dtype=np.uint8)
    
    def _calculate_adaptive_tolerance(self, image: np.ndarray,
                                       bg_color: np.ndarray) -> float:
        """Calculate adaptive tolerance based on image characteristics."""
        # FIX GROUP 1.2: Use tolerance directly (no *3 factor for Euclidean distance)
        base_tolerance = self.tolerance

        # Adjust based on image variance
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        variance = np.var(gray)

        # FIX: Reduced multipliers - max is now 1.1 instead of 1.5
        # High variance = complex image, need slightly higher tolerance
        if variance > 5000:
            multiplier = 1.1  # Reduced from 1.5
        elif variance > 2000:
            multiplier = 1.05  # Reduced from 1.2
        else:
            multiplier = 1.0

        result = base_tolerance * multiplier
        logger.info(f"[BackgroundDetector] Adaptive tolerance: {result:.1f} (base={self.tolerance}, variance={variance:.0f})")
        return result
    
    def _refine_mask(self, mask: np.ndarray) -> np.ndarray:
        """Refine background mask using morphological operations."""
        # Close small holes in background
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_CLOSE, kernel)
        
        # Remove small isolated background spots (likely noise)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        return mask.astype(bool)


def detect_background(image: np.ndarray, 
                       mode: BackgroundMode = "auto",
                       tolerance: int = 30) -> Tuple[np.ndarray, np.ndarray, dict]:
    """
    Convenience function for background detection.
    
    Args:
        image: BGR image
        mode: Detection mode ("auto", "remove_white", "remove_black", "keep_all")
        tolerance: Color distance tolerance
        
    Returns:
        (bg_mask, fg_mask, stats)
    """
    detector = BackgroundDetector(mode=mode, tolerance=tolerance)
    return detector.detect(image)
