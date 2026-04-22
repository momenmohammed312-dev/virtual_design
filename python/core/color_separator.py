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

# FIX GROUP 8.2: Module-level singleton for PantoneLibrary
try:
    from core.pantone_library import PantoneLibrary as _PL
    _PANTONE = _PL()
    logger.info("[ColorSeparator] PantoneLibrary singleton initialized")
except Exception as _e:
    _PANTONE = None
    logger.debug(f"[ColorSeparator] PantoneLibrary not available: {_e}")


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
        bg_tolerance: int = 20,  # FIX GROUP 1.3: Reduced from 30 to 20 for better precision
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
            - 'bg_mask': Boolean mask of background pixels
            - 'fg_mask': Boolean mask of foreground pixels
            - 'bg_stats': Background detection statistics
            Note: Use MaskGenerator.generate_masks() to create binary masks from label_map
        """
        if len(image.shape) != 3 or image.shape[2] != 3:
            raise ValueError("Input image must be BGR format with 3 channels")
        
        h, w = image.shape[:2]
        logger.info(f"[ColorSeparator] Starting separation: {w}x{h}, {num_colors} colors, bg_mode='{background_mode}'")
        total_pixels = h * w

        # ── FIX A-05: Replace thumbnail-based solid detection with full-resolution
        # border analysis.  The 50×50 downscale merged 1600 real pixels into one,
        # making complex multi-color artwork look solid and skipping background
        # removal — causing one KMeans cluster to be wasted on the white background.
        #
        # New approach: sample only the border pixels at native resolution.
        # Detect whether the artwork is "bleed" (extends to canvas edges) or has a
        # conventional bordered background, then choose the correct remove mode.
        border_samples = self._sample_border_colors(
            image, border_width=max(5, min(h, w) // 20)
        )
        if len(border_samples) > 0:
            border_mean_bgr = np.mean(border_samples, axis=0)
            is_white_background = np.all(border_mean_bgr > 230)
            is_black_background = np.all(border_mean_bgr < 25)

            # Bleed artwork: border has low lightness-variance AND non-neutral hue
            # (a dark-blue illustration extending to edges would match this)
            border_lab = cv2.cvtColor(
                border_samples.reshape(1, -1, 3), cv2.COLOR_BGR2LAB
            ).reshape(-1, 3).astype(np.float32)
            border_lightness_var = float(np.var(border_lab[:, 0]))
            border_ab_magnitude  = float(np.mean(np.abs(border_lab[:, 1:])))
            # Bleed if: consistent border colour (low variance) that is not
            # achromatic white/grey (ab channels are non-zero)
            is_bleed_artwork = border_lightness_var < 50 and border_ab_magnitude > 5
        else:
            is_white_background = True
            is_black_background = False
            is_bleed_artwork    = False

        logger.debug(
            f"[ColorSeparator] Border analysis: white={is_white_background}, "
            f"black={is_black_background}, bleed={is_bleed_artwork}"
        )

        # ── Background Detection & Removal ───────────────────────────────────
        if is_bleed_artwork:
            # Bleed artwork has design colour at the edges — border-based
            # background detection would misidentify the design as background.
            logger.info("[ColorSeparator] Bleed artwork detected — skipping background removal")
            bg_mask = np.zeros((h, w), dtype=bool)
            fg_mask = np.ones((h, w), dtype=bool)
            bg_stats = {
                "mode": "bleed_skip",
                "bg_pixels": 0,
                "fg_pixels": total_pixels,
                "bg_coverage": 0.0,
                "fg_coverage": 100.0,
            }
        else:
            if background_mode == "keep_all":
                bg_mode = "keep_all"
            elif background_mode == "remove_white":
                bg_mode = "remove_white"
            elif background_mode == "remove_black":
                bg_mode = "remove_black"
            elif is_white_background:
                bg_mode = "remove_white"
            elif is_black_background:
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

        # FIX: Downscale image BEFORE building label map to preserve edge quality
        # Memory safety: Process large images at reduced resolution
        max_safe_pixels = 2_000_000  # ~2MP limit
        original_h, original_w = h, w
        if total_pixels > max_safe_pixels:
            scale = np.sqrt(max_safe_pixels / total_pixels)
            new_h, new_w = int(h * scale), int(w * scale)
            logger.warning(f"[ColorSeparator] Image too large ({h}x{w}={total_pixels}px), downscaling to {new_h}x{new_w} BEFORE separation for memory safety")
            # Resize image data BEFORE building label map
            image_small = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
            # Re-extract foreground data at smaller size
            if use_lab:
                lab_small = cv2.cvtColor(image_small, cv2.COLOR_BGR2LAB)
                full_data = lab_small.reshape((-1, 3)).astype(np.float32)
            else:
                full_data = image_small.reshape((-1, 3)).astype(np.float32)
            # Resize masks
            bg_mask = cv2.resize(bg_mask.astype(np.uint8), (new_w, new_h), interpolation=cv2.INTER_NEAREST).astype(bool)
            fg_mask = cv2.resize(fg_mask.astype(np.uint8), (new_w, new_h), interpolation=cv2.INTER_NEAREST).astype(bool)
            h, w = new_h, new_w
            total_pixels = h * w
            fg_pixel_count = int(np.sum(fg_mask))
            logger.info(f"[ColorSeparator] Resized to {h}x{w}, fg_pixels={fg_pixel_count}")

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
                chunk_size = 5000  # Smaller chunks to avoid memory issues
                for start in range(0, total_pixels, chunk_size):
                    end = min(start + chunk_size, total_pixels)
                    chunk_data = full_data[start:end]  # (N, 3)
                    # CORRECT BROADCASTING: (N,1,3) - (1,K,3) -> (N,K,3)
                    diff = chunk_data[:, np.newaxis, :] - centers_f[np.newaxis, :, :]
                    dist = np.sum(diff ** 2, axis=2)  # (N, K)
                    labels = np.argmin(dist, axis=1)  # (N,)
                    label_map_flat[start:end] = labels
                    logger.debug(f"[ColorSeparator] T01: Processed chunk {start}-{end}/{total_pixels}")
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

        # Store original dimensions for mask generation (upscale back if needed)
        label_map_resized = (h != original_h or w != original_w)
        if label_map_resized:
            logger.info(f"[ColorSeparator] Label map at {h}x{w}, original was {original_h}x{original_w}")

        # Enforce minimum cluster coverage (<0.1% ink -> reassign to nearest cluster)
        valid_pixels = np.sum(label_map >= 0)
        for k_idx in range(num_colors):
            k_mask = (label_map == k_idx)
            count = np.sum(k_mask)
            pct = (count / max(1, valid_pixels)) * 100
            if 0 < pct < 0.1:
                logger.warning(f"[ColorSeparator] Cluster {k_idx} (<0.1% coverage: {pct:.3f}%) reassigned")
                other_indices = [i for i in range(num_colors) if i != k_idx and np.sum(label_map == i)/max(1, valid_pixels)*100 >= 0.1]
                if other_indices:
                    dists = np.sum((best_centers[other_indices] - best_centers[k_idx])**2, axis=1)
                    nearest_idx = other_indices[np.argmin(dists)]
                    label_map[k_mask] = nearest_idx

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

        # FIX GROUP 8.1: Replace np.vectorize with fast NumPy LUT approach
        # Build lookup table O(K) instead of O(N * dict_lookup)
        lut = np.full(num_colors, -1, dtype=np.int32)
        for old_lbl, new_lbl in label_mapping.items():
            if 0 <= old_lbl < num_colors:
                lut[old_lbl] = new_lbl
        # Apply via direct indexing (background=-1 → clamp then re-mask)
        tmp = np.where(label_map >= 0, label_map, 0)
        sorted_label_map = np.where(label_map >= 0, lut[tmp], -1).astype(np.int32)
        logger.info(f"[ColorSeparator] T08: Fast LUT label remapping applied (num_colors={num_colors})")

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

        # FIX GROUP 2.3: Removed redundant color_masks generation
        # Masks should ONLY be built by MaskGenerator.generate_masks() to avoid divergence
        # The label_map is the source of truth for mask generation

        logger.info(f"[ColorSeparator] Separated {num_colors} colors in {color_space} space")
        for i, info in enumerate(color_info):
            logger.debug(f"  Color {i}: BGR={info['center_bgr']}, brightness={info['brightness']:.1f}, "
                         f"coverage={info['percentage']:.1f}%")

        # 🔥 FIX: Exclude near-white background colors from results
        # Background colors (brightness > 235 or very close to white) should NOT be separate films
        background_brightness_threshold = 235  # Pixels brighter than this are considered background
        min_color_coverage_pct = 1.0  # Minimum 1% coverage to be a valid color
        
        logger.info(f"[ColorSeparator] 🔍 Background exclusion check: threshold={background_brightness_threshold}, min_coverage={min_color_coverage_pct}%")
        
        valid_colors = []
        valid_centers = []
        valid_labels = []
        
        logger.info(f"[ColorSeparator] 🔍 Checking {len(color_info)} colors for background exclusion:")
        for i, (center, info) in enumerate(zip(sorted_centers, color_info)):
            bgr = np.clip(center, 0, 255).astype(np.uint8)
            brightness = info['brightness']
            coverage_pct = info['percentage']
            
            # Debug: log every color being checked
            logger.warning(f"[ColorSeparator] 🔍 Color {i}: BGR={bgr.tolist()}, brightness={brightness:.1f}, coverage={coverage_pct:.2f}%")
            
            # Skip colors that are:
            # 1. Too bright (background-like) OR
            # 2. Have too little coverage (< 1%)
            is_background_like = brightness > background_brightness_threshold
            is_too_small = coverage_pct < min_color_coverage_pct
            
            if is_background_like:
                logger.warning(f"[ColorSeparator] ❌ EXCLUDING color {i}: brightness={brightness:.1f} > {background_brightness_threshold} (BACKGROUND-LIKE)")
                continue
            if is_too_small:
                logger.warning(f"[ColorSeparator] ❌ EXCLUDING color {i}: coverage={coverage_pct:.2f}% < {min_color_coverage_pct}% (TOO SMALL)")
                continue
            
            logger.warning(f"[ColorSeparator] ✅ KEEPING color {i}: brightness={brightness:.1f}, coverage={coverage_pct:.2f}%")
                
            rgb_pixel = cv2.cvtColor(np.array([[bgr]], dtype=np.uint8), cv2.COLOR_BGR2RGB)[0][0]
            valid_colors.append(tuple(int(x) for x in rgb_pixel))
            valid_centers.append(center)
            valid_labels.append(i)
        
        # Rebuild with only valid colors
        num_colors = len(valid_colors)
        colors_rgb = valid_colors
        sorted_centers = np.array(valid_centers) if valid_centers else np.array([])
        
        # Rebuild color_info with only valid colors
        color_info = [info for i, info in enumerate(color_info) 
                     if i in valid_labels]
        
        logger.info(f"[ColorSeparator] After background exclusion: {num_colors} valid colors (excluded {len(sorted_indices) - num_colors})")
        
        # 🔥 FIX: Remap label_map to exclude removed colors
        # Old labels that were removed should become background (-1)
        if num_colors > 0 and len(valid_labels) < len(sorted_indices):
            # Create remapping: old_label -> new_label or -1 if excluded
            old_to_new = {}
            for new_idx, old_idx in enumerate(valid_labels):
                old_to_new[old_idx] = new_idx
            
            # Apply remapping to label_map
            # Pixels with excluded labels become -1 (background)
            remapped = np.full_like(sorted_label_map, -1)
            for old_idx, new_idx in old_to_new.items():
                remapped[sorted_label_map == old_idx] = new_idx
            sorted_label_map = remapped
            
            logger.info(f"[ColorSeparator] Label map remapped: {len(old_to_new)} valid labels, rest set to background")
        elif num_colors == 0:
            # All colors were background - keep only foreground mask
            logger.warning("[ColorSeparator] All colors were background-like! Keeping original image as single layer.")
            sorted_label_map = np.full_like(sorted_label_map, 0)  # Single color layer
            num_colors = 1
            # Use average color of non-background pixels
            if np.any(fg_mask):
                avg_color = np.mean(image[fg_mask], axis=0)
                colors_rgb = [tuple(int(x) for x in cv2.cvtColor(np.array([[avg_color]], dtype=np.uint8), cv2.COLOR_BGR2RGB)[0][0])]
                sorted_centers = np.array([avg_color])
            else:
                colors_rgb = [(128, 128, 128)]  # Gray fallback
                sorted_centers = np.array([[128, 128, 128]], dtype=np.float32)
        
        # Build 'color_names' expected by the rest of the pipeline
        color_names = []
        for i in range(num_colors):
            color_names.append(f"color_{i+1:02d}")

        # FIX GROUP 8.2: Use singleton PantoneLibrary instead of instantiating
        if _PANTONE is not None:
            try:
                color_names = []
                for rgb in colors_rgb:
                    match = _PANTONE.find_nearest_pantone(rgb)
                    color_names.append(match.name)
                logger.info(f"[ColorSeparator] Enriched {len(color_names)} colors with Pantone names")
            except Exception as _e:
                logger.debug(f"[ColorSeparator] Pantone matching failed: {_e}") 

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
            # FIX GROUP 2.3: Removed 'color_masks' - use MaskGenerator.generate_masks() instead
            'compactness': float(best_compactness),
            'color_space': color_space,
            'colors': colors_rgb,
            'color_names': color_names,
            'bg_mask': bg_mask,
            'fg_mask': fg_mask,
            'bg_stats': bg_stats,
            'image': None,
            # NEW: Store original dimensions for proper scaling in export
            'original_dimensions': {'width': original_w, 'height': original_h},
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
        """
        FIX A-06: Use proper sklearn silhouette_score instead of the custom
        intra/inter centroid ratio which was inverting the threshold
        (retrying good separations, keeping poor ones).

        Silhouette score range: [-1, 1]
          > 0.5  = good separation  → keep
          < 0.25 = poor separation  → retry with k-1
          0.25-0.5 = acceptable     → keep

        Uses a sample of up to 5000 points for O(N²) silhouette efficiency.
        """
        min_k = 2
        if k <= min_k:
            return best_comp, best_lbls, best_cntrs, k

        # Sample for silhouette (O(N²) otherwise)
        n_sample = min(5000, len(data))
        idx = np.random.choice(len(data), n_sample, replace=False)
        sample_data   = data[idx]
        sample_labels = best_lbls.flatten()[idx]

        # Need at least 2 distinct labels in the sample
        if len(np.unique(sample_labels)) < 2:
            return best_comp, best_lbls, best_cntrs, k

        try:
            from sklearn.metrics import silhouette_score
            sil_score = silhouette_score(sample_data, sample_labels, metric='euclidean')
        except Exception as e:
            logger.debug(f"[ColorSeparator] silhouette_score unavailable: {e}")
            return best_comp, best_lbls, best_cntrs, k

        logger.info(f"[ColorSeparator] Silhouette score (k={k}): {sil_score:.3f}")

        # FIX A-06: Retry ONLY on genuinely poor separations (score < 0.25).
        # The old code fired when score >= 0.5, which is the opposite —
        # it was merging well-separated clusters!
        if sil_score < 0.25 and k > min_k:
            retry_k = k - 1
            logger.warning(
                f"[ColorSeparator] Poor silhouette ({sil_score:.3f}), "
                f"retrying with k={retry_k}"
            )
            try:
                comp_alt, lbls_alt, cntrs_alt = cv2.kmeans(
                    data, retry_k, None, criteria, 3, cv2.KMEANS_PP_CENTERS
                )
                sample_labels_alt = lbls_alt.flatten()[idx]
                if len(np.unique(sample_labels_alt)) >= 2:
                    sil_alt = silhouette_score(
                        sample_data, sample_labels_alt, metric='euclidean'
                    )
                    if sil_alt > sil_score:
                        logger.info(
                            f"[ColorSeparator] Improved silhouette with k={retry_k}: "
                            f"{sil_alt:.3f} > {sil_score:.3f}"
                        )
                        return comp_alt, lbls_alt, cntrs_alt, retry_k
            except Exception:
                pass

        return best_comp, best_lbls, best_cntrs, k

    def _sample_border_colors(self, image: np.ndarray, border_width: int = 5) -> np.ndarray:
        """
        Sample colors from image borders for background analysis.
        
        Args:
            image: Input BGR image
            border_width: Width of border strip to sample
            
        Returns:
            Array of border pixel colors (N x 3)
        """
        h, w = image.shape[:2]
        samples = []
        
        # Sample corners (more weight to corners as they often show background)
        corner_size = min(h, w) // 10  # 10% of smaller dimension
        
        corners = [
            image[:corner_size, :corner_size],  # Top-left
            image[:corner_size, -corner_size:],  # Top-right
            image[-corner_size:, :corner_size],  # Bottom-left
            image[-corner_size:, -corner_size:]  # Bottom-right
        ]
        
        for corner in corners:
            samples.extend(corner.reshape(-1, 3))
        
        # Sample edges
        edge_strip = border_width
        top_edge = image[:edge_strip, :].reshape(-1, 3)
        bottom_edge = image[-edge_strip:, :].reshape(-1, 3)
        left_edge = image[:, :edge_strip].reshape(-1, 3)
        right_edge = image[:, -edge_strip:].reshape(-1, 3)
        
        samples.extend(top_edge)
        samples.extend(bottom_edge)
        samples.extend(left_edge)
        samples.extend(right_edge)
        
        return np.array(samples, dtype=np.uint8)
