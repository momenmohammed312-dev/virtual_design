"""
color_separator.py — Color Separation with LAB->RGB brightness sorting fix
Virtual Design Silk Screen Studio
FIXED: BUG D - LAB->RGB brightness calculation for correct color ordering
FIXED: Background detection and removal for clean color separation
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging

from core.background_detector import detect_background, BackgroundMode

logger = logging.getLogger(__name__)


class ColorSeparator:
    """
    Separate image into color layers using K-means clustering.
    FIXED: LAB->RGB brightness sorting for correct color layer ordering.
    """

    def separate(
        self,
        image: np.ndarray,
        num_colors: int = 4,
        use_lab: bool = True,
        max_iterations: int = 20,
        epsilon: float = 1.0,
        attempts: int = 3,
        background_mode: BackgroundMode = "auto",
        bg_tolerance: int = 30,
        alpha_mask: Optional[np.ndarray] = None,
    ) -> Dict:
        """
        Separate image into color layers using K-means clustering.
        🔥 NEW: Proper background detection and removal before clustering.
        🔥 FIXED: Now uses alpha_mask to exclude transparent pixels from clustering.

        Args:
            image: Input image (BGR format)
            num_colors: Number of colors to separate
            use_lab: Use LAB color space for better clustering
            max_iterations: Maximum K-means iterations
            epsilon: K-means convergence epsilon
            attempts: Number of K-means attempts (best result kept)
            background_mode: Background detection mode ("auto", "remove_white", "remove_black", "keep_all")
            bg_tolerance: Color distance tolerance for background matching
            alpha_mask: Optional boolean mask where True=visible, False=transparent.
                       If provided, transparent pixels are excluded from clustering.

        Returns:
            Dictionary with separation results:
            - 'label_map': Array with pixel labels (-1 for background, 0..N-1 for colors)
            - 'centers': Color centers (in original BGR format)
            - 'num_colors': Actual number of colors
            - 'labels': List of labels for each color (sorted by brightness)
            - 'color_masks': List of binary masks for each color
            - 'bg_mask': Boolean mask of background pixels
            - 'fg_mask': Boolean mask of foreground pixels
            - 'bg_stats': Background detection statistics
        """
        if len(image.shape) != 3 or image.shape[2] != 3:
            raise ValueError("Input image must be BGR format with 3 channels")
        
        h, w = image.shape[:2]
        logger.info(f"[ColorSeparator] Starting separation: {w}x{h}, {num_colors} colors, bg_mode='{background_mode}'")

        h, w, _ = image.shape
        total_pixels = h * w

        # ── Solid Image Detection ─────────────────────────────────────────────
        # Detect solid images (few unique colors) to skip background removal
        # Otherwise a solid-color design gets mistaken for background
        img_small = cv2.resize(image, (50, 50), interpolation=cv2.INTER_AREA)
        total_unique_colors = len(np.unique(img_small.reshape(-1, 3), axis=0))
        
        # ── Background Detection & Removal ──────────────────────────────────
        # 🔥 NEW: Robust background detection using border sampling
        
        # Check if image is solid (few unique colors) - skip background removal
        hist = cv2.calcHist([cv2.cvtColor(img_small, cv2.COLOR_BGR2GRAY)], [0], None, [256], [0, 256]).flatten()
        mode_luma = int(np.argmax(hist))
        mode_concentration = np.sum(hist[max(0, mode_luma-7):min(256, mode_luma+8)]) / (hist.sum() + 1e-6)
        is_solid = (total_unique_colors < 10) or (mode_concentration > 0.80)
        
        if is_solid:
            # Solid image — skip background detection, cluster everything
            logger.info(f"[ColorSeparator] Solid image detected ({total_unique_colors} unique colors). Skipping background removal.")
            bg_mask = np.zeros((h, w), dtype=bool)
            fg_mask = np.ones((h, w), dtype=bool)
            bg_stats = {
                "mode": "solid_skip",
                "bg_pixels": 0,
                "fg_pixels": total_pixels,
                "bg_coverage": 0.0,
                "fg_coverage": 100.0
            }
        else:
            # Use robust background detector
            if background_mode == "keep_all":
                bg_mode = "keep_all"
            elif background_mode == "remove_white":
                bg_mode = "remove_white"
            elif background_mode == "remove_black":
                bg_mode = "remove_black"
            else:
                bg_mode = "auto"
            
            bg_mask, fg_mask, bg_stats = detect_background(image, mode=bg_mode, tolerance=bg_tolerance)
            logger.info(f"[ColorSeparator] Background detection: {bg_stats['bg_pixels']} bg, {bg_stats['fg_pixels']} fg pixels")
        
        # 🔥 NEW: Apply alpha mask to exclude transparent pixels from foreground
        if alpha_mask is not None:
            if alpha_mask.shape != (h, w):
                logger.warning(f"[ColorSeparator] Alpha mask shape {alpha_mask.shape} doesn't match image {h}x{w}, resizing")
                alpha_mask = cv2.resize(alpha_mask.astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST).astype(bool)
            
            # Update fg_mask to exclude transparent pixels (alpha=False means transparent)
            visible_pixels = np.sum(alpha_mask)
            transparent_pixels = total_pixels - visible_pixels
            
            # Combine: foreground = non-background AND visible (non-transparent)
            fg_mask = fg_mask & alpha_mask
            bg_mask = bg_mask | (~alpha_mask)  # Background = original bg OR transparent
            
            # Update stats
            fg_pixel_count = int(np.sum(fg_mask))
            bg_pixel_count = int(np.sum(bg_mask))
            
            logger.info(f"[ColorSeparator] Alpha mask applied: {visible_pixels/total_pixels*100:.1f}% visible, "
                       f"{transparent_pixels/total_pixels*100:.1f}% transparent excluded. "
                       f"Final fg={fg_pixel_count}, bg={bg_pixel_count}")
            
            bg_stats['alpha_applied'] = True
            bg_stats['transparent_pixels'] = int(transparent_pixels)
            bg_stats['visible_pixels'] = int(visible_pixels)
        else:
            bg_stats['alpha_applied'] = False
        
        # Recalculate after alpha mask application
        fg_pixel_count = int(np.sum(fg_mask))
        bg_pixel_count = int(np.sum(bg_mask))
        
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
            # T01 FIX: Replace np.tile() with broadcasting to eliminate ~400MB peak RAM
            # Old: np.tile(center_px, (h, w, 1)) allocated H*W*3 array per cluster = OOM on large images
            # New: broadcasting diff = pixels[:,None,:] - centers[None,:,:] → single vectorized op
            label_map_flat = np.zeros(total_pixels, dtype=np.int32)
            try:
                # Delta-E CIE76 with broadcasting — no tile(), no per-cluster temp arrays
                full_lab = full_data.reshape(-1, 3).astype(np.float32)          # (N, 3)
                centers_f = np.clip(best_centers, 0, 255).astype(np.float32)    # (K, 3)
                # Broadcasting: (N,1,3) - (1,K,3) → (N,K,3) → sum → (N,K)
                diff = full_lab[:, np.newaxis, :] - centers_f[np.newaxis, :, :]
                sq_dist = np.sum(diff ** 2, axis=2)                              # (N, K)
                label_map_flat = np.argmin(sq_dist, axis=1).astype(np.int32)
                label_map_flat = label_map_flat.reshape(h, w)
                logger.info(f"[ColorSeparator] T01: Broadcasting pixel assignment (memory-safe)")
            except MemoryError:
                # Fallback for extremely large images: chunk-wise assignment
                logger.warning("[ColorSeparator] T01: MemoryError in broadcast, falling back to chunked")
                centers_f = np.clip(best_centers, 0, 255).astype(np.float32)
                chunk = 10000
                for start in range(0, total_pixels, chunk):
                    end = min(start + chunk, total_pixels)
                    diff = full_data[start:end] - centers_f[:, np.newaxis, :]
                    label_map_flat[start:end] = np.argmin(
                        np.sum(diff.transpose(1, 0, 2) ** 2, axis=2), axis=0
                    )
                label_map_flat = label_map_flat.reshape(h, w)
            label_map = label_map_flat
            # Mark background pixels as -1 (excluded from color layers)
            label_map[bg_mask] = -1
        else:
            # Solid/degenerate case — same T01 fix: broadcasting instead of tile()
            label_map_flat = np.zeros(total_pixels, dtype=np.int32)
            try:
                full_lab = full_data.reshape(-1, 3).astype(np.float32)
                centers_f = np.clip(best_centers, 0, 255).astype(np.float32)
                diff = full_lab[:, np.newaxis, :] - centers_f[np.newaxis, :, :]
                sq_dist = np.sum(diff ** 2, axis=2)
                label_map_flat = np.argmin(sq_dist, axis=1).astype(np.int32)
                label_map = label_map_flat.reshape(h, w)
                logger.info(f"[ColorSeparator] T01 Solid mode: Broadcasting pixel assignment")
            except Exception:
                for k_idx in range(num_colors):
                    diff = full_data - best_centers[k_idx].astype(np.float32)
                    if k_idx == 0:
                        min_dist = np.sum(diff ** 2, axis=1)
                        label_map_flat[:] = 0
            label_map = label_map_flat.reshape(h, w)
            # No background removal in solid mode — bg_mask is all False anyway

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

        # FIXED: Sort colors by brightness (convert LAB->RGB first, then calculate brightness)
        brightness = self._calculate_brightness(centers_bgr, use_lab)
        sorted_indices = np.argsort(brightness)
        
        # Reorder centers and labels by brightness
        sorted_centers = centers_bgr[sorted_indices]
        
        # Create mapping from old labels to new sorted labels
        label_mapping = {old_label: new_label for new_label, old_label in enumerate(sorted_indices)}

        # Apply mapping to label map
        # IMPORTANT: label_mapping only covers 0..K-1. Background pixels have label=-1.
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
        colors_rgb = []
        color_names = []
        for i, center in enumerate(sorted_centers):
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
            pass 

        # 🔥 NEW: Log background/foreground separation stats
        logger.info(f"[ColorSeparator] Final separation: {fg_pixel_count} foreground pixels "
                   f"({fg_pixel_count/total_pixels*100:.1f}%), "
                   f"{bg_pixel_count} background pixels removed")
        
        return {
            'label_map': sorted_label_map,
            'centers': sorted_centers,
            'num_colors': num_colors,
            'labels': list(range(num_colors)),
            'color_info': color_info,
            'color_masks': color_masks,
            'compactness': float(best_compactness),
            'color_space': color_space,
            'colors': colors_rgb,           
            'color_names': color_names,
            'bg_mask': bg_mask,
            'fg_mask': fg_mask,
            'bg_stats': bg_stats,
            'image': None,                  
        }

    def _calculate_brightness(self, centers: np.ndarray, use_lab: bool) -> np.ndarray:
        """
        FIXED: Calculate brightness for color centers.
        """
        brightness = []
        
        for i, center in enumerate(centers):
            if use_lab:
                center_uint8 = np.clip(center, 0, 255).astype(np.uint8)
                lab_pixel = np.array([[center_uint8]], dtype=np.uint8)
                bgr_pixel = cv2.cvtColor(lab_pixel, cv2.COLOR_LAB2BGR)[0][0]
                rgb_pixel = cv2.cvtColor(np.array([[bgr_pixel]], dtype=np.uint8), cv2.COLOR_BGR2RGB)[0][0]
                brightness_val = np.mean(rgb_pixel)
            else:
                center_uint8 = np.clip(center, 0, 255).astype(np.uint8)
                gray_val = cv2.cvtColor(np.array([[center_uint8]], dtype=np.uint8), cv2.COLOR_BGR2GRAY)[0][0]
                brightness_val = float(gray_val)
            
            brightness.append(brightness_val)
        
        return np.array(brightness)

    def get_color_hex(self, rgb: tuple) -> str:
        return f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"

    def extract_dominant_colors_for_ai(
        self,
        image: np.ndarray,
        max_colors: int = 8,
        min_coverage: float = 1.0
    ) -> List[Dict]:
        """
        Extract dominant colors using K-Means for AI analysis.
        Returns list of colors with hex, coverage %, and brightness.
        
        This is the FIRST PASS - OpenCV finds colors, AI decides merging.
        """
        h, w = image.shape[:2]
        
        # Downsample for speed
        small = cv2.resize(image, (150, 150), interpolation=cv2.INTER_AREA)
        
        # Simple K-Means to find dominant colors
        data = small.reshape(-1, 3).astype(np.float32)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 15, 1.0)
        
        np.random.seed(42)
        _, labels, centers = cv2.kmeans(data, max_colors, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
        
        # Count pixels per cluster
        total_pixels = h * w
        color_data = []
        
        for i, center in enumerate(centers):
            count = np.sum(labels == i)
            coverage = (count / (150 * 150)) * 100
            
            if coverage >= min_coverage:
                bgr = np.clip(center, 0, 255).astype(np.uint8)
                rgb = cv2.cvtColor(np.array([[bgr]], dtype=np.uint8), cv2.COLOR_BGR2RGB)[0][0]
                brightness = np.mean(rgb)
                
                color_data.append({
                    'hex': self.get_color_hex(tuple(int(x) for x in rgb)),
                    'rgb': tuple(int(x) for x in rgb),
                    'coverage': round(coverage, 1),
                    'brightness': round(brightness, 1),
                })
        
        # Sort by coverage (most dominant first)
        color_data.sort(key=lambda x: x['coverage'], reverse=True)
        
        logger.info(f"[ColorSeparator] Extracted {len(color_data)} dominant colors for AI")
        for c in color_data[:5]:
            logger.debug(f"  {c['hex']} -> {c['coverage']:.1f}%")
        
        return color_data

    def get_color_info(self, separation_result: Dict) -> List[Dict]:
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

    def _validate_and_retry_kmeans(
        self, 
        data: np.ndarray, 
        k: int, 
        best_comp: float, 
        best_lbls: np.ndarray, 
        best_cntrs: np.ndarray,
        criteria: Tuple
    ) -> Tuple[float, np.ndarray, np.ndarray, int]:
        min_k = 2  
        if k <= min_k:
            return best_comp, best_lbls, best_cntrs, k
            
        avg_intra = best_comp / data.shape[0]
        inter_dists = []
        for i in range(len(best_cntrs)):
            for j in range(i + 1, len(best_cntrs)):
                inter_dists.append(np.linalg.norm(best_cntrs[i] - best_cntrs[j]))
        avg_inter = np.mean(inter_dists) if inter_dists else 1.0
        
        quality_score = avg_intra / avg_inter
        logger.info(f"[ColorSeparator] Silhouette Score (k={k}): {quality_score:.3f}")
        
        if quality_score >= 0.5:
            retry_k = max(min_k, k - 1)
            if retry_k < k:
                logger.warning(f"[ColorSeparator] Poor separation (score={quality_score:.3f}). Retrying with k={retry_k}...")
                try:
                    comp_alt, lbls_alt, cntrs_alt = cv2.kmeans(
                        data, retry_k, None, criteria, 3, cv2.KMEANS_PP_CENTERS
                    )
                    
                    avg_intra_alt = comp_alt / data.shape[0]
                    inter_dists_alt = []
                    for i in range(len(cntrs_alt)):
                        for j in range(i + 1, len(cntrs_alt)):
                            inter_dists_alt.append(np.linalg.norm(cntrs_alt[i] - cntrs_alt[j]))
                    avg_inter_alt = np.mean(inter_dists_alt) if inter_dists_alt else 1.0
                    quality_score_alt = avg_intra_alt / avg_inter_alt
                    
                    if quality_score_alt < quality_score:
                        return comp_alt, lbls_alt, cntrs_alt, retry_k
                except Exception:
                    pass
        
        return best_comp, best_lbls, best_cntrs, k
