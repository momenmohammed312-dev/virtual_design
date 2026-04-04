"""
pipeline_router.py — Specialized Pipeline Routing Logic
Virtual Design Silk Screen Studio
"""

import cv2
import numpy as np
import logging
import sys
import argparse
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

# Local imports
try:
    from core.print_job_config import PrintJobConfig
    from core.pipeline_controller import PipelineController
    from core.color_separator import ColorSeparator
    from core.mask_generator import MaskGenerator
    from core.halftone_generator import HalftoneGenerator
except ImportError:
    # Fallback for direct testing if needed
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from core.print_job_config import PrintJobConfig
    from core.pipeline_controller import PipelineController
    from core.color_separator import ColorSeparator
    from core.mask_generator import MaskGenerator
    from core.halftone_generator import HalftoneGenerator

logger = logging.getLogger(__name__)

def edge_aware_binarize(gray: np.ndarray) -> np.ndarray:
    """
    Improved binarization that preserves solid fill for large text characters.
    🔥 Enhanced with constant threshold to prevent bloating and preserve thin strokes.
    """
    # 0. 🔥 CRITICAL FIX: Bilateral filter to preserve edges while smoothing noise
    # This prevents the "chewed up"/erosion effect
    bilateral = cv2.bilateralFilter(gray, 9, 75, 75)
    
    # 1. 🔥 KEY FIX: Use constant threshold instead of Otsu for sharper text
    # Otsu causes bloating by including gray edges. Constant threshold captures only dark core.
    threshold_value = 180  # High value to avoid gray edges and preserve thin strokes
    _, th_const = cv2.threshold(bilateral, threshold_value, 255, cv2.THRESH_BINARY)
    
    # 2. Local Edge Sharpness (only for very fine details)
    # Use adaptive thresholding only for small areas to preserve counters
    h, w = bilateral.shape[:2]
    # Only use adaptive for small text to avoid over-bloating
    if min(h, w) < 800:  # Small image - use adaptive to preserve details
        block_size = int(min(h, w) * 0.1) | 1  # Smaller block for precision
        block_size = max(31, min(101, block_size))
        
        th_adaptive = cv2.adaptiveThreshold(
            bilateral, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, block_size, 8
        )
        
        # Combine: Use constant threshold as base, add adaptive only for fine details
        base = cv2.bitwise_and(th_const, cv2.bitwise_not(th_adaptive))
    else:
        # Large image - use constant threshold only for maximum sharpness
        base = th_const
    
    # 3. 🔥 Minimal morphological cleanup to preserve thin strokes
    # Very small kernel to avoid bloating
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    base = cv2.morphologyEx(base, cv2.MORPH_CLOSE, kernel, iterations=1)
    
    return base

@dataclass
class PipelineResult:
    masks: List[np.ndarray]
    separation_result: Dict
    image_class: str
    skip_binarization: bool = False
    effective_smoothing: float = None  # For artwork smoothing override (BUG-11 fix)

