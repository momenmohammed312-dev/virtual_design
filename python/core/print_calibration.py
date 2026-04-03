"""
Print Calibration Module - Professional RIP-level accuracy
Ensures 1:1 scaling: 1cm in design = 1cm in print
"""

import numpy as np
import cv2
from dataclasses import dataclass
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)

@dataclass
class PrintCalibration:
    """Professional print calibration data"""
    dpi: int = 300
    pixels_per_mm: float = 0.0
    pixels_per_cm: float = 0.0
    mm_per_pixel: float = 0.0
    cm_per_pixel: float = 0.0
    
    def __post_init__(self):
        """Calculate conversion factors based on DPI"""
        self.pixels_per_mm = self.dpi / 25.4
        self.pixels_per_cm = self.dpi * 10 / 25.4
        self.mm_per_pixel = 25.4 / self.dpi
        self.cm_per_pixel = 2.54 / self.dpi
    
    def mm_to_pixels(self, mm: float) -> int:
        """Convert millimeters to pixels"""
        return int(round(mm * self.pixels_per_mm))
    
    def cm_to_pixels(self, cm: float) -> int:
        """Convert centimeters to pixels"""
        return int(round(cm * self.pixels_per_cm))
    
    def pixels_to_mm(self, pixels: float) -> float:
        """Convert pixels to millimeters"""
        return pixels * self.mm_per_pixel
    
    def pixels_to_cm(self, pixels: float) -> float:
        """Convert pixels to centimeters"""
        return pixels * self.cm_per_pixel
    
    def validate_1_to_1_scaling(self, design_size_px: Tuple[int, int], 
                               expected_size_mm: Tuple[float, float]) -> bool:
        """Validate if scaling is truly 1:1"""
        expected_w_px = self.mm_to_pixels(expected_size_mm[0])
        expected_h_px = self.mm_to_pixels(expected_size_mm[1])
        
        tolerance = 2  # 2 pixels tolerance
        
        w_ok = abs(design_size_px[0] - expected_w_px) <= tolerance
        h_ok = abs(design_size_px[1] - expected_h_px) <= tolerance
        
        logger.info(f"Scaling validation:")
        logger.info(f"  Design: {design_size_px[0]}x{design_size_px[1]} px")
        logger.info(f"  Expected: {expected_w_px}x{expected_h_px} px ({expected_size_mm[0]}x{expected_size_mm[1]} mm)")
        logger.info(f"  Width OK: {w_ok}, Height OK: {h_ok}")
        
        return w_ok and h_ok


