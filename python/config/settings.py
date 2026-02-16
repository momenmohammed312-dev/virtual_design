"""
Configuration settings
"""

from dataclasses import dataclass
from typing import Literal

@dataclass
class ProcessingSettings:
    """Processing configuration"""
    
    # Image settings
    target_dpi: int = 300
    min_image_width: int = 500
    min_image_height: int = 500
    
    # Color separation
    n_colors: int = 4
    kmeans_attempts: int = 10
    
    # Stroke validation
    min_stroke_mm: float = 0.5
    auto_thicken: bool = False
    
    # Edge cleaning
    clean_edges: bool = True
    kernel_size: int = 3
    morph_iterations: int = 1
    remove_small_objects: bool = True
    min_object_area: int = 50
    
    # Binarization
    threshold_method: Literal['simple', 'otsu', 'adaptive_mean', 'adaptive_gaussian'] = 'otsu'
    threshold_value: int = 127
    
    # Halftone
    use_halftone: bool = False
    lpi: int = 55
    halftone_angle: float = 45.0
    dot_shape: Literal['round', 'square', 'ellipse'] = 'round'
    
    # Export
    export_png: bool = True
    export_pdf: bool = True
    export_svg: bool = False
    create_zip: bool = True
    create_readme: bool = True
    
    # Advanced
    detail_level: Literal['high', 'medium', 'low'] = 'medium'
    verbose: bool = True


@dataclass
class UISettings:
    """UI/Display settings"""
    
    show_progress: bool = True
    colored_output: bool = True
    show_warnings: bool = True


# Default settings instance
DEFAULT_SETTINGS = ProcessingSettings()
