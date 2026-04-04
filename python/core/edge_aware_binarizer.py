"""
Edge-Aware Binarizer - Simple Implementation
Preserves sharp text edges and prevents bloating
"""

import cv2
import numpy as np
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class EdgeAwareConfig:
    """Configuration for Edge-Aware Binarizer"""
    def __init__(self):
        self.window_size = 51
        self.min_area = 3
        self.edge_threshold = 50
        self.preserve_thin_strokes = True

class EdgeAwareBinarizer:
    """
    Simple Edge-Aware Binarizer that preserves text sharpness
    and prevents the bloating effect of standard Otsu
    """
    
    def __init__(self, config: EdgeAwareConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.EdgeAwareBinarizer")
    
    def binarize(self, image: np.ndarray, **kwargs) -> np.ndarray:
        """
        Edge-aware binarization that preserves thin strokes
        """
        request_id = kwargs.get('request_id', 'unknown')
        self.logger.info(f"[{request_id}] Edge-Aware Binarization started")
        
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # 🔥 KEY FIX: Use constant threshold for sharp text
        # Instead of Otsu which causes bloating, use a high threshold
        # to capture only the dark core of characters
        threshold_value = 180  # High value to avoid gray edges
        
        # Apply threshold
        _, binary = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY)
        
        # 🔥 Edge preservation: Use morphological operations carefully
        # Small closing to connect broken parts, but preserve thin strokes
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)
        
        # 🔥 Counter preservation: Ensure small holes in letters aren't filled
        # Find and preserve small components (like holes in A, R, O)
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
        
        # Create result preserving small components
        result = np.full_like(binary, 255)  # Start with white background
        
        for i in range(1, num_labels):  # Skip background (label 0)
            area = stats[i, cv2.CC_STAT_AREA]
            
            # Preserve main text areas but also keep small holes
            if area >= self.config.min_area:
                # Check if this is a hole (surrounded by black)
                component_mask = (labels == i).astype(np.uint8) * 255
                
                # For small components, check if they're holes
                if area < 100:  # Small component - could be a hole
                    # Check if it's surrounded by black pixels
                    dilated = cv2.dilate(component_mask, np.ones((3,3), np.uint8), iterations=2)
                    surrounding = binary[dilated > 0]
                    
                    # If mostly black around, it's a hole - preserve it as white
                    if np.sum(surrounding == 0) > np.sum(surrounding == 255):
                        continue  # Keep as white (hole)
                
                # Add the component to result
                result[labels == i] = 0  # Make it black
        self.logger.info(f"[{request_id}] Edge-Aware Binarization completed")
        return result
    
    def get_quality_metrics(self, original: np.ndarray, binary: np.ndarray) -> Dict[str, float]:
        """
        Calculate quality metrics for the binarization result
        """
        if original is None or binary is None:
            return {"edge_preservation": 0.0, "noise_reduction": 0.0}
            
        # Rescale for faster processing
        h, w = original.shape[:2]
        scale = min(1.0, 500.0 / max(h, w))
        orig_s = cv2.resize(original, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        bin_s = cv2.resize(binary, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
        
        # Edges of original
        orig_edges = cv2.Canny(orig_s, 50, 150)
        # Edges of binary
        bin_edges = cv2.Canny(bin_s, 50, 150)
        
        # Edge preservation: how many original edge pixels are preserved in binary edges
        intersection = cv2.bitwise_and(orig_edges, bin_edges)
        edge_pres = np.count_nonzero(intersection) / max(1, np.count_nonzero(orig_edges))
        
        # Noise reduction: estimate based on small components in binary
        num, _, stats, _ = cv2.connectedComponentsWithStats(cv2.bitwise_not(bin_s), connectivity=8)
        small_comp_ratio = np.sum(stats[1:, cv2.CC_STAT_AREA] < 10) / max(1, num-1) if num > 1 else 0.0
        noise_red = 1.0 - small_comp_ratio
        
        return {
            "edge_preservation": float(edge_pres),
            "noise_reduction": float(noise_red)
        }

    def get_health_summary(self) -> Dict[str, Any]:
        return {"status": "ok", "method": "edge_aware"}
    
    def auto_threshold(self, image: np.ndarray, preferred_method: str = 'auto', **kwargs) -> np.ndarray:
        """
        Compatibility method - delegates to binarize
        """
        return self.binarize(image, **kwargs)
