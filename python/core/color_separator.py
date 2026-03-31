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

        # ── Global Background Pre-Filtering ──────────────────────────────────
        # FIXED: Use histogram mode instead of corner sampling (BUG-07)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Use histogram mode for robust background detection
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
        bg_luma = int(np.argmax(hist))  # Most frequent pixel = background
        bg_mask = np.abs(gray.astype(int) - bg_luma) < 15  # 15-luma tolerance
        
        if bg_luma > 200:
            logger.info(f"[ColorSeparator] Adaptive: Detected WHITE background (luma={bg_luma})")
        elif bg_luma < 50:
            logger.info(f"[ColorSeparator] Adaptive: Detected BLACK background (luma={bg_luma})")
        else:
            logger.info(f"[ColorSeparator] Adaptive: Detected GRAY background (luma={bg_luma})")
            
        fg_mask = ~bg_mask
        fg_pixel_count = int(np.sum(fg_mask))
        
        logger.info(f"[ColorSeparator] Separating {num_colors} colors (LAB={use_lab}, "
                    f"fg_pixels={fg_pixel_count}/{total_pixels} = "
                    f"{fg_pixel_count/total_pixels*100:.1f}%)")

        # Convert color space for clustering
        if use_lab:
            lab_image = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            full_data = lab_image.reshape((-1, 3)).astype(np.float32)
            color_space = "LAB"
        else:
            full_data = image.reshape((-1, 3)).astype(np.float32)
            color_space = "BGR"

        # Only cluster foreground pixels
        fg_flat = fg_mask.reshape(-1)
        if fg_pixel_count < 100:
            # Degenerate case: nearly all-white image — cluster everything
            logger.warning("[ColorSeparator] Too few foreground pixels, clustering all pixels")
            cluster_data = full_data
            using_fg_only = False
        else:
            cluster_data = full_data[fg_flat]
            using_fg_only = True

        # Apply K-means clustering
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, max_iterations, epsilon)

        # Seed for determinism: same image + same settings = same output every time.
        np.random.seed(42)
        cv2.setRNGSeed(42)

        # Run K-means multiple times and keep best result
        best_compactness = float('inf')
        best_labels = None
        best_centers = None

        for attempt in range(attempts):
            try:
                compactness, labels, centers = cv2.kmeans(
                    cluster_data, num_colors, None, criteria, 1, cv2.KMEANS_PP_CENTERS
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

        # TASK 15: SILHOUETTE VALIDATION & AUTO-RETRY
        # If separation quality is poor, try reducing K to find a more distinct clustering.
        best_compactness, best_labels, best_centers, num_colors = self._validate_and_retry_kmeans(
            cluster_data, num_colors, best_compactness, best_labels, best_centers, criteria
        )

        # Build full label map: assign every pixel to nearest center
        if using_fg_only:
            # Assign all full-resolution pixels to nearest center by Euclidean distance
            label_map_flat = np.zeros(total_pixels, dtype=np.int32)
            for k_idx in range(num_colors):
                # Distance from every pixel to center k
                diff = full_data - best_centers[k_idx].astype(np.float32)
                # Initialise with large value on first iteration
                if k_idx == 0:
                    min_dist = np.sum(diff ** 2, axis=1)
                    label_map_flat[:] = 0
                else:
                    dist = np.sum(diff ** 2, axis=1)
                    closer = dist < min_dist
                    min_dist = np.where(closer, dist, min_dist)
                    label_map_flat[closer] = k_idx

            label_map = label_map_flat.reshape((h, w)).astype(np.int32)
            # Mark white/background pixels as -1 (excluded from color layers)
            label_map[bg_mask] = -1
        else:
            label_map = best_labels.reshape((h, w)).astype(np.int32)

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
        # IMPORTANT: label_mapping only covers 0..K-1. Background pixels have label=-1.
        # Using lambda with default=-1 preserves background pixels correctly.
        # (np.vectorize(label_mapping.get) would return None for -1 → object array → crash)
        sorted_label_map = np.vectorize(lambda x: label_mapping.get(x, -1))(label_map)

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

        # Build 'colors' (RGB tuples) and 'color_names' expected by the rest of the pipeline
        # (step9_export, step2_5_underbase_creation, _save_color_info all use these keys).
        colors_rgb = []
        color_names = []
        for i, center in enumerate(sorted_centers):
            # sorted_centers are already in BGR format (converted back after LAB clustering)
            bgr = np.clip(center, 0, 255).astype(np.uint8)
            rgb_pixel = cv2.cvtColor(np.array([[bgr]], dtype=np.uint8), cv2.COLOR_BGR2RGB)[0][0]
            colors_rgb.append(tuple(int(x) for x in rgb_pixel))
            color_names.append(f"color_{i+1:02d}")

        # Optionally enrich color names with Pantone matches
        try:
            from core.pantone_library import PantoneLibrary
            pantone_lib = PantoneLibrary()
            color_names = []
            for rgb in colors_rgb:
                match = pantone_lib.find_nearest_pantone(rgb)
                color_names.append(match.name)
        except Exception:
            pass  # fallback names already set above

        return {
            'label_map': sorted_label_map,
            'centers': sorted_centers,
            'num_colors': num_colors,
            'labels': list(range(num_colors)),
            'color_info': color_info,
            'color_masks': color_masks,
            'compactness': float(best_compactness),
            'color_space': color_space,
            # Keys required by the rest of the pipeline:
            'colors': colors_rgb,           # List of RGB tuples, light→dark sorted
            'color_names': color_names,     # Pantone name or 'color_NN'
            'image': None,                  # Placeholder (image not stored to save memory)
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

    def get_color_hex(self, rgb: tuple) -> str:
        """Convert an RGB tuple to a hex string like #RRGGBB."""
        return f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"

    def get_color_info(self, separation_result: Dict) -> List[Dict]:
        """
        Return detailed per-color info for the UI / color_info.json.
        Works with both the new (color_info key) and old (colors+color_names keys) formats.
        """
        # Prefer the rich color_info list built during separate()
        if 'color_info' in separation_result:
            base = separation_result['color_info']
            colors = separation_result.get('colors', [])
            names  = separation_result.get('color_names', [])
            result = []
            for i, entry in enumerate(base):
                rgb = colors[i] if i < len(colors) else (0, 0, 0)
                name = names[i] if i < len(names) else f"color_{i+1:02d}"
                result.append({
                    'index': entry.get('index', i),
                    'name': name,
                    'rgb': rgb,
                    'hex': self.get_color_hex(rgb),
                    'pixel_count': entry.get('pixel_count', 0),
                    'percentage': round(entry.get('percentage', 0.0), 1),
                })
            return result

        # Fallback: build from colors + color_names + label_map
        label_map = separation_result.get('label_map')
        colors = separation_result.get('colors', [])
        names  = separation_result.get('color_names', [])
        total_pixels = label_map[label_map >= 0].size if label_map is not None else 1
        info = []
        for i, (color, name) in enumerate(zip(colors, names)):
            count = int(np.sum(label_map == i)) if label_map is not None else 0
            pct = (count / total_pixels * 100) if total_pixels > 0 else 0
            info.append({
                'index': i,
                'name': name,
                'rgb': color,
                'hex': self.get_color_hex(color),
                'pixel_count': count,
                'percentage': round(pct, 1),
            })
        info = [x for x in info if x['pixel_count'] > 0]
        info.sort(key=lambda x: x['pixel_count'], reverse=True)
        return info

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

    def _validate_and_retry_kmeans(
        self, 
        data: np.ndarray, 
        k: int, 
        best_comp: float, 
        best_lbls: np.ndarray, 
        best_cntrs: np.ndarray,
        criteria: Tuple
    ) -> Tuple[float, np.ndarray, np.ndarray, int]:
        """
        Computes silhouette-like quality score and retries with k-1 if poor.
        Returns: (compactness, labels, centers, k)
        """
        if k <= 2:
            return best_comp, best_lbls, best_cntrs, k
            
        # Calculate mean intra-cluster distance (Compactness / N)
        avg_intra = best_comp / data.shape[0]
        
        # Calculate mean inter-cluster distance (distance between centers)
        inter_dists = []
        for i in range(len(best_cntrs)):
            for j in range(i + 1, len(best_cntrs)):
                inter_dists.append(np.linalg.norm(best_cntrs[i] - best_cntrs[j]))
        avg_inter = np.mean(inter_dists) if inter_dists else 1.0
        
        # Quality Score (lower is better separation)
        quality_score = avg_intra / avg_inter
        logger.info(f"[ColorSeparator] Silhouette Score (k={k}): {quality_score:.3f}")
        
        # If score >= 0.5 (poor separation) and K > 2, try K-1
        if quality_score >= 0.5:
            logger.warning(f"[ColorSeparator] Poor separation (score={quality_score:.3f}). Retrying with k={k-1}...")
            try:
                comp_alt, lbls_alt, cntrs_alt = cv2.kmeans(
                    data, k - 1, None, criteria, 3, cv2.KMEANS_PP_CENTERS
                )
                
                # Check k-1 quality
                avg_intra_alt = comp_alt / data.shape[0]
                inter_dists_alt = []
                for i in range(len(cntrs_alt)):
                    for j in range(i + 1, len(cntrs_alt)):
                        inter_dists_alt.append(np.linalg.norm(cntrs_alt[i] - cntrs_alt[j]))
                avg_inter_alt = np.mean(inter_dists_alt) if inter_dists_alt else 1.0
                quality_score_alt = avg_intra_alt / avg_inter_alt
                
                logger.info(f"[ColorSeparator] Silhouette Score (k={k-1}): {quality_score_alt:.3f}")
                
                if quality_score_alt < quality_score:
                    logger.info(f"[ColorSeparator] Accepting k={k-1} results (improved from {quality_score:.3f} to {quality_score_alt:.3f})")
                    return comp_alt, lbls_alt, cntrs_alt, k - 1
                else:
                    logger.info(f"[ColorSeparator] Keeping k={k} results (k={k-1} was not better)")
            except Exception as e:
                logger.warning(f"[ColorSeparator] Retry k={k-1} failed: {e}")
        
        return best_comp, best_lbls, best_cntrs, k