class CalibrationGridGenerator:
    """Generate calibration grids for print testing"""
    
    def __init__(self, calibration: PrintCalibration):
        self.calib = calibration
    
    def create_mm_grid(self, width_mm: float, height_mm: float, 
                      grid_spacing_mm: float = 10.0) -> np.ndarray:
        """Create a millimeter grid for calibration"""
        width_px = self.calib.mm_to_pixels(width_mm)
        height_px = self.calib.mm_to_pixels(height_mm)
        spacing_px = self.calib.mm_to_pixels(grid_spacing_mm)
        
        # White background
        grid = np.ones((height_px, width_px, 3), dtype=np.uint8) * 255
        
        # Draw vertical lines
        for x in range(0, width_px, spacing_px):
            cv2.line(grid, (x, 0), (x, height_px), (200, 200, 200), 1)
        
        # Draw horizontal lines
        for y in range(0, height_px, spacing_px):
            cv2.line(grid, (0, y), (width_px, y), (200, 200, 200), 1)
        
        # Draw major lines every 50mm
        major_spacing_px = self.calib.mm_to_pixels(50.0)
        for x in range(0, width_px, major_spacing_px):
            cv2.line(grid, (x, 0), (x, height_px), (100, 100, 100), 2)
            # Add labels
            mm_val = int(x / self.calib.pixels_per_mm)
            cv2.putText(grid, f"{mm_val}mm", (x + 5, 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        
        for y in range(0, height_px, major_spacing_px):
            cv2.line(grid, (0, y), (width_px, y), (100, 100, 100), 2)
            # Add labels
            mm_val = int(y / self.calib.pixels_per_mm)
            cv2.putText(grid, f"{mm_val}mm", (5, y - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        
        # Add calibration info
        info_text = f"Calibration Grid: {width_mm}x{height_mm}mm @ {self.calib.dpi} DPI"
        cv2.putText(grid, info_text, (10, height_px - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        return grid
    
    def create_test_pattern(self, width_mm: float = 100.0, height_mm: float = 100.0) -> np.ndarray:
        """Create a professional test pattern for print validation"""
        width_px = self.calib.mm_to_pixels(width_mm)
        height_px = self.calib.mm_to_pixels(height_mm)
        
        # White background
        pattern = np.ones((height_px, width_px, 3), dtype=np.uint8) * 255
        
        # 1. Resolution test lines (varying thickness)
        line_widths_mm = [0.1, 0.15, 0.2, 0.3, 0.5]  # Minimum printable line widths
        y_offset = self.calib.mm_to_pixels(10)
        
        for i, line_width in enumerate(line_widths_mm):
            line_width_px = max(1, self.calib.mm_to_pixels(line_width))
            y = y_offset + i * self.calib.mm_to_pixels(5)
            
            # Horizontal line
            cv2.line(pattern, (self.calib.mm_to_pixels(10), y), 
                    (width_px - self.calib.mm_to_pixels(10), y), 
                    (0, 0, 0), line_width_px)
            
            # Label
            cv2.putText(pattern, f"{line_width}mm", 
                       (self.calib.mm_to_pixels(2), y + 3), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
        
        # 2. Circle test (check for roundness)
        center_x = width_px // 2
        center_y = height_px // 2 + self.calib.mm_to_pixels(20)
        
        circle_radii_mm = [5, 10, 15, 20]
        for i, radius_mm in enumerate(circle_radii_mm):
            radius_px = self.calib.mm_to_pixels(radius_mm)
            cv2.circle(pattern, (center_x, center_y + i * self.calib.mm_to_pixels(25)), 
                      radius_px, (0, 0, 0), 2)
            
            # Label
            cv2.putText(pattern, f"R{radius_mm}mm", 
                       (center_x + radius_px + 5, center_y + i * self.calib.mm_to_pixels(25) + 3), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
        
        # 3. Text test (check readability)
        text_sizes = [6, 8, 10, 12]  # Point sizes
        text_y = height_px - self.calib.mm_to_pixels(30)
        
        for i, pt_size in enumerate(text_sizes):
            # Convert points to pixels (1 point = 1/72 inch)
            px_size = int(pt_size * self.calib.dpi / 72)
            cv2.putText(pattern, f"{pt_size}pt", 
                       (self.calib.mm_to_pixels(10) + i * self.calib.mm_to_pixels(20), text_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, px_size / 30, (0, 0, 0), 1)
        
        # 4. Registration marks
        mark_size = self.calib.mm_to_pixels(5)
        mark_positions = [
            (mark_size, mark_size),
            (width_px - mark_size, mark_size),
            (mark_size, height_px - mark_size),
            (width_px - mark_size, height_px - mark_size)
        ]
        
        for x, y in mark_positions:
            # Crosshair
            cv2.line(pattern, (x - mark_size, y), (x + mark_size, y), (0, 0, 0), 1)
            cv2.line(pattern, (x, y - mark_size), (x, y + mark_size), (0, 0, 0), 1)
            # Circle
            cv2.circle(pattern, (x, y), mark_size // 2, (0, 0, 0), 1)
        
        # Add calibration info
        info_text = f"Print Test Pattern: {width_mm}x{height_mm}mm @ {self.calib.dpi} DPI"
        cv2.putText(pattern, info_text, (10, height_px - 5), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        return pattern


class PrintAccuracyValidator:
    """Validate print accuracy with real-world measurements"""
    
    def __init__(self, calibration: PrintCalibration):
        self.calib = calibration
    
    def create_measurement_template(self, design_size_px: Tuple[int, int]) -> np.ndarray:
        """Create a template for measuring printed output"""
        h, w = design_size_px
        template = np.ones((h, w, 3), dtype=np.uint8) * 255
        
        # Add measurement rulers
        ruler_spacing = self.calib.mm_to_pixels(10)  # 10mm spacing
        
        # Top ruler
        for x in range(0, w, ruler_spacing):
            cv2.line(template, (x, 0), (x, self.calib.mm_to_pixels(5)), (0, 0, 0), 1)
            if x > 0:
                mm_val = int(x / self.calib.pixels_per_mm)
                cv2.putText(template, f"{mm_val}", (x - 10, self.calib.mm_to_pixels(8)), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 0), 1)
        
        # Left ruler
        for y in range(0, h, ruler_spacing):
            cv2.line(template, (0, y), (self.calib.mm_to_pixels(5), y), (0, 0, 0), 1)
            if y > 0:
                mm_val = int(y / self.calib.pixels_per_mm)
                cv2.putText(template, f"{mm_val}", (self.calib.mm_to_pixels(8), y + 3), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 0), 1)
        
        # Add center crosshair
        center_x, center_y = w // 2, h // 2
        cv2.line(template, (center_x - 20, center_y), (center_x + 20, center_y), (255, 0, 0), 1)
        cv2.line(template, (center_x, center_y - 20), (center_x, center_y + 20), (255, 0, 0), 1)
        
        # Add info
        real_w_mm = self.calib.pixels_to_mm(w)
        real_h_mm = self.calib.pixels_to_mm(h)
        info = f"Design: {w}x{h}px = {real_w_mm:.1f}x{real_h_mm:.1f}mm @ {self.calib.dpi} DPI"
        cv2.putText(template, info, (10, h - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        return template
    
    def validate_printed_size(self, design_size_px: Tuple[int, int], 
                            measured_size_mm: Tuple[float, float]) -> dict:
        """Validate if printed size matches expected size"""
        expected_w_mm = self.calib.pixels_to_mm(design_size_px[0])
        expected_h_mm = self.calib.pixels_to_mm(design_size_px[1])
        
        w_error_pct = ((measured_size_mm[0] - expected_w_mm) / expected_w_mm) * 100
        h_error_pct = ((measured_size_mm[1] - expected_h_mm) / expected_h_mm) * 100
        
        # Industry standard tolerance: ±1mm or ±1%, whichever is stricter
        w_tolerance = max(1.0, expected_w_mm * 0.01)
        h_tolerance = max(1.0, expected_h_mm * 0.01)
        
        w_accurate = abs(measured_size_mm[0] - expected_w_mm) <= w_tolerance
        h_accurate = abs(measured_size_mm[1] - expected_h_mm) <= h_tolerance
        
        return {
            'design_size_px': design_size_px,
            'expected_size_mm': (expected_w_mm, expected_h_mm),
            'measured_size_mm': measured_size_mm,
            'width_error_pct': w_error_pct,
            'height_error_pct': h_error_pct,
            'width_accurate': w_accurate,
            'height_accurate': h_accurate,
            'overall_accurate': w_accurate and h_accurate,
            'tolerance_mm': (w_tolerance, h_tolerance)
        }


# Global calibration instance
CALIBRATION = PrintCalibration(dpi=300)

def get_calibration(dpi: int = 300) -> PrintCalibration:
    """Get calibrated instance for specific DPI"""
    return PrintCalibration(dpi=dpi)
