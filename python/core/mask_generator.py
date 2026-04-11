"""
mask_generator.py — Binary Mask Generator for each color layer
Virtual Design Silk Screen Studio
FIXED: BUG B - get_mask_stats() counting ink pixels correctly + adaptive epsilon
P1 ENHANCEMENT: Added professional ink trapping functionality
"""

import cv2
import numpy as np
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


def apply_ink_trapping(
    masks: List[np.ndarray], 
    trap_width_px: int = 3,
    trap_method: str = "expand_into_inks"
) -> List[np.ndarray]:
    """
    P1 ENHANCEMENT: Professional ink trapping to prevent white gaps.
    
    Ink trapping is the process of slightly overlapping adjacent color layers
    to prevent white gaps at color boundaries due to press misregistration.
    
    Args:
        masks: List of binary masks (ink=0, bg=255)
        trap_width_px: Trap width in pixels (typically 2-4px for 300 DPI)
        trap_method: "expand_into_inks" or "expand_all"
    
    Returns:
        List of trapped masks with proper overlap
    """
    if len(masks) < 2:
        return masks
    
    logger.info(f"[InkTrapping] Applying {trap_width_px}px trap to {len(masks)} masks")
    
    # Create elliptical structuring element for natural trap shape
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (trap_width_px*2+1, trap_width_px*2+1))
    
    # Create combined ink areas for trapping reference
    combined_ink = np.zeros_like(masks[0])
    for mask in masks:
        ink = cv2.bitwise_not(mask)
        combined_ink = cv2.bitwise_or(combined_ink, ink)
    
    trapped_masks = []
    
    for i, mask in enumerate(masks):
        ink = cv2.bitwise_not(mask)
        
        if trap_method == "expand_into_inks":
            # Method 1: Only expand into areas covered by OTHER inks
            dilated_ink = cv2.dilate(ink, kernel, iterations=1)
            
            # Find expansion areas (where dilated_ink overlaps other inks)
            expansion = cv2.bitwise_and(dilated_ink, combined_ink)
            expansion = cv2.bitwise_and(expansion, cv2.bitwise_not(ink))  # Remove original ink
            
            # Apply expansion only to adjacent ink areas
            trapped_ink = cv2.bitwise_or(ink, expansion)
            trapped_mask = cv2.bitwise_not(trapped_ink)
            
        else:  # trap_method == "expand_all"
            # Method 2: Simple expansion of all ink areas
            trapped_ink = cv2.dilate(ink, kernel, iterations=1)
            trapped_mask = cv2.bitwise_not(trapped_ink)
        
        trapped_masks.append(trapped_mask)
    
    logger.info(f"[InkTrapping] Completed trapping for {len(trapped_masks)} masks")
    return trapped_masks


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
        dpi: int = 300,  # FIX GROUP 2.1: Added DPI parameter for scaling
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
        
        # 🔥 NEW: Get background mask if available
        bg_mask = separation_result.get("bg_mask", None)
        bg_pixels = 0
        if bg_mask is not None:
            bg_pixels = np.sum(bg_mask)
            logger.info(f"[MaskGenerator] Background mask found: {bg_pixels} bg pixels will stay white")

        # FIX GROUP 2.1: Calculate DPI-scaled minimum component size
        min_component_px = max(5, int(20 * (dpi / 300) ** 2))
        logger.info(f"[MaskGenerator] Generating {num_colors} masks (grayscale_output={grayscale_output}, dpi={dpi}, min_component_px={min_component_px})")
        masks = []

        # Get original image for grayscale output
        if len(image.shape) == 3:
            gray_orig = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray_orig = image.copy()

        for i in range(num_colors):
            # 🔥 FIX: Proper film polarity mask generation
            # Start with WHITE background (255), then set selected label pixels to BLACK (0)
            mask = np.full(label_map.shape, 255, dtype=np.uint8)
            mask[label_map == i] = 0  # Design pixels = BLACK (ink)
            
            # 🔥 NEW: Ensure background pixels stay white (255)
            if bg_mask is not None:
                mask[bg_mask] = 255  # Background always white (transparent on film)
            # Also handle label_map == -1 (background label)
            mask[label_map == -1] = 255
            
            if grayscale_output:
                # For halftone: preserve grayscale intensity from original image
                # Only apply grayscale to design pixels (where mask == 0)
                selected_pixels = (label_map == i)
                if np.any(selected_pixels):
                    mask[selected_pixels] = gray_orig[selected_pixels]
                
                # Ensure background stays white even in grayscale mode
                if bg_mask is not None:
                    mask[bg_mask] = 255
                mask[label_map == -1] = 255

            if apply_cleanup and not grayscale_output:
                # FIX 1 (single smoothing source): _cleanup_mask only.
                # _smart_smooth_mask REMOVED \u2014 it added a 2nd morphological close
                # + boundary Gaussian that produced halos and wavy straight lines.
                # The vector exporter's geometry-aware Catmull-Rom is now the only
                # smoothing stage for all artwork.
                mask = self._cleanup_mask(mask, morph_kernel_size, min_area)
                # After cleanup, ensure background is still white
                if bg_mask is not None:
                    mask[bg_mask] = 255
                mask[label_map == -1] = 255
                
                # FINAL FIX: enforce strict binary integrity
                mask = (mask > 127).astype(np.uint8) * 255


            elif grayscale_output:
                # FIX GROUP 2.2: Polarity enforcement after grayscale_output
                from core.pipeline_controller import PipelineController
                ctrl = PipelineController()
                mask = ctrl.enforce_polarity(mask, stage=f"grayscale_mask_{i}")

            # FIXED: Log correct ink coverage (design pixels = 0)
            coverage = self.get_mask_stats(mask)["filled_pixels"]
            # Calculate coverage excluding background
            if bg_mask is not None:
                fg_pixels_only = np.sum(~bg_mask)
                coverage_excl_bg = coverage / fg_pixels_only * 100 if fg_pixels_only > 0 else 0
                logger.info(f"  Mask {i+1}: {coverage} ink pixels ({coverage_excl_bg:.1f}% of foreground)")
            else:
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

        FIX A-09: Removed the duplicate _smart_smooth_mask() call that was
        previously the last line of this method.  generate_masks() calls
        _smart_smooth_mask() once after _cleanup_mask() returns — having it
        also at the end here meant every mask received two consecutive 3×3
        morphological closings (equivalent to a ~5px closing), which erased
        thin strokes and Arabic diacritics below ~7px width.
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

        # FIX A-09: do NOT call _smart_smooth_mask here.
        # Smoothing is the caller's responsibility (generate_masks does it once).
        return cleaned


    def _remove_small_components(self, mask: np.ndarray, min_area: int) -> np.ndarray:
        """
        Remove connected components smaller than min_area.
        Enhanced with DPI-aware minimum area for better small detail preservation.
        
        Args:
            mask: Binary mask
            min_area: Minimum area threshold
            
        Returns:
            Mask with small components removed
        """
        # Use smaller minimum area for high DPI to preserve fine details
        if min_area > 0:
            # Scale minimum area based on typical DPI ranges
            # This prevents removing legitimate small details in high-resolution images
            min_area = max(min_area, 15)  # Ensure minimum 15px for fine details
        
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

    def _smart_smooth_mask(self, mask: np.ndarray, min_component_px: int = 20) -> np.ndarray:
        """
        Apply morphological closing and selective boundary smoothing to eliminate jagged edges.
        Replaces approxPolyDP which was causing angular artifacts.

        Args:
            mask: Binary mask to smooth
            min_component_px: Minimum component size to keep (FIX GROUP 2.1: now DPI-scaled)

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
            if stats[lbl, cv2.CC_STAT_AREA] >= min_component_px:  # FIX: Now uses parameter
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
