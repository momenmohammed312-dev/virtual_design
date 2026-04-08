"""
underbase_generator.py — White Underbase and Ink Trapping
Virtual Design Silk Screen Studio
"""

import cv2
import numpy as np
from typing import List, Tuple, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class UnderbaseGenerator:
    """
    Generates a White Underbase (Flash) layer for printing on dark garments.
    Also handles Ink Trapping (overlaps) to prevent registration gaps.
    """

    def generate_underbase(
        self, 
        masks: List[np.ndarray], 
        choke_px: int = 2,
        mode: str = "full"
    ) -> np.ndarray:
        """
        Creates a white underbase layer from all existing color masks.
        
        Args:
            masks: List of color masks (ink=0, bg=255)
            choke_px: Pixels to shrink the underbase (to avoid white edges showing)
            mode: "full" (all colors) or "selective" (exclude dark colors)
            
        Returns:
            Single binary mask for the White Underbase
        """
        if not masks:
            return None
            
        logger.info(f"[Underbase] Generating underbase (choke={choke_px}px, mode={mode})")
        
        # 1. Combine all ink areas
        combined_ink = np.zeros_like(masks[0])
        for mask in masks:
            ink = cv2.bitwise_not(mask)
            combined_ink = cv2.bitwise_or(combined_ink, ink)
            
        # 2. Apply Choke (Shrinking)
        # We erode the INK area so it stays hidden under the top colors
        if choke_px > 0:
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (choke_px*2+1, choke_px*2+1))
            underbase_ink = cv2.erode(combined_ink, kernel, iterations=1)
        else:
            underbase_ink = combined_ink
            
        underbase_mask = cv2.bitwise_not(underbase_ink)
        return underbase_mask

    def apply_trapping(
        self, 
        masks: List[np.ndarray], 
        trap_px: int = 1
    ) -> List[np.ndarray]:
        """
        Expands mask boundaries slightly to create overlaps (trapping).
        This prevents white gaps between colors on the press.
        """
        if trap_px <= 0:
            return masks
            
        logger.info(f"[Trapping] Expanding {len(masks)} masks by {trap_px}px")
        
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (trap_px*2+1, trap_px*2+1))
        trapped_masks = []
        
        for mask in masks:
            ink = cv2.bitwise_not(mask)
            # Dilate the INK area
            trapped_ink = cv2.dilate(ink, kernel, iterations=1)
            trapped_masks.append(cv2.bitwise_not(trapped_ink))
            
        return trapped_masks
