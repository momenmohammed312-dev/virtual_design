"""
Halftone Generator
Generate halftone patterns for gradients and photographs
"""

import cv2
import numpy as np
from typing import Literal

class HalftoneGenerator:
    """Generate halftone patterns for screen printing"""
    
    def __init__(self, dpi: int = 300):
        """
        Initialize halftone generator
        
        Args:
            dpi: Output DPI
        """
        self.dpi = dpi
    
    def generate(self,
                 image: np.ndarray,
                 lpi: int = 55,
                 angle: float = 45.0,
                 dot_shape: Literal['round', 'square', 'ellipse'] = 'round') -> np.ndarray:
        """
        Generate halftone pattern
        
        Args:
            image: Grayscale image
            lpi: Lines per inch (screen frequency)
            angle: Screen angle in degrees
            dot_shape: Shape of halftone dots
            
        Returns:
            Binary halftone image
        """
        print(f"      📊 Generating halftone (LPI: {lpi}, angle: {angle}°, shape: {dot_shape})...")
        
        # Ensure grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Calculate dot spacing in pixels
        dot_spacing = int(self.dpi / lpi)
        
        # Create halftone
        if dot_shape == 'round':
            halftone = self._generate_round_halftone(gray, dot_spacing, angle)
        elif dot_shape == 'square':
            halftone = self._generate_square_halftone(gray, dot_spacing, angle)
        elif dot_shape == 'ellipse':
            halftone = self._generate_ellipse_halftone(gray, dot_spacing, angle)
        else:
            raise ValueError(f"Unknown dot shape: {dot_shape}")
        
        print(f"         ✅ Halftone generated")
        return halftone
    
    def _generate_round_halftone(self, 
                                  gray: np.ndarray, 
                                  dot_spacing: int,
                                  angle: float) -> np.ndarray:
        """Generate round dot halftone"""
        h, w = gray.shape
        halftone = np.zeros((h, w), dtype=np.uint8)
        
        # Rotate coordinates
        angle_rad = np.radians(angle)
        cos_a = np.cos(angle_rad)
        sin_a = np.sin(angle_rad)
        
        # Generate dots
        for y in range(0, h, dot_spacing):
            for x in range(0, w, dot_spacing):
                # Get average intensity in this cell
                y_end = min(y + dot_spacing, h)
                x_end = min(x + dot_spacing, w)
                cell = gray[y:y_end, x:x_end]
                intensity = np.mean(cell)
                
                # Calculate dot radius (inverse: darker = bigger dot)
                radius = int((1 - intensity / 255) * (dot_spacing / 2))
                
                if radius > 0:
                    # Draw circle
                    center_x = x + dot_spacing // 2
                    center_y = y + dot_spacing // 2
                    cv2.circle(halftone, (center_x, center_y), radius, 255, -1)
        
        return halftone
    
    def _generate_square_halftone(self,
                                   gray: np.ndarray,
                                   dot_spacing: int,
                                   angle: float) -> np.ndarray:
        """Generate square dot halftone"""
        h, w = gray.shape
        halftone = np.zeros((h, w), dtype=np.uint8)
        
        for y in range(0, h, dot_spacing):
            for x in range(0, w, dot_spacing):
                y_end = min(y + dot_spacing, h)
                x_end = min(x + dot_spacing, w)
                cell = gray[y:y_end, x:x_end]
                intensity = np.mean(cell)
                
                # Calculate square size
                size = int((1 - intensity / 255) * dot_spacing)
                
                if size > 0:
                    center_x = x + dot_spacing // 2
                    center_y = y + dot_spacing // 2
                    half_size = size // 2
                    
                    cv2.rectangle(
                        halftone,
                        (center_x - half_size, center_y - half_size),
                        (center_x + half_size, center_y + half_size),
                        255,
                        -1
                    )
        
        return halftone
    
    def _generate_ellipse_halftone(self,
                                    gray: np.ndarray,
                                    dot_spacing: int,
                                    angle: float) -> np.ndarray:
        """Generate ellipse dot halftone"""
        h, w = gray.shape
        halftone = np.zeros((h, w), dtype=np.uint8)
        
        for y in range(0, h, dot_spacing):
            for x in range(0, w, dot_spacing):
                y_end = min(y + dot_spacing, h)
                x_end = min(x + dot_spacing, w)
                cell = gray[y:y_end, x:x_end]
                intensity = np.mean(cell)
                
                # Calculate ellipse size
                axis_size = int((1 - intensity / 255) * (dot_spacing / 2))
                
                if axis_size > 0:
                    center_x = x + dot_spacing // 2
                    center_y = y + dot_spacing // 2
                    
                    cv2.ellipse(
                        halftone,
                        (center_x, center_y),
                        (axis_size, int(axis_size * 0.7)),  # Ellipse ratio
                        angle,
                        0,
                        360,
                        255,
                        -1
                    )
        
        return halftone
    
    def floyd_steinberg_dithering(self, gray: np.ndarray) -> np.ndarray:
        """
        Apply Floyd-Steinberg error diffusion dithering
        
        Args:
            gray: Grayscale image
            
        Returns:
            Binary dithered image
        """
        print(f"      📊 Applying Floyd-Steinberg dithering...")
        
        # Work on a copy as float
        img = gray.astype(float)
        h, w = img.shape
        
        for y in range(h):
            for x in range(w):
                old_pixel = img[y, x]
                new_pixel = 255 if old_pixel > 127 else 0
                img[y, x] = new_pixel
                
                error = old_pixel - new_pixel
                
                # Distribute error to neighbors
                if x + 1 < w:
                    img[y, x + 1] += error * 7/16
                if y + 1 < h:
                    if x > 0:
                        img[y + 1, x - 1] += error * 3/16
                    img[y + 1, x] += error * 5/16
                    if x + 1 < w:
                        img[y + 1, x + 1] += error * 1/16
        
        print(f"         ✅ Dithering complete")
        return img.astype(np.uint8)
