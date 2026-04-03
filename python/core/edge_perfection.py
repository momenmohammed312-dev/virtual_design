"""
Edge Perfection Module - Photoshop RIP-level quality
Advanced edge processing for professional print output
"""

import cv2
import numpy as np
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class EdgePerfectionProcessor:
    """Professional edge processing for RIP-quality output"""
    
    def __init__(self, dpi: int = 300):
        self.dpi = dpi
        # Calculate minimum printable line width (0.1mm industry standard)
        self.min_line_width_px = max(1, int(dpi * 0.1 / 25.4))
        
    def enhance_edges_for_vectorization(self, image: np.ndarray, 
                                    image_class: str = "auto") -> np.ndarray:
        """
        Enhance edges to Photoshop RIP quality before vectorization
        
        This combines multiple professional techniques:
        1. Adaptive contrast enhancement
        2. Multi-scale edge detection  
        3. Morphological optimization
        4. Anti-aliasing control
        """
        
        logger.info(f"Enhancing edges for {image_class} at {self.dpi} DPI")
        
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Step 1: Adaptive contrast enhancement
        enhanced = self._adaptive_contrast_enhancement(gray, image_class)
        
        # Step 2: Multi-scale edge detection
        edges = self._multiscale_edge_detection(enhanced, image_class)
        
        # Step 3: Morphological optimization
        optimized = self._morphological_optimization(edges, image_class)
        
        # Step 4: Final edge refinement
        final_edges = self._edge_refinement(optimized, image_class)
        
        logger.info("Edge enhancement completed")
        return final_edges
    
    def _adaptive_contrast_enhancement(self, gray: np.ndarray, 
                                   image_class: str) -> np.ndarray:
        """Adaptive contrast enhancement based on image type"""
        
        if image_class == "text_logo":
            # Strong contrast for sharp text
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            
            # Additional local contrast
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            local_contrast = cv2.morphologyEx(enhanced, cv2.MORPH_TOPHAT, kernel)
            enhanced = cv2.add(enhanced, local_contrast)
            
        elif image_class == "artwork":
            # Moderate contrast for artwork
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(16, 16))
            enhanced = clahe.apply(gray)
            
        else:  # photo or auto
            # Gentle contrast for photos
            clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(32, 32))
            enhanced = clahe.apply(gray)
        
        return enhanced
    
    def _multiscale_edge_detection(self, enhanced: np.ndarray, 
                                image_class: str) -> np.ndarray:
        """Multi-scale edge detection for optimal edge capture"""
        
        edges_list = []
        
        # Multiple scales for different edge sizes
        scales = [1, 2, 4] if image_class == "text_logo" else [1, 2]
        
        for scale in scales:
            # Gaussian blur at this scale
            ksize = scale * 2 + 1
            blurred = cv2.GaussianBlur(enhanced, (ksize, ksize), scale)
            
            # Canny edge detection with adaptive thresholds
            median_val = np.median(blurred)
            lower = int(max(0, 0.7 * median_val))
            upper = int(min(255, 1.3 * median_val))
            
            edges = cv2.Canny(blurred, lower, upper)
            edges_list.append(edges)
        
        # Combine edges from all scales
        if len(edges_list) > 1:
            combined_edges = np.zeros_like(edges_list[0])
            for edges in edges_list:
                combined_edges = cv2.bitwise_or(combined_edges, edges)
        else:
            combined_edges = edges_list[0]
        
        return combined_edges
    
    def _morphological_optimization(self, edges: np.ndarray, 
                                image_class: str) -> np.ndarray:
        """Morphological operations to optimize edge quality"""
        
        if image_class == "text_logo":
            # Aggressive cleanup for sharp text
            # Remove small noise
            kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
            cleaned = cv2.morphologyEx(edges, cv2.MORPH_OPEN, kernel_small)
            
            # Connect close edges
            kernel_connect = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            connected = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel_connect)
            
            # Thinning for precise edges
            thinned = cv2.ximgproc.thinning(connected)
            
        elif image_class == "artwork":
            # Moderate optimization for artwork
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            cleaned = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
            thinned = cv2.ximgproc.thinning(cleaned)
            
        else:  # photo or auto
            # Gentle optimization for photos
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
            cleaned = cv2.morphologyEx(edges, cv2.MORPH_OPEN, kernel)
            thinned = cleaned
        
        return thinned
    
    def _edge_refinement(self, edges: np.ndarray, 
                       image_class: str) -> np.ndarray:
        """Final edge refinement for vectorization"""
        
        # Ensure minimum line width
        if self.min_line_width_px > 1:
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, 
                                           (self.min_line_width_px, self.min_line_width_px))
            edges = cv2.morphologyEx(edges, cv2.MORPH_DILATE, kernel)
        
        # Remove isolated pixels (noise)
        kernel_noise = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        connectivity = 8
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(edges, connectivity, cv2.CV_32S)
        
        # Remove small components (noise)
        min_area = 5  # Minimum area in pixels
        cleaned_edges = np.zeros_like(edges)
        
        for i in range(1, num_labels):  # Skip background (0)
            if stats[i, cv2.CC_STAT_AREA] >= min_area:
                cleaned_edges[labels == i] = 255
        
        return cleaned_edges
    
    def optimize_for_halftone(self, image: np.ndarray) -> np.ndarray:
        """Specialized optimization for halftone generation"""
        
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Gaussian blur for smooth gradients (important for halftone)
        blur_sigma = 0.8  # Optimized for halftone dot formation
        blurred = cv2.GaussianBlur(gray, (0, 0), blur_sigma)
        
        # Contrast enhancement for better dot definition
        clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(32, 32))
        enhanced = clahe.apply(blurred)
        
        return enhanced
    
    def validate_edge_quality(self, original: np.ndarray, 
                          processed: np.ndarray) -> dict:
        """Validate edge quality improvement"""
        
        # Calculate edge density
        edge_density = np.sum(processed > 0) / processed.size
        
        # Calculate edge continuity (fewer breaks is better)
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
            processed, 8, cv2.CV_32S)
        
        # Average component size (larger is better for continuity)
        if num_labels > 1:
            avg_component_size = np.mean(stats[1:, cv2.CC_STAT_AREA])
        else:
            avg_component_size = 0
        
        # Edge sharpness (gradient magnitude)
        if len(original.shape) == 3:
            gray_orig = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
        else:
            gray_orig = original
            
        grad_x = cv2.Sobel(gray_orig, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray_orig, cv2.CV_64F, 0, 1, ksize=3)
        gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
        avg_sharpness = np.mean(gradient_magnitude)
        
        return {
            'edge_density': edge_density,
            'num_components': num_labels - 1,  # Exclude background
            'avg_component_size': avg_component_size,
            'avg_sharpness': avg_sharpness,
            'quality_score': self._calculate_quality_score(
                edge_density, avg_component_size, avg_sharpness)
        }
    
    def _calculate_quality_score(self, edge_density: float, 
                              avg_component_size: float, 
                              avg_sharpness: float) -> float:
        """Calculate overall edge quality score"""
        
        # Normalize metrics (0-1 range)
        density_score = min(1.0, edge_density * 10)  # Target: ~10% edge density
        size_score = min(1.0, avg_component_size / 100)  # Target: ~100px components
        sharpness_score = min(1.0, avg_sharpness / 50)  # Target: ~50 gradient magnitude
        
        # Weighted combination
        quality_score = (density_score * 0.3 + 
                        size_score * 0.4 + 
                        sharpness_score * 0.3)
        
        return quality_score


def enhance_image_for_vectorization(image: np.ndarray, 
                                 image_class: str = "auto",
                                 dpi: int = 300) -> np.ndarray:
    """
    Public interface for edge enhancement
    
    Args:
        image: Input image (grayscale or BGR)
        image_class: Type of image ("text_logo", "artwork", "photo", "auto")
        dpi: Output DPI for calculations
        
    Returns:
        Enhanced image optimized for vectorization
    """
    processor = EdgePerfectionProcessor(dpi)
    return processor.enhance_edges_for_vectorization(image, image_class)


def optimize_for_halftone_generation(image: np.ndarray, 
                                  dpi: int = 300) -> np.ndarray:
    """
    Public interface for halftone optimization
    
    Args:
        image: Input image (grayscale or BGR)
        dpi: Output DPI for calculations
        
    Returns:
        Optimized image for halftone generation
    """
    processor = EdgePerfectionProcessor(dpi)
    return processor.optimize_for_halftone(image)
