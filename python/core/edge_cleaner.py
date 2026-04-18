"""
edge_cleaner.py — Edge Cleaning with Morphological Operations
Virtual Design Silk Screen Studio
Fixes the placeholder that was returning mask unchanged
"""

import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)


class EdgeCleaner:
    """
    Clean mask edges using morphological operations and Gaussian smoothing.
    Improves print quality by removing jagged edges and fine noise.
    """

    def clean(
        self,
        mask: np.ndarray,
        kernel_size: int = 3,
        smooth: bool = True,
        smooth_sigma: float = 0.8,
        iterations: int = 1,
    ) -> np.ndarray:
        """
        Clean mask edges.

        Args:
            mask: binary mask (0 and 255)
            kernel_size: Morphological kernel size
            smooth: Apply Gaussian smoothing to edges
            smooth_sigma: Smoothing strength (higher = smoother)
            iterations: Number of iterations to apply

        Returns:
            np.ndarray: mask with clean edges
        """
        logger.debug(f"[EdgeCleaner] Cleaning mask {mask.shape}, kernel={kernel_size}")

        result = mask.copy()

        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (kernel_size, kernel_size)
        )

        for _ in range(iterations):
            # 1. Remove small speckles outside shape
            result = cv2.morphologyEx(result, cv2.MORPH_OPEN, kernel)

            # 2. Fill small holes inside shape
            result = cv2.morphologyEx(result, cv2.MORPH_CLOSE, kernel)

        # TASK 12: Gaussian blur and secondary thresholding removed.
        # Vector paths benefit from clean morphological edges; raster blur is destructive.
        # Parameters 'smooth' and 'smooth_sigma' are kept for API compatibility (no-op).
        
        return result

    def clean_all(
        self,
        masks: list,
        kernel_size: int = 3,
        smooth: bool = True,
    ) -> list:
        """Clean a batch of masks at once."""
        logger.info(f"[EdgeCleaner] Cleaning {len(masks)} masks")
        return [self.clean(m, kernel_size, smooth) for m in masks]

    def anti_alias_edges(self, mask: np.ndarray, radius: int = 1) -> np.ndarray:
        """
        Anti-aliasing for edges - useful for halftone printing.
        Smooths edges with gray levels instead of hard edges.
        """
        blurred = cv2.GaussianBlur(mask, (radius * 4 + 1, radius * 4 + 1), radius)
        return blurred

    def expand_edges(self, mask: np.ndarray, pixels: int = 1) -> np.ndarray:
        """
        Expand edges by pixels - useful to avoid gaps between colors during printing.
        """
        kernel = np.ones((pixels * 2 + 1, pixels * 2 + 1), np.uint8)
        return cv2.dilate(mask, kernel, iterations=1)

    def shrink_edges(self, mask: np.ndarray, pixels: int = 1) -> np.ndarray:
        """
        Shrink edges by pixels - prevents color overlap.
        """
        kernel = np.ones((pixels * 2 + 1, pixels * 2 + 1), np.uint8)
        return cv2.erode(mask, kernel, iterations=1)
