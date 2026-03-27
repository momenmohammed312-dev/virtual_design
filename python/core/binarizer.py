"""
Binarizer - Robust thresholding with near-binary path and collapse detection
FIXED: Prevents Adaptive Gaussian from collapsing near-binary images
"""

import cv2
import numpy as np
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

class Binarizer:
    """
    Robust image binarization with multiple methods and intelligent selection.
    FIXED: Near-binary fast path prevents collapse on bimodal images.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.Binarizer")
    
    def smart_threshold(self, mask: np.ndarray) -> np.ndarray:
        """
        FIXED: Adaptive threshold selection with near-binary fast path.
        
        NEW Decision Logic:
        1. Already binary? → passthrough
        2. Near-binary (mid_ratio < 10%)? → Otsu fast path (Adaptive disabled)
        3. Standard path: try all methods with scoring
        4. Collapse detection: retry with Otsu if >97% white/black
        
        Args:
            mask: Input mask (any format)
            
        Returns:
            Binary mask with design=255 (bright ink), background=0 (dark)
        """
        # Convert to grayscale
        if len(mask.shape) == 3:
            gray = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
        else:
            gray = mask.copy()
        
        # Ensure uint8
        if gray.dtype != np.uint8:
            gray = gray.astype(np.uint8)
        
        # ── 1. Already Binary Check ──────────────────────────────────────
        unique_vals = np.unique(gray)
        if len(unique_vals) <= 2 and all(v in [0, 255] for v in unique_vals):
            self.logger.info("[SmartThreshold] Already binary - passthrough")
            return gray
        
        # ── 2. Near-Binary Fast Path (FIXED) ───────────────────────────
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
        total_pixels = gray.size
        mid_ratio = np.sum(hist[85:170]) / total_pixels
        
        if mid_ratio < 0.10:
            # Near-binary image - use Otsu directly, NEVER use Adaptive
            self.logger.info(f"[SmartThreshold] Near-binary (mid={mid_ratio:.1%}) - Otsu fast path")
            _, result = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Check for collapse
            if self._is_collapsed(result):
                self.logger.warning("[SmartThreshold] Otsu collapsed - trying Triangle")
                _, result = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_TRIANGLE)
                
                if self._is_collapsed(result):
                    self.logger.error("[SmartThreshold] Triangle also collapsed - using raw")
                    return gray
            
            return result
        
        # ── 3. Standard Path - Try Multiple Methods ───────────────────────
        methods = []
        
        # Method 1: Otsu
        _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        methods.append(("Otsu", otsu))
        
        # Method 2: Triangle
        _, triangle = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_TRIANGLE)
        methods.append(("Triangle", triangle))
        
        # Method 3: Adaptive Mean
        adaptive_mean = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 21, 3
        )
        methods.append(("AdaptiveMean", adaptive_mean))
        
        # Method 4: Adaptive Gaussian (NOW SAFE - won't run on near-binary)
        adaptive_gauss = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 5
        )
        methods.append(("AdaptiveGaussian", adaptive_gauss))
        
        # ── 4. Evaluate and Select Best Method ─────────────────────────
        best_method = None
        best_score = -1
        best_result = None
        
        for method_name, result in methods:
            # Check for collapse
            if self._is_collapsed(result):
                self.logger.warning(f"[SmartThreshold] {method_name} collapsed - skipping")
                continue
            
            # Calculate metrics for scoring
            metrics = self._calculate_metrics(result)
            
            # Scoring function (prefers ~20% ink coverage)
            ink_penalty = abs(metrics['ink_ratio'] - 0.20) * 2
            edge_bonus = min(metrics['edge_ratio'] * 10, 1.0)
            comp_bonus = min(metrics['num_components'] / 10, 1.0)
            noise_penalty = min(metrics['noise_score'] / 50000, 1.0)
            
            score = (1 - ink_penalty) + edge_bonus + comp_bonus - noise_penalty
            
            self.logger.debug(
                f"[SmartThreshold] {method_name}: score={score:.2f}, "
                f"ink={metrics['ink_ratio']:.1%}, edge={metrics['edge_ratio']:.1%}"
            )
            
            if score > best_score:
                best_score = score
                best_method = method_name
                best_result = result
        
        # ── 5. Fallback Handling ───────────────────────────────────────
        if best_result is None:
            # All methods collapsed - use Otsu as last resort
            self.logger.warning("[SmartThreshold] All methods failed - using Otsu fallback")
            _, best_result = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            best_method = "Otsu_fallback"
        
        self.logger.info(f"[SmartThreshold] Selected {best_method} (score={best_score:.2f})")
        return best_result
    
    def _is_collapsed(self, mask: np.ndarray, threshold: float = 0.97) -> bool:
        """
        Check if binary result is collapsed (all white or all black).
        
        Args:
            mask: Binary mask to check
            threshold: Threshold for collapse detection (default 97%)
            
        Returns:
            True if mask is collapsed
        """
        if mask.size == 0:
            return True
        
        white_pct = np.sum(mask == 255) / mask.size
        black_pct = np.sum(mask == 0) / mask.size
        
        return white_pct > threshold or black_pct > threshold
    
    def _calculate_metrics(self, mask: np.ndarray) -> dict:
        """
        Calculate metrics for scoring binary mask quality.
        
        Args:
            mask: Binary mask to analyze
            
        Returns:
            Dictionary with metrics
        """
        if mask.dtype != np.uint8:
            mask = mask.astype(np.uint8)
        
        total_pixels = mask.size
        
        # Ink ratio (design pixels = 255 in this context)
        ink_pixels = np.sum(mask == 255)
        ink_ratio = ink_pixels / total_pixels
        
        # Edge ratio
        edges = cv2.Canny(mask, 50, 150)
        edge_pixels = np.sum(edges > 0)
        edge_ratio = edge_pixels / total_pixels
        
        # Connected components
        num_labels, _, stats, _ = cv2.connectedComponentsWithStats(
            mask, 8, cv2.CV_32S
        )
        num_components = num_labels - 1  # Exclude background
        
        # Noise score (small components)
        noise_score = 0
        for label in range(1, num_labels):
            area = stats[label, cv2.CC_STAT_AREA]
            if area < 50:  # Small components = noise
                noise_score += area
        
        return {
            'ink_ratio': ink_ratio,
            'edge_ratio': edge_ratio,
            'num_components': num_components,
            'noise_score': noise_score
        }
    
    def adaptive_threshold(self, 
                         image: np.ndarray, 
                         method: str = 'gaussian',
                         block_size: int = 31,
                         C: float = 5) -> np.ndarray:
        """
        Apply adaptive thresholding with specified parameters.
        
        Args:
            image: Input grayscale image
            method: 'gaussian' or 'mean'
            block_size: Size of neighborhood (must be odd)
            C: Constant subtracted from mean
            
        Returns:
            Binary image
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        if gray.dtype != np.uint8:
            gray = gray.astype(np.uint8)
        
        # Ensure block_size is odd and >= 3
        block_size = max(3, block_size | 1)
        
        if method.lower() == 'gaussian':
            result = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, block_size, C
            )
        else:
            result = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, 
                cv2.THRESH_BINARY, block_size, C
            )
        
        return result
    
    def otsu_threshold(self, image: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Apply Otsu's thresholding method.
        
        Args:
            image: Input grayscale image
            
        Returns:
            Tuple of (binary_image, threshold_value)
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        if gray.dtype != np.uint8:
            gray = gray.astype(np.uint8)
        
        thresh_val, result = cv2.threshold(
            gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        
        return result, float(thresh_val)
    
    def triangle_threshold(self, image: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Apply Triangle thresholding method.
        
        Args:
            image: Input grayscale image
            
        Returns:
            Tuple of (binary_image, threshold_value)
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        if gray.dtype != np.uint8:
            gray = gray.astype(np.uint8)
        
        thresh_val, result = cv2.threshold(
            gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_TRIANGLE
        )
        
        return result, float(thresh_val)
