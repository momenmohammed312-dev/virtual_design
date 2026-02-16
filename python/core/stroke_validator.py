"""
Stroke Width Validator
Validates minimum stroke width for screen printing
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple

class StrokeValidator:
    """Validate and measure stroke widths in masks"""
    
    def __init__(self, min_stroke_mm: float = 0.5, dpi: int = 300):
        """
        Initialize validator
        
        Args:
            min_stroke_mm: Minimum acceptable stroke width in millimeters
            dpi: Image DPI for pixel-to-mm conversion
        """
        self.min_stroke_mm = min_stroke_mm
        self.dpi = dpi
        
        # Calculate minimum pixels
        self.min_stroke_pixels = self._mm_to_pixels(min_stroke_mm)
        
    def _mm_to_pixels(self, mm: float) -> int:
        """Convert millimeters to pixels"""
        inches = mm / 25.4  # mm to inches
        pixels = inches * self.dpi
        return int(round(pixels))
    
    def _pixels_to_mm(self, pixels: int) -> float:
        """Convert pixels to millimeters"""
        inches = pixels / self.dpi
        mm = inches * 25.4
        return round(mm, 2)
    
    def validate_mask(self, mask: np.ndarray) -> Dict:
        """
        Validate stroke widths in a mask
        
        Args:
            mask: Binary mask (0 or 255)
            
        Returns:
            dict: {
                'valid': bool,
                'min_width_pixels': int,
                'min_width_mm': float,
                'violations': int,
                'warnings': list,
                'stats': dict
            }
        """
        print(f"   🔍 Validating stroke widths (min: {self.min_stroke_mm}mm = {self.min_stroke_pixels}px)...")
        
        # Find contours
        contours, _ = cv2.findContours(
            mask, 
            cv2.RETR_EXTERNAL, 
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        if len(contours) == 0:
            return {
                'valid': False,
                'min_width_pixels': 0,
                'min_width_mm': 0,
                'violations': 0,
                'warnings': ['No objects found in mask'],
                'stats': {}
            }
        
        # Calculate stroke widths using distance transform
        dist_transform = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
        
        # Minimum stroke width is 2x the max distance transform value
        # (distance transform gives distance to nearest zero pixel)
        min_width_pixels = int(2 * np.min(dist_transform[dist_transform > 0]))
        max_width_pixels = int(2 * np.max(dist_transform))
        avg_width_pixels = int(2 * np.mean(dist_transform[dist_transform > 0]))
        
        min_width_mm = self._pixels_to_mm(min_width_pixels)
        max_width_mm = self._pixels_to_mm(max_width_pixels)
        avg_width_mm = self._pixels_to_mm(avg_width_pixels)
        
        # Check for violations
        violations = 0
        warnings = []
        
        if min_width_pixels < self.min_stroke_pixels:
            violations += 1
            warnings.append(
                f"⚠️  Minimum stroke width ({min_width_mm}mm) is below "
                f"recommended ({self.min_stroke_mm}mm)"
            )
        
        # Check for thin areas
        thin_areas = np.sum((dist_transform > 0) & (dist_transform < self.min_stroke_pixels / 2))
        total_area = np.sum(mask > 0)
        thin_percentage = (thin_areas / total_area * 100) if total_area > 0 else 0
        
        if thin_percentage > 5:
            warnings.append(
                f"⚠️  {thin_percentage:.1f}% of the design has thin strokes"
            )
        
        # Statistics
        stats = {
            'min_width_pixels': min_width_pixels,
            'max_width_pixels': max_width_pixels,
            'avg_width_pixels': avg_width_pixels,
            'min_width_mm': min_width_mm,
            'max_width_mm': max_width_mm,
            'avg_width_mm': avg_width_mm,
            'thin_area_percentage': round(thin_percentage, 2),
            'total_objects': len(contours)
        }
        
        is_valid = violations == 0
        
        if is_valid:
            print(f"      ✅ Stroke widths OK (min: {min_width_mm}mm, avg: {avg_width_mm}mm)")
        else:
            print(f"      ⚠️  {violations} validation warning(s)")
        
        return {
            'valid': is_valid,
            'min_width_pixels': min_width_pixels,
            'min_width_mm': min_width_mm,
            'violations': violations,
            'warnings': warnings,
            'stats': stats
        }
    
    def thicken_strokes(self, mask: np.ndarray, target_width_mm: float = 0.5) -> np.ndarray:
        """
        Thicken strokes to meet minimum width requirement
        
        Args:
            mask: Binary mask
            target_width_mm: Target stroke width in mm
            
        Returns:
            Mask with thickened strokes
        """
        target_pixels = self._mm_to_pixels(target_width_mm)
        
        # Calculate current width
        dist_transform = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
        current_width = int(2 * np.min(dist_transform[dist_transform > 0]))
        
        if current_width >= target_pixels:
            return mask  # Already thick enough
        
        # Calculate dilation needed
        dilation_needed = (target_pixels - current_width) // 2
        
        if dilation_needed > 0:
            kernel = cv2.getStructuringElement(
                cv2.MORPH_ELLIPSE, 
                (dilation_needed * 2 + 1, dilation_needed * 2 + 1)
            )
            mask = cv2.dilate(mask, kernel, iterations=1)
            print(f"      🔧 Thickened strokes by {dilation_needed}px")
        
        return mask
    
    def create_stroke_width_heatmap(self, mask: np.ndarray) -> np.ndarray:
        """
        Create a heatmap showing stroke widths
        
        Args:
            mask: Binary mask
            
        Returns:
            Color heatmap image (BGR)
        """
        # Distance transform
        dist_transform = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
        
        # Normalize to 0-255
        heatmap = cv2.normalize(dist_transform, None, 0, 255, cv2.NORM_MINMAX)
        heatmap = heatmap.astype(np.uint8)
        
        # Apply colormap
        heatmap_color = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
        
        # Mask out background
        heatmap_color[mask == 0] = [0, 0, 0]
        
        return heatmap_color
