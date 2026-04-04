"""
Input validation utilities
"""

from pathlib import Path
from typing import Tuple, Optional
import os

class Validators:
    """Input validation functions"""
    
    SUPPORTED_FORMATS = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']
    
    @staticmethod
    def validate_image_path(path: str) -> Tuple[bool, Optional[str]]:
        """
        Validate image file path
        
        Args:
            path: Path to image file
            
        Returns:
            tuple: (is_valid, error_message)
        """
        # Check if exists
        if not os.path.exists(path):
            return False, f"File not found: {path}"
        
        # Check if file
        if not os.path.isfile(path):
            return False, f"Not a file: {path}"
        
        # Check extension
        ext = Path(path).suffix.lower()
        if ext not in Validators.SUPPORTED_FORMATS:
            return False, f"Unsupported format: {ext}. Supported: {', '.join(Validators.SUPPORTED_FORMATS)}"
        
        return True, None
    
    @staticmethod
    def validate_color_count(n_colors: int) -> Tuple[bool, Optional[str]]:
        """
        Validate color count
        
        Args:
            n_colors: Number of colors
            
        Returns:
            tuple: (is_valid, error_message)
        """
        if n_colors < 1:
            return False, "Color count must be at least 1"
        
        if n_colors > 16:
            return False, "Color count cannot exceed 16"
        
        return True, None
    
    @staticmethod
    def validate_dpi(dpi: int) -> Tuple[bool, Optional[str]]:
        """
        Validate DPI value
        
        Args:
            dpi: DPI value
            
        Returns:
            tuple: (is_valid, error_message)
        """
        if dpi < 72:
            return False, "DPI must be at least 72"
        
        if dpi > 1200:
            return False, "DPI cannot exceed 1200"
        
        if dpi < 300:
            return True, "⚠️  Warning: DPI below 300 may result in poor print quality"
        
        return True, None
    
    @staticmethod
    def validate_stroke_width(width_mm: float) -> Tuple[bool, Optional[str]]:
        """
        Validate stroke width
        
        Args:
            width_mm: Stroke width in millimeters
            
        Returns:
            tuple: (is_valid, error_message)
        """
        if width_mm < 0.1:
            return False, "Stroke width must be at least 0.1mm"
        
        if width_mm > 10:
            return False, "Stroke width cannot exceed 10mm"
        
        if width_mm < 0.5:
            return True, "⚠️  Warning: Strokes below 0.5mm may not print clearly"
        
        return True, None
    
    @staticmethod
    def validate_lpi(lpi: int) -> Tuple[bool, Optional[str]]:
        """
        Validate lines per inch for halftone
        
        Args:
            lpi: Lines per inch
            
        Returns:
            tuple: (is_valid, error_message)
        """
        if lpi < 20:
            return False, "LPI must be at least 20"
        
        if lpi > 100:
            return False, "LPI cannot exceed 100"
        
        if lpi < 45:
            return True, "⚠️  Warning: LPI below 45 may result in visible dots"
        
        if lpi > 85:
            return True, "⚠️  Warning: LPI above 85 may cause screen clogging"
        
        return True, None

    @staticmethod
    def slider_to_smoothing_params(slider_value: int) -> Tuple[float, float]:
        """
        Converts unified smoothing slider (0-100) to smoothing_factor and epsilon.
        
        Design principles:
        - 0-30: sharp logos, text
        - 30-70: artwork balanced
        - 70-100: smooth illustrations
        
        Args:
            slider_value: 0 (sharp) to 100 (smooth)
        Returns:
            (smoothing_factor, epsilon)
        """
        # Clamp slider value
        slider_value = max(0, min(100, slider_value))
        t = float(slider_value) / 100.0  # normalize to [0, 1]
        
        # ① Smoothing Factor: S-curve (ease-in-out) to avoid sudden jumps
        # Formula: 3t² - 2t³ (Hermite interpolation)
        smooth_t = 3 * (t**2) - 2 * (t**3)
        # Smoothing factor: 0.0 (sharp) -> 0.45 (very smooth)
        smoothing_factor = 0.0 + smooth_t * 0.45
        
        # ② Epsilon: Quadratic inverse - logo needs very small epsilon
        # Slider=0 -> epsilon=0.3 (fine details)
        # Slider=100 -> epsilon=8.0 (strong smoothing)
        epsilon = 0.3 + (t ** 1.5) * 7.7
        
        return round(float(smoothing_factor), 3), round(float(epsilon), 2)
