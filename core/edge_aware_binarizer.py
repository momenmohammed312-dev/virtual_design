"""
edge_aware_binarizer.py - Phase 2: Edge-aware binarization for ARTWORK
Implements Sauvola/Niblack thresholding with edge preservation
Production-grade binarization for screen printing workflows
"""

import cv2
import numpy as np
from typing import Tuple, Optional, Literal
from dataclasses import dataclass


@dataclass
class EdgeAwareConfig:
    """Configuration for edge-aware binarization."""
    method: Literal["sauvola", "niblack", "guided"] = "sauvola"
    window_size: int = 51          # Local window size (odd number)
    k: float = 0.34               # Threshold parameter (Sauvola: 0.2-0.5)
    r: float = 128.0              # Dynamic range parameter (Niblack)
    edge_preserve: bool = True     # Enable edge preservation
    edge_threshold: float = 0.1   # Edge strength threshold (0-1)
    min_area: int = 5             # Minimum component area to keep


class EdgeAwareBinarizer:
    """
    Production-grade edge-aware binarization.
    Implements RIP-level thresholding with edge preservation.
    """

    def __init__(self, config: Optional[EdgeAwareConfig] = None):
        self.config = config or EdgeAwareConfig()

    def binarize(self, image: np.ndarray) -> np.ndarray:
        """
        Apply edge-aware binarization to input image.
        
        Args:
            image: Input grayscale image (uint8)
            
        Returns:
            Binary image (uint8, 0=ink, 255=background)
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Normalize to 0-255 range
        if gray.dtype != np.uint8:
            gray = np.clip(gray * 255, 0, 255).astype(np.uint8)

        # Apply selected thresholding method
        if self.config.method == "sauvola":
            binary = self._sauvola_threshold(gray)
        elif self.config.method == "niblack":
            binary = self._niblack_threshold(gray)
        elif self.config.method == "guided":
            binary = self._guided_threshold(gray)
        else:
            # Fallback to Otsu
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Apply edge preservation if enabled
        if self.config.edge_preserve:
            binary = self._preserve_edges(gray, binary)

        # Clean small noise
        binary = self._remove_noise(binary)

        return binary

    def _sauvola_threshold(self, gray: np.ndarray) -> np.ndarray:
        """
        Sauvola thresholding - excellent for document and artwork.
        T(x,y) = mean(x,y) * [1 + k * ((std(x,y) / R) - 1)]
        
        Where k=0.34, R=128 (dynamic range)
        """
        # Calculate local mean and standard deviation
        mean = cv2.boxFilter(gray.astype(np.float32), -1, 
                           (self.config.window_size, self.config.window_size))
        
        # Calculate local variance
        squared = cv2.boxFilter((gray.astype(np.float32))**2, -1,
                              (self.config.window_size, self.config.window_size))
        variance = squared - mean**2
        std = np.sqrt(np.maximum(variance, 0))

        # Sauvola formula
        R = self.config.r
        k = self.config.k
        
        # Dynamic threshold map
        threshold = mean * (1 + k * ((std / R) - 1))
        
        # Apply threshold
        binary = np.where(gray.astype(np.float32) > threshold, 255, 0).astype(np.uint8)
        
        return binary

    def _niblack_threshold(self, gray: np.ndarray) -> np.ndarray:
        """
        Niblack thresholding - good for uneven lighting.
        T(x,y) = mean(x,y) + k * std(x,y)
        """
        # Calculate local mean and standard deviation
        mean = cv2.boxFilter(gray.astype(np.float32), -1,
                           (self.config.window_size, self.config.window_size))
        
        squared = cv2.boxFilter((gray.astype(np.float32))**2, -1,
                              (self.config.window_size, self.config.window_size))
        variance = squared - mean**2
        std = np.sqrt(np.maximum(variance, 0))

        # Niblack formula
        k = self.config.k
        threshold = mean + k * std
        
        # Apply threshold
        binary = np.where(gray.astype(np.float32) > threshold, 255, 0).astype(np.uint8)
        
        return binary

    def _guided_threshold(self, gray: np.ndarray) -> np.ndarray:
        """
        Guided threshold - combines global and local thresholding.
        Uses edge information to guide local thresholding.
        """
        # Get edge map
        edges = cv2.Canny(gray, 50, 150)
        edges_dilated = cv2.dilate(edges, np.ones((3,3), np.uint8), iterations=1)
        
        # Global threshold (Otsu)
        _, global_binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Local threshold (Sauvola)
        local_binary = self._sauvola_threshold(gray)
        
        # Guided fusion: use local near edges, global elsewhere
        guided_binary = np.where(edges_dilated > 0, local_binary, global_binary)
        
        return guided_binary

    def _preserve_edges(self, gray: np.ndarray, binary: np.ndarray) -> np.ndarray:
        """
        Edge preservation using gradient masking.
        Prevents edge bleeding and maintains sharp transitions.
        """
        # Calculate gradient magnitude
        grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
        
        # Normalize gradient to 0-1
        gradient_norm = gradient_magnitude / gradient_magnitude.max()
        
        # Create edge mask
        edge_mask = (gradient_norm > self.config.edge_threshold).astype(np.uint8) * 255
        
        # Apply morphological operations to strengthen edges
        kernel = np.ones((3,3), np.uint8)
        edge_mask = cv2.morphologyEx(edge_mask, cv2.MORPH_CLOSE, kernel)
        
        # Preserve edges in binary image
        # Where edges exist, ensure binary maintains original contrast
        edge_preserved = binary.copy()
        
        # Find edge regions
        edge_regions = (edge_mask > 0)
        
        # In edge regions, use adaptive threshold to preserve detail
        if np.any(edge_regions):
            # Apply adaptive threshold only to edge regions
            adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                           cv2.THRESH_BINARY, 11, 2)
            edge_preserved[edge_regions] = adaptive[edge_regions]
        
        return edge_preserved

    def _remove_noise(self, binary: np.ndarray) -> np.ndarray:
        """
        Remove small noise components while preserving structure.
        """
        if self.config.min_area <= 0:
            return binary
        
        # Find connected components
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
            binary, 8, cv2.CV_32S)
        
        # Create clean output
        clean = np.full_like(binary, 255)  # Start with white background
        
        # Keep only components above minimum area
        for label in range(1, num_labels):
            area = stats[label, cv2.CC_STAT_AREA]
            if area >= self.config.min_area:
                clean[labels == label] = 0  # Keep as ink
        
        return clean

    def get_quality_metrics(self, gray: np.ndarray, binary: np.ndarray) -> dict:
        """
        Calculate quality metrics for binarization evaluation.
        """
        # Edge preservation metric
        grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        grad_magnitude = np.sqrt(grad_x**2 + grad_y**2)
        
        grad_x_bin = cv2.Sobel(binary, cv2.CV_64F, 1, 0, ksize=3)
        grad_y_bin = cv2.Sobel(binary, cv2.CV_64F, 0, 1, ksize=3)
        grad_magnitude_bin = np.sqrt(grad_x_bin**2 + grad_y_bin**2)
        
        # Edge preservation score (higher is better)
        edge_score = np.corrcoef(grad_magnitude.flatten(), grad_magnitude_bin.flatten())[0,1]
        edge_score = max(0, edge_score) if not np.isnan(edge_score) else 0
        
        # Noise reduction metric
        num_labels, _, stats, _ = cv2.connectedComponentsWithStats(binary, 8, cv2.CV_32S)
        small_components = sum(1 for i in range(1, num_labels) 
                              if stats[i, cv2.CC_STAT_AREA] < self.config.min_area)
        
        noise_score = 1.0 - (small_components / max(1, num_labels - 1))
        
        return {
            "edge_preservation": edge_score,
            "noise_reduction": noise_score,
            "method": self.config.method,
            "components": num_labels - 1,  # Exclude background
            "small_components": small_components
        }


# Convenience function for quick usage
def binarize_artwork(image: np.ndarray, 
                    method: str = "sauvola",
                    edge_preserve: bool = True) -> np.ndarray:
    """
    Quick binarization function for artwork processing.
    
    Args:
        image: Input image (grayscale or color)
        method: Thresholding method ("sauvola", "niblack", "guided")
        edge_preserve: Enable edge preservation
        
    Returns:
        Binary image optimized for screen printing
    """
    config = EdgeAwareConfig(
        method=method,
        edge_preserve=edge_preserve,
        k=0.34 if method == "sauvola" else 0.2,  # Optimal per method
        window_size=51
    )
    
    binarizer = EdgeAwareBinarizer(config)
    return binarizer.binarize(image)
