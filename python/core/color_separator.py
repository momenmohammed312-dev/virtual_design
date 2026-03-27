"""
color_separator.py — Color Separation with LAB→RGB brightness sorting fix
Virtual Design Silk Screen Studio
FIXED: BUG D - LAB→RGB brightness calculation for correct color ordering
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class ColorSeparator:
    """
    Separate image into color layers using K-means clustering.
    FIXED: LAB→RGB brightness sorting for correct color layer ordering.
    """

    def separate(
        self,
        image: np.ndarray,
        num_colors: int = 4,
        use_lab: bool = True,
        max_iterations: int = 20,
        epsilon: float = 1.0,
        attempts: int = 3,
    ) -> Dict:
        """
        Separate image into specified number of color layers.

        Args:
            image: Input image (BGR format)
            num_colors: Number of colors to separate
            use_lab: Use LAB color space for better clustering
            max_iterations: Maximum K-means iterations
            epsilon: K-means convergence epsilon
            attempts: Number of K-means attempts (best result kept)

        Returns:
            Dictionary with separation results:
            - 'label_map': Array with pixel labels (0 to num_colors-1)
            - 'centers': Color centers (in original BGR format)
            - 'num_colors': Actual number of colors
            - 'labels': List of labels for each color (sorted by brightness)
            - 'color_masks': List of binary masks for each color
        """
        if len(image.shape) != 3 or image.shape[2] != 3:
            raise ValueError("Input image must be BGR format with 3 channels")

        h, w, _ = image.shape
        total_pixels = h * w

        logger.info(f"[ColorSeparator] Separating {num_colors} colors (use_lab={use_lab})")

        # Convert color space if needed
        if use_lab:
            # Convert BGR to LAB
            lab_image = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            data = lab_image.reshape((-1, 3)).astype(np.float32)
            color_space = "LAB"
        else:
            # Use BGR directly
            data = image.reshape((-1, 3)).astype(np.float32)
            color_space = "BGR"

        # Apply K-means clustering
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, max_iterations, epsilon)
        
        # Run K-means multiple times and keep best result
        best_compactness = float('inf')
        best_labels = None
        best_centers = None

        for attempt in range(attempts):
            try:
                compactness, labels, centers = cv2.kmeans(
                    data, num_colors, None, criteria, 1, cv2.KMEANS_PP_CENTERS
                )
                
                if compactness < best_compactness:
                    best_compactness = compactness
                    best_labels = labels
                    best_centers = centers
                    
            except Exception as e:
                logger.warning(f"[ColorSeparator] K-means attempt {attempt+1} failed: {e}")
                continue

        if best_labels is None:
            raise RuntimeError("K-means clustering failed on all attempts")

        # Reshape labels back to image dimensions
        label_map = best_labels.reshape((h, w))

        # FIXED: Convert centers back to BGR for consistent output
        if use_lab:
            # Convert LAB centers back to BGR
            centers_bgr = []
            for center in best_centers:
                # Convert single LAB value to BGR
                lab_pixel = np.array([[center]], dtype=np.uint8)
                bgr_pixel = cv2.cvtColor(lab_pixel, cv2.COLOR_LAB2BGR)[0][0]
                centers_bgr.append(bgr_pixel)
            centers_bgr = np.array(centers_bgr, dtype=np.float32)
        else:
            centers_bgr = best_centers.copy()

        # FIXED: Sort colors by brightness (convert LAB→RGB first, then calculate brightness)
        brightness = self._calculate_brightness(centers_bgr, use_lab)
        sorted_indices = np.argsort(brightness)
        
        # Reorder centers and labels by brightness
        sorted_centers = centers_bgr[sorted_indices]
        
        # Create mapping from old labels to new sorted labels
        label_mapping = {old_label: new_label for new_label, old_label in enumerate(sorted_indices)}
        
        # Apply mapping to label map
        sorted_label_map = np.vectorize(label_mapping.get)(label_map)

        # Generate color information
        color_info = []
        for i, (center, brightness_val) in enumerate(zip(sorted_centers, brightness[sorted_indices])):
            # Convert center to uint8 for display
            center_uint8 = np.clip(center, 0, 255).astype(np.uint8)
            
            # Calculate percentage of pixels
            pixel_count = np.sum(sorted_label_map == i)
            percentage = (pixel_count / total_pixels) * 100
            
            color_info.append({
                'index': i,
                'center_bgr': center_uint8.tolist(),
                'brightness': float(brightness_val),
                'pixel_count': int(pixel_count),
                'percentage': float(percentage)
            })

        # Generate binary masks for each color
        color_masks = []
        for i in range(num_colors):
            mask = (sorted_label_map == i).astype(np.uint8) * 255
            color_masks.append(mask)

        logger.info(f"[ColorSeparator] Separated {num_colors} colors in {color_space} space")
        for i, info in enumerate(color_info):
            logger.debug(f"  Color {i}: BGR={info['center_bgr']}, brightness={info['brightness']:.1f}, "
                         f"coverage={info['percentage']:.1f}%")

        return {
            'label_map': sorted_label_map,
            'centers': sorted_centers,
            'num_colors': num_colors,
            'labels': list(range(num_colors)),
            'color_info': color_info,
            'color_masks': color_masks,
            'compactness': float(best_compactness),
            'color_space': color_space
        }

    def _calculate_brightness(self, centers: np.ndarray, use_lab: bool) -> np.ndarray:
        """
        FIXED: Calculate brightness for color centers.
        For LAB: convert to RGB first, then calculate grayscale brightness.
        For BGR: calculate directly.
        
        Args:
            centers: Color centers (in BGR format)
            use_lab: Whether original clustering was in LAB space
            
        Returns:
            Array of brightness values for each center
        """
        brightness = []
        
        for i, center in enumerate(centers):
            if use_lab:
                # FIXED: Convert LAB center to RGB first, then calculate brightness
                center_uint8 = np.clip(center, 0, 255).astype(np.uint8)
                
                # Convert LAB to RGB (via BGR intermediate)
                lab_pixel = np.array([[center_uint8]], dtype=np.uint8)
                bgr_pixel = cv2.cvtColor(lab_pixel, cv2.COLOR_LAB2BGR)[0][0]
                
                # Convert BGR to RGB
                rgb_pixel = cv2.cvtColor(np.array([[bgr_pixel]], dtype=np.uint8), cv2.COLOR_BGR2RGB)[0][0]
                
                # Calculate brightness as mean of RGB values
                brightness_val = np.mean(rgb_pixel)
                
            else:
                # BGR space - calculate brightness directly
                center_uint8 = np.clip(center, 0, 255).astype(np.uint8)
                
                # Convert BGR to grayscale
                gray_val = cv2.cvtColor(np.array([[center_uint8]], dtype=np.uint8), cv2.COLOR_BGR2GRAY)[0][0]
                brightness_val = float(gray_val)
            
            brightness.append(brightness_val)
        
        return np.array(brightness)

    def create_color_layers(
        self,
        original_image: np.ndarray,
        separation_result: Dict,
        background_color: Tuple[int, int, int] = (255, 255, 255)
    ) -> List[np.ndarray]:
        """
        Create individual color layer images from separation result.
        
        Args:
            original_image: Original BGR image
            separation_result: Result from separate() method
            background_color: Background color for layers (BGR)
            
        Returns:
            List of color layer images
        """
        h, w, _ = original_image.shape
        num_colors = separation_result['num_colors']
        label_map = separation_result['label_map']
        centers = separation_result['centers']
        
        layers = []
        
        for i in range(num_colors):
            # Create layer with background
            layer = np.full((h, w, 3), background_color, dtype=np.uint8)
            
            # Get mask for this color
            mask = (label_map == i)
            
            # Apply color to masked regions
            color = np.clip(centers[i], 0, 255).astype(np.uint8)
            layer[mask] = color
            
            layers.append(layer)
        
        return layers

    def optimize_color_count(
        self,
        image: np.ndarray,
        max_colors: int = 8,
        min_colors: int = 2,
        use_lab: bool = True
    ) -> Tuple[int, Dict]:
        """
        Automatically determine optimal number of colors using elbow method.
        
        Args:
            image: Input image
            max_colors: Maximum number of colors to try
            min_colors: Minimum number of colors
            use_lab: Use LAB color space
            
        Returns:
            Tuple of (optimal_color_count, separation_result)
        """
        logger.info(f"[ColorSeparator] Optimizing color count ({min_colors}-{max_colors})")
        
        results = {}
        compactness_ratios = []
        
        # Test different color counts
        for k in range(min_colors, max_colors + 1):
            try:
                result = self.separate(image, k, use_lab)
                results[k] = result
                compactness_ratios.append(result['compactness'])
                
                logger.debug(f"  k={k}: compactness={result['compactness']:.0f}")
                
            except Exception as e:
                logger.warning(f"  k={k}: Failed - {e}")
                continue
        
        if not results:
            raise RuntimeError("Failed to separate image with any color count")
        
        # Find elbow point (largest drop in compactness ratio)
        if len(compactness_ratios) > 1:
            ratios = []
            for i in range(1, len(compactness_ratios)):
                if compactness_ratios[i-1] > 0:
                    ratio = (compactness_ratios[i-1] - compactness_ratios[i]) / compactness_ratios[i-1]
                    ratios.append(ratio)
                else:
                    ratios.append(0)
            
            if ratios:
                best_idx = np.argmax(ratios) + min_colors
                optimal_k = min(best_idx, max_colors)
            else:
                optimal_k = min_colors
        else:
            optimal_k = min_colors
        
        logger.info(f"[ColorSeparator] Optimal colors: {optimal_k}")
        
        return optimal_k, results.get(optimal_k, list(results.values())[0])

    def validate_separation(self, separation_result: Dict) -> Dict:
        """
        Validate separation result and return quality metrics.
        
        Args:
            separation_result: Result from separate() method
            
        Returns:
            Dictionary with validation metrics
        """
        num_colors = separation_result['num_colors']
        color_info = separation_result['color_info']
        compactness = separation_result['compactness']
        
        # Calculate quality metrics
        total_coverage = sum(info['percentage'] for info in color_info)
        avg_coverage = total_coverage / num_colors
        
        # Check for empty or dominant colors
        empty_colors = sum(1 for info in color_info if info['percentage'] < 1.0)
        dominant_colors = sum(1 for info in color_info if info['percentage'] > 80.0)
        
        # Calculate color separation quality (lower compactness is better)
        max_compactness = 1000000  # Arbitrary high value
        quality_score = max(0, 1 - (compactness / max_compactness))
        
        validation = {
            'num_colors': num_colors,
            'total_coverage': total_coverage,
            'avg_coverage': avg_coverage,
            'empty_colors': empty_colors,
            'dominant_colors': dominant_colors,
            'compactness': compactness,
            'quality_score': quality_score,
            'is_valid': (empty_colors == 0 and dominant_colors == 0)
        }
        
        logger.info(f"[ColorSeparator] Validation: quality={validation['quality_score']:.2f}, "
                   f"empty={empty_colors}, dominant={dominant_colors}")
        
        return validation
