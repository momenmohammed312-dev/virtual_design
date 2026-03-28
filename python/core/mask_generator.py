"""
mask_generator.py — Binary Mask Generator for each color layer
Virtual Design Silk Screen Studio
FIXED: BUG B - get_mask_stats() counting ink pixels correctly + adaptive epsilon
"""

import cv2
import numpy as np
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class MaskGenerator:
    """
    يولّد binary mask (أبيض وأسود) لكل لون من نتيجة ColorSeparator.
    يطبق morphological operations لتنظيف الـ masks.
    FIXED: Correct ink pixel counting and adaptive contour epsilon
    """

    def generate_masks(
        self,
        image: np.ndarray,
        separation_result: Dict,
        morph_kernel_size: int = 3,
        min_area: int = 50,
        apply_cleanup: bool = True,
        grayscale_output: bool = False,
    ) -> List[np.ndarray]:
        """
        توليد قائمة masks — mask لكل لون.

        Args:
            image: الصورة الأصلية (للمرجع)
            separation_result: نتيجة ColorSeparator.separate()
            morph_kernel_size: حجم kernel للـ morphological ops
            min_area: أصغر مساحة (pixels) تُحذَف كـ noise
            apply_cleanup: تطبيق التنظيف المورفولوجي
            grayscale_output: إذا كان True، الـ mask يحتفظ بـ grayscale intensity
                              من الصورة الأصلية (للـ halftone قبل الـ binarization)

        Returns:
            List[np.ndarray]: mask لكل لون (film polarity: ink=0, bg=255)
        """
        label_map = separation_result["label_map"]
        num_colors = separation_result["num_colors"]

        logger.info(f"[MaskGenerator] Generating {num_colors} masks (grayscale_output={grayscale_output})")
        masks = []

        # Get original image for grayscale output
        if len(image.shape) == 3:
            gray_orig = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray_orig = image.copy()

        for i in range(num_colors):
            # Start with white background (film polarity)
            mask = np.full(label_map.shape, 255, dtype=np.uint8)

            if grayscale_output:
                # For halftone: preserve grayscale intensity from original image
                mask[label_map == i] = 255 - gray_orig[label_map == i]
            else:
                # For solid: black design on white background (film polarity)
                mask[label_map == i] = 0  # Design pixels = BLACK (0)

            if apply_cleanup and not grayscale_output:
                mask = self._cleanup_mask(mask, morph_kernel_size, min_area)

            # FIXED: Log correct ink coverage (design pixels = 0)
            coverage = self.get_mask_stats(mask)["filled_pixels"]
            logger.info(f"  Mask {i+1}: {coverage} pixels ({coverage/label_map.size:.1%} coverage)")

            masks.append(mask)

        return masks

    def get_mask_stats(self, mask: np.ndarray) -> Dict:
        """
        FIXED: Count ink pixels correctly (mask == 0 for film polarity)
        
        Args:
            mask: Binary mask with film polarity (ink=0, bg=255)
            
        Returns:
            Dictionary with mask statistics
        """
        if mask.dtype != np.uint8:
            mask = mask.astype(np.uint8)

        total_pixels = mask.size
        
        # FIXED: Count ink pixels (design = 0 in film polarity)
        filled = int(np.sum(mask == 0))  # BLACK pixels = design
        empty = total_pixels - filled
        
        # Calculate coverage percentage
        coverage_pct = (filled / total_pixels) * 100 if total_pixels > 0 else 0

        return {
            "total_pixels": total_pixels,
            "filled_pixels": filled,      # Design pixels
            "empty_pixels": empty,        # Background pixels
            "coverage_pct": coverage_pct
        }

    def _cleanup_mask(self, mask: np.ndarray, kernel_size: int = 3, min_area: int = 50) -> np.ndarray:
        """
        Apply morphological cleanup to remove noise and fill holes.
        Uses adaptive epsilon for small contours (Arabic dots, hamza, etc.)
        
        Args:
            mask: Binary mask to clean
            kernel_size: Size of morphological kernel
            min_area: Minimum area for connected components
            
        Returns:
            Cleaned binary mask
        """
        if mask.dtype != np.uint8:
            mask = mask.astype(np.uint8)

        # Morphological opening to remove small noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        cleaned = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        # Morphological closing to fill small holes
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel)

        # Remove small connected components (noise removal)
        if min_area > 0:
            cleaned = self._remove_small_components(cleaned, min_area)

        # Apply smart smoothing for contours (adaptive epsilon)
        cleaned = self._smart_smooth_mask(cleaned)

        return cleaned

    def _remove_small_components(self, mask: np.ndarray, min_area: int) -> np.ndarray:
        """
        Remove connected components smaller than min_area.
        
        Args:
            mask: Binary mask
            min_area: Minimum area threshold
            
        Returns:
            Mask with small components removed
        """
        # Find connected components (work on white pixels)
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
            cv2.bitwise_not(mask), 8, cv2.CV_32S
        )

        # Create output mask with white background
        result = np.full_like(mask, 255)

        # Keep only components larger than min_area
        for label in range(1, num_labels):
            area = stats[label, cv2.CC_STAT_AREA]
            if area >= min_area:
                # Set pixels of this component to black (design)
                result[labels == label] = 0

        return result

    def _smart_smooth_mask(self, mask: np.ndarray) -> np.ndarray:
        """
        Apply morphological closing and selective boundary smoothing to eliminate jagged edges.
        Replaces approxPolyDP which was causing angular artifacts.
        
        Args:
            mask: Binary mask to smooth
            
        Returns:
            Smoothed mask
        """
        if mask.dtype != np.uint8:
            mask = mask.astype(np.uint8)

        # Step 1: remove tiny isolated noise components
        inv = cv2.bitwise_not(mask)
        num, labels, stats, _ = cv2.connectedComponentsWithStats(inv, 8, cv2.CV_32S)
        clean_inv = np.zeros_like(inv)
        for lbl in range(1, num):
            if stats[lbl, cv2.CC_STAT_AREA] >= 20: # Keep components >= 20px
                clean_inv[labels == lbl] = 255

        # Step 2: morphological closing — fills small holes, smooth edges
        k_size = 3
        # Use elliptical kernel for natural rounded edges
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k_size, k_size))
        smoothed = cv2.morphologyEx(clean_inv, cv2.MORPH_CLOSE, kernel)

        # Step 3: gentle Gaussian on the BOUNDARY only (not full image)
        # This preserves solid fills while smoothing only the edge transitions
        dilated = cv2.dilate(smoothed, kernel, iterations=1)
        eroded  = cv2.erode(smoothed,  kernel, iterations=1)
        boundary = dilated - eroded   # Provides a thin boundary ring
        
        # Apply gentle blur only to the boundary pixels
        blurred_boundary = cv2.GaussianBlur(boundary, (3, 3), 0.8)
        
        # Combine eroded core with blurred boundary to get smooth but sharp edges
        # We need to Ensure bitwise_or works on same types
        smoothed = cv2.bitwise_or(eroded, blurred_boundary)

        return cv2.bitwise_not(smoothed)


    def validate_masks(self, masks: List[np.ndarray]) -> List[bool]:
        """
        Validate each mask for common issues.
        
        Args:
            masks: List of binary masks to validate
            
        Returns:
            List of validation results (True = valid, False = invalid)
        """
        results = []
        
        for i, mask in enumerate(masks):
            stats = self.get_mask_stats(mask)
            
            # Check for empty mask
            if stats["filled_pixels"] == 0:
                logger.warning(f"  [Validate] Mask {i+1}: EMPTY - no design pixels")
                results.append(False)
                continue
            
            # Check for overly filled mask (possible polarity issue)
            if stats["coverage_pct"] > 95:
                logger.warning(f"  [Validate] Mask {i+1}: OVERFILLED - {stats['coverage_pct']:.1f}% coverage")
                results.append(False)
                continue
            
            # Check for very sparse mask
            if stats["coverage_pct"] < 0.5:
                logger.warning(f"  [Validate] Mask {i+1}: TOO SPARSE - {stats['coverage_pct']:.1f}% coverage")
                results.append(False)
                continue
            
            # Mask looks good
            logger.debug(f"  [Validate] Mask {i+1}: OK - {stats['coverage_pct']:.1f}% coverage")
            results.append(True)
        
        return results

    def combine_masks(self, masks: List[np.ndarray], operation: str = "union") -> np.ndarray:
        """
        Combine multiple masks using specified operation.
        
        Args:
            masks: List of masks to combine
            operation: "union", "intersection", or "difference"
            
        Returns:
            Combined mask
        """
        if not masks:
            return np.zeros((100, 100), dtype=np.uint8)  # Default empty mask
        
        if len(masks) == 1:
            return masks[0].copy()

        # Start with first mask
        result = masks[0].copy()

        if operation == "union":
            # Union: any pixel that is design in any mask
            for mask in masks[1:]:
                result = cv2.bitwise_or(result, mask)
        
        elif operation == "intersection":
            # Intersection: pixel must be design in all masks
            for mask in masks[1:]:
                result = cv2.bitwise_and(result, mask)
        
        elif operation == "difference":
            # Difference: subtract subsequent masks from first
            for mask in masks[1:]:
                result = cv2.bitwise_xor(result, mask)
        
        return result

    def mask_to_grayscale(self, mask: np.ndarray, intensity: int = 128) -> np.ndarray:
        """
        Convert binary mask to grayscale with specified intensity.
        
        Args:
            mask: Binary mask (film polarity)
            intensity: Grayscale intensity for design pixels (0-255)
            
        Returns:
            Grayscale mask
        """
        if mask.dtype != np.uint8:
            mask = mask.astype(np.uint8)

        # Create grayscale result
        gray = np.full_like(mask, 255)  # White background
        
        # Set design pixels to specified intensity
        gray[mask == 0] = intensity
        
        return gray