class PipelineRouter:
    """
    Routes an image to the most appropriate processing pipeline.
    Based on Task #18: Specialized Processing Tiers.
    """
    def __init__(self, job_config: PrintJobConfig):
        self.job_config = job_config
        self.controller = PipelineController()
        self.separator = ColorSeparator()
        self.mask_gen = MaskGenerator()
        self.halftone_gen = HalftoneGenerator()

    def route(self, image: np.ndarray, analysis, args: argparse.Namespace) -> PipelineResult:
        """
        Main entry point for routing.
        Args:
            image: Original upscaled image
            analysis: Result from SmartAnalyzer (or None if auto-detect skipped)
            args: CLI arguments
        """
        img_type = getattr(args, 'image_type', 'auto')
        
        # Classification decision
        if analysis and img_type == 'auto':
            image_class = analysis.image_class.value
            logger.info(f"[Router] Auto-routing decision: {image_class} (confidence={analysis.confidence:.2f})")
        else:
            image_class = img_type
            logger.info(f"[Router] Manual routing: {image_class}")

        # Execute specific pipeline (Passing analysis object to all sub-pipelines for connectivity)
        if image_class == 'text_logo':
            return self._run_text_logo(image, args, analysis)
        elif image_class == 'photo':
            return self._run_photo(image, args, analysis)
        else:
            # Default to artwork (illustrations)
            return self._run_artwork(image, args, analysis)

    def _run_text_logo(self, image: np.ndarray, args: argparse.Namespace, analysis=None) -> PipelineResult:
        """Pipeline for high-contrast logos/type: Sharpening + Pure Threshold + 1 Color."""
        # pure text_logo pipeline only handles 1 color (binary).
        if args.colors > 1:
            logger.info(f"[Router] Multi-color logo detected ({args.colors} colors). Routing to ARTWORK pipeline for separation.")
            return self._run_artwork(image, args, analysis)
            
        logger.info("[Router] Executing TEXT_LOGO pipeline...")
        from core.router_utils import preprocess_text_logo, _make_single_color_separation
        
        # 1. Preprocess
        preprocessed = preprocess_text_logo(image)
        gray = cv2.cvtColor(preprocessed, cv2.COLOR_BGR2GRAY)
        
        # 2. Binarization (Edge-Aware Thresholding)
        binary = edge_aware_binarize(gray)
        
        # 3. Enforce Polarity & Validate
        # 🔥 CRITICAL FIX: Force black ink for 1-color user choice
        force_black_ink = (args.colors == 1 and any(a.startswith('--colors') for a in sys.argv))
        binary = self.controller.enforce_polarity(binary, stage="text_logo", force_black_ink=force_black_ink)
        self.controller.validate_mask_coverage(binary, "text_logo")
        
        # 4. Cleanup (remove tiny noise)
        num, labels, stats, _ = cv2.connectedComponentsWithStats(cv2.bitwise_not(binary), 8, cv2.CV_32S)
        clean = np.full_like(binary, 255)
        for i in range(1, num):
            if stats[i, cv2.CC_STAT_AREA] >= 5: # 5px min area
                clean[labels == i] = 0
        binary = clean

        # 5. Synthetic separation (num_colors=1)
        sep_result = _make_single_color_separation(image)
        
        return PipelineResult(
            masks=[binary],
            separation_result=sep_result,
            image_class='text_logo',
            skip_binarization=True # Already binary
        )

    def _run_artwork(self, image: np.ndarray, args: argparse.Namespace, analysis=None) -> PipelineResult:
        """Pipeline for illustrations: Multi-color K-means."""
        logger.info("[Router] Executing ARTWORK pipeline...")
        from core.router_utils import preprocess_artwork, apply_halftone_pipeline
        
        # 1. Preprocess
        preprocessed = preprocess_artwork(image)
        
        # Auto-detect colors if not specified
        if args.colors == 0:
            args.colors = analysis.num_colors if analysis else 4
            logger.info(f"[Connectivity] SmartAnalyzer recommends {args.colors} colors. Applied.")
        
        target_colors = args.colors
        
        # 🔥 FIX 3: Single-color bypass (مهم جداً)
        should_halftone = False # Initialize scoped variable
        if target_colors == 1:
            logger.info("[Router] 1-color Artwork detected. Bypassing ColorSeparator.")
            from core.router_utils import _make_single_color_separation
            gray = cv2.cvtColor(preprocessed, cv2.COLOR_BGR2GRAY)
            m = edge_aware_binarize(gray)
            
            # 🔥 CRITICAL FIX: Force black ink for 1-color user choice
            force_black_ink = (args.colors == 1 and any(a.startswith('--colors') for a in sys.argv))
            m = self.controller.enforce_polarity(m, stage="artwork_1color", force_black_ink=force_black_ink)
            
            sep_result = _make_single_color_separation(image)
            masks = [m]
        else:
            # BUG-F3 Guard: KMeans n_clusters must be >= 2
            kmeans_colors = max(target_colors, 2)
            sep_result = self.separator.separate(preprocessed, num_colors=kmeans_colors)
            
            # 3. Generate Masks
            should_halftone = args.halftone or (analysis and (analysis.score_photo > 0.4 or analysis.use_halftone))
            use_grayscale = should_halftone
            masks = self.mask_gen.generate_masks(preprocessed, sep_result, grayscale_output=use_grayscale)

            # Snippet 3: IndexError Guard - Align masks and colors count
            num_sep_colors = len(sep_result.get('colors', []))
            if len(masks) != num_sep_colors:
                logger.warning(f"[MaskColorMismatch] masks={len(masks)}, colors={num_sep_colors}. Aligning...")
                if len(masks) > num_sep_colors:
                    masks = masks[:num_sep_colors]
                else:
                    empty = np.full(masks[0].shape, 255, dtype=np.uint8)
                    while len(masks) < num_sep_colors:
                        masks.append(empty.copy())
        
        # 4. Halftone (if requested or auto-detected for artwork)
        if should_halftone:
            logger.info("[Connectivity] Gradient/Photo-like features detected in Artwork. Enabling auto-halftone.")
            masks = apply_halftone_pipeline(masks, args, self.halftone_gen)
        
        # 5. Polarity & Coverage check per mask
        processed_masks = []
        for i, m in enumerate(masks):
            # 🔥 FIX 1: Guard ضد mask الفاضية
            if np.std(m) < 5:
                logger.warning(f"Mask {i} is flat (std={np.std(m):.2f}) -> fallback to simple threshold")
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                _, m = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
                
            # If not halftoning and not already binary, make binary now
            # FIXED: Use Otsu for each mask independently (BUG-05)
            if not args.halftone and len(np.unique(m)) > 2:
                # Edge-Aware Thresholding
                m = edge_aware_binarize(m)
            
            try:
                self.controller.validate_mask_coverage(m, f"artwork_mask_{i}", min_coverage=0.001)
                processed_masks.append(m)
            except ValueError:
                logger.warning(f"[Router] Skipping empty color mask {i}")
                # FIXED: Don't add empty mask - skip it entirely (BUG-03 fix)
                continue 

        # Task 18 override: cap smoothing for artwork
        # 🔥 CRITICAL FIX: Remove harsh capping for 1-color user choice
        user_forced_1color = (args.colors == 1 and any(a.startswith('--colors') for a in sys.argv))
        if user_forced_1color:
            # Don't cap for user 1-color choice - respect user smoothing
            effective_smooth = args.smoothing_factor
            logger.info(f'[Router] User 1-color - respecting smoothing: {effective_smooth}')
        else:
            # Apply capping for auto-detected cases
            effective_smooth = min(args.smoothing_factor, 0.25) if not args.halftone else 0.0
            logger.info(f'[Router] Artwork smoothing capped: {args.smoothing_factor} -> {effective_smooth}')
        
        return PipelineResult(
            masks=processed_masks,
            separation_result=sep_result,
            image_class='artwork',
            skip_binarization=False,
            effective_smoothing=effective_smooth  # New field for step9_export
        )

    def _run_photo(self, image: np.ndarray, args: argparse.Namespace, analysis=None) -> PipelineResult:
        """Pipeline for photos: AM Raster Halftone (professional grade)."""
        logger.info("[Router] Executing PHOTO pipeline (AM Raster Halftone)...")
        from core.router_utils import preprocess_photo, _make_single_color_separation
        try:
            from core.raster_halftone import RasterHalftoneEngine, RasterHalftoneConfig
            has_raster = True
        except ImportError:
            has_raster = False
        
        # 1. Preprocess
        preprocessed_gray = preprocess_photo(image)
        
        # 2. Validate LPI
        args.lpi = self.job_config.validate_lpi(args.lpi)
        
        # 3. AM Raster Halftone — الاستخدام الصحيح
        halftone_mode = getattr(args, 'halftone_mode', 'raster')
        
        if halftone_mode == 'raster' and has_raster:
            cfg = RasterHalftoneConfig(
                lpi=args.lpi,
                dpi=getattr(args, 'dpi', 1200),
                angle=getattr(args, 'halftone_angle', 45.0),
                dot_fn=getattr(args, 'dot_shape', 'round'),
                gamma=1.6,
            )
            engine = RasterHalftoneEngine(cfg)
            ht_mask = engine.generate(preprocessed_gray)
        else:
            # vector mode (fallback)
            ht_mask = self.halftone_gen.generate(
                preprocessed_gray,
                lpi=args.lpi,
                angle=getattr(args, 'halftone_angle', 45.0),
            )
        
        # 4. Validate
        self.controller.validate_mask_coverage(ht_mask, "photo_halftone", min_coverage=0.0005)
        
        # 5. Synthetic separation
        sep_result = _make_single_color_separation(image)
        
        return PipelineResult(
            masks=[ht_mask],
            separation_result=sep_result,
            image_class='photo',
            skip_binarization=True
        )
