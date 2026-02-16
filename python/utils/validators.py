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
