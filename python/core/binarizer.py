"""
Image Binarizer
Convert grayscale masks to pure black and white (1-bit)
"""

import cv2
import numpy as np
from typing import Tuple

class Binarizer:
    """Convert images to binary (black and white only)"""
    
    def __init__(self):
        self.threshold_methods = {
            'simple': cv2.THRESH_BINARY,
            'otsu': cv2.THRESH_BINARY + cv2.THRESH_OTSU,
            'adaptive_mean': cv2.ADAPTIVE_THRESH_MEAN_C,
            'adaptive_gaussian': cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        }
    
    def binarize(self, 
                 image: np.ndarray, 
                 method: str = 'otsu',
                 threshold: int = 127,
                 invert: bool = False) -> np.ndarray:
        """
        Convert image to binary (black and white)
        
        Args:
            image: Grayscale image
            method: Thresholding method ('simple', 'otsu', 'adaptive_mean', 'adaptive_gaussian')
            threshold: Threshold value for 'simple' method
            invert: Invert black and white
            
        Returns:
            Binary image (0 or 255)
        """
        # Ensure grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Apply thresholding
        if method == 'simple':
            _, binary = cv2.threshold(
                gray, 
                threshold, 
                255, 
                self.threshold_methods['simple']
            )
        
        elif method == 'otsu':
            # Otsu's method automatically finds optimal threshold
            _, binary = cv2.threshold(
                gray, 
                0, 
                255, 
                self.threshold_methods['otsu']
            )
        
        elif method == 'adaptive_mean':
            binary = cv2.adaptiveThreshold(
                gray,
                255,
                cv2.ADAPTIVE_THRESH_MEAN_C,
                cv2.THRESH_BINARY,
                11,  # Block size
                2    # C constant
            )
        
        elif method == 'adaptive_gaussian':
            binary = cv2.adaptiveThreshold(
                gray,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                11,  # Block size
                2    # C constant
            )
        
        else:
            raise ValueError(f"Unknown method: {method}")
        
        # Invert if needed
        if invert:
            binary = cv2.bitwise_not(binary)
        
        return binary
    
    def auto_binarize(self, image: np.ndarray) -> Tuple[np.ndarray, str, int]:
        """
        Automatically choose best binarization method
        
        Args:
            image: Grayscale image
            
        Returns:
            tuple: (binary_image, method_used, threshold_value)
        """
        # Ensure grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Try Otsu's method first
        threshold_value, binary = cv2.threshold(
            gray, 
            0, 
            255, 
            cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        
        # Check if result is good (not too much black or white)
        white_percentage = (np.sum(binary == 255) / binary.size) * 100
        
        if 10 < white_percentage < 90:
            # Good balance
            return binary, 'otsu', int(threshold_value)
        else:
            # Use adaptive threshold
            binary = cv2.adaptiveThreshold(
                gray,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                11,
                2
            )
            return binary, 'adaptive_gaussian', 0
    
    def remove_noise(self, 
                     binary: np.ndarray, 
                     kernel_size: int = 3) -> np.ndarray:
        """
        Remove noise from binary image
        
        Args:
            binary: Binary image
            kernel_size: Morphological kernel size
            
        Returns:
            Cleaned binary image
        """
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, 
            (kernel_size, kernel_size)
        )
        
        # Opening to remove small white noise
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        
        # Closing to fill small black holes
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel)
        
        return cleaned
