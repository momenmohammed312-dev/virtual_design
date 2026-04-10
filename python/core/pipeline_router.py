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
    from core.underbase_generator import UnderbaseGenerator
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from core.print_job_config import PrintJobConfig
    from core.pipeline_controller import PipelineController
    from core.color_separator import ColorSeparator
    from core.mask_generator import MaskGenerator
    from core.halftone_generator import HalftoneGenerator
    from core.underbase_generator import UnderbaseGenerator

logger = logging.getLogger(__name__)

def edge_aware_binarize(gray: np.ndarray) -> np.ndarray:
    """
    Improved binarization that preserves solid fill for large text characters.
    🔥 Enhanced with constant threshold to prevent bloating and preserve thin strokes.
    """
    bilateral = cv2.bilateralFilter(gray, 9, 75, 75)
    threshold_value = 180  
    _, th_const = cv2.threshold(bilateral, threshold_value, 255, cv2.THRESH_BINARY)
    
    h, w = bilateral.shape[:2]
    if min(h, w) < 800:  
        block_size = int(min(h, w) * 0.1) | 1  
        block_size = max(31, min(101, block_size))
        th_adaptive = cv2.adaptiveThreshold(
            bilateral, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, block_size, 8
        )
        base = cv2.bitwise_and(th_const, cv2.bitwise_not(th_adaptive))
    else:
        base = th_const
    
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    base = cv2.morphologyEx(base, cv2.MORPH_CLOSE, kernel, iterations=1)
    return base

@dataclass
class PipelineResult:
    masks: List[np.ndarray]
    separation_result: Dict
    image_class: str
    skip_binarization: bool = False
    effective_smoothing: float = None  

class PipelineRouter:
    """
    Routes an image to the most appropriate processing pipeline.
    """
    def __init__(self, job_config: PrintJobConfig, alpha_mask: Optional[np.ndarray] = None):
        self.job_config = job_config
        self.controller = PipelineController()
        self.separator = ColorSeparator()
        self.mask_gen = MaskGenerator()
        self.halftone_gen = HalftoneGenerator()
        # 🔥 Store alpha mask for transparent PNG handling
        self.alpha_mask = alpha_mask

    def route(self, image: np.ndarray, analysis, args: argparse.Namespace) -> PipelineResult:
        img_type = getattr(args, 'image_type', 'auto')

        # 🔥 FIX: Check if user explicitly selected halftone from UI
        user_selected_halftone = getattr(args, 'halftone', False)
        logger.info(f"[PipelineRouter] ENTRY: user_selected_halftone={user_selected_halftone}, img_type={img_type}, args.halftone={getattr(args, 'halftone', 'NOTSET')}")

        # 🔥🔥🔥 CRITICAL FIX: If user selected halftone, ALWAYS use artwork pipeline for raster halftone
        # This check is OUTSIDE the 'auto' block to catch all cases including when AI changes img_type
        if user_selected_halftone:
            logger.info("[PipelineRouter] ✓✓✓ USER SELECTED HALFTONE -> Forcing ARTWORK pipeline for raster halftone ✓✓✓")
            return self._run_artwork(image, args, analysis)

        if img_type == 'auto':
            try:
                from core.ai_vision_bridge import analyze_image as ai_analyze, apply_to_args, is_available
                if is_available():
                    ai_result = ai_analyze(image)
                    if ai_result is not None:
                        apply_to_args(ai_result, args)
                        image_class = ai_result["image_class"]

                        if image_class == 'text_logo':
                            return self._run_text_logo(image, args, analysis)
                        elif image_class == 'photo':
                            return self._run_photo(image, args, analysis)
                        else:
                            return self._run_artwork(image, args, analysis)
            except Exception:
                pass

        if analysis and img_type == 'auto':
            image_class = analysis.image_class.value
        else:
            image_class = img_type

        if image_class == 'text_logo':
            return self._run_text_logo(image, args, analysis)
        elif image_class == 'photo':
            return self._run_photo(image, args, analysis)
        else:
            return self._run_artwork(image, args, analysis)

    def _run_text_logo(self, image: np.ndarray, args: argparse.Namespace, analysis=None) -> PipelineResult:
        if args.colors > 1:
            return self._run_artwork(image, args, analysis)
            
        from core.router_utils import preprocess_text_logo, _make_single_color_separation
        preprocessed = preprocess_text_logo(image)
        gray = cv2.cvtColor(preprocessed, cv2.COLOR_BGR2GRAY)
        binary = edge_aware_binarize(gray)
        
        binary = self.controller.enforce_polarity(
            binary, 
            stage="text_logo",
            force_black_ink=True,   # Always black ink on white background for silk screen
            alpha_mask=self.alpha_mask  # 🔥 Respect transparent pixels
        )
        
        num, labels, stats, _ = cv2.connectedComponentsWithStats(cv2.bitwise_not(binary), 8, cv2.CV_32S)
        clean = np.full_like(binary, 255)
        for i in range(1, num):
            if stats[i, cv2.CC_STAT_AREA] >= 5: 
                clean[labels == i] = 0
        binary = clean
        
        # 🔥 CRITICAL FIX: Apply alpha mask to ensure transparent pixels are background (255)
        if self.alpha_mask is not None:
            if binary.shape != self.alpha_mask.shape:
                alpha_resized = cv2.resize(
                    self.alpha_mask.astype(np.uint8),
                    (binary.shape[1], binary.shape[0]),
                    interpolation=cv2.INTER_NEAREST
                ).astype(bool)
            else:
                alpha_resized = self.alpha_mask
            
            binary = binary.copy()
            binary[~alpha_resized] = 255
            transparent_count = np.sum(~alpha_resized)
            logger.info(f"[PipelineRouter] TextLogo: Set {transparent_count} transparent pixels to background (255)")
        
        sep_result = _make_single_color_separation(image)

        # FIX GROUP 9.1: Apply pro prepress (underbase and trapping)
        masks = [binary]
        masks, sep_result = self._apply_pro_prepress(masks, args, sep_result)

        return PipelineResult(
            masks=masks,
            separation_result=sep_result,
            image_class='text_logo',
            skip_binarization=True
        )

    def _apply_pro_prepress(self, masks: List[np.ndarray], args: argparse.Namespace, sep_result: Dict) -> Tuple[List[np.ndarray], Dict]:
        ub_gen = UnderbaseGenerator()
        # 1. White Underbase (for dark shirts)
        if getattr(args, 'use_underbase', False):
            # Create underbase from all existing masks
            under_mask = ub_gen.generate_underbase(masks, choke_px=getattr(args, 'choke_px', 2))
            if under_mask is not None:
                masks.insert(0, under_mask)
                sep_result['colors'].insert(0, (255, 255, 255))
                sep_result['color_names'].insert(0, "White_Underbase")
                logger.info("[Prepress] White Underbase generated.")

        # 2. Ink Trapping (overlaps)
        trap_px = getattr(args, 'trapping_px', 0)
        if trap_px > 0:
            masks = ub_gen.apply_trapping(masks, trap_px=trap_px)
            logger.info(f"[Prepress] Applied {trap_px}px trapping.")
            
        return masks, sep_result

    def _run_artwork(self, image: np.ndarray, args: argparse.Namespace, analysis=None) -> PipelineResult:
        from core.router_utils import preprocess_artwork, apply_halftone_pipeline
        preprocessed = preprocess_artwork(image)
        
        if args.colors == 0:
            args.colors = analysis.num_colors if analysis else 4
        
        target_colors = args.colors
        should_halftone = args.halftone or (analysis and (analysis.score_photo > 0.4 or analysis.use_halftone))
        
        # 🔥 FIX Issue #9: Detect if image is truly single-color to avoid blank masks
        # Pre-analyze image to determine actual color count
        if target_colors == 1 and should_halftone:
            # Even for halftone, check if image really needs only 1 color
            # by analyzing color variance in non-transparent regions
            if self.alpha_mask is not None:
                visible_pixels = preprocessed[self.alpha_mask]
            else:
                visible_pixels = preprocessed.reshape(-1, 3)
            
            if len(visible_pixels) > 0:
                # Convert to LAB for perceptual analysis
                visible_lab = cv2.cvtColor(
                    visible_pixels.reshape(1, -1, 3), 
                    cv2.COLOR_BGR2LAB
                ).reshape(-1, 3)
                
                # Check color variance
                color_std = np.std(visible_lab, axis=0)
                is_truly_single_color = np.all(color_std < 15)  # Low variance = single color
                
                if is_truly_single_color:
                    logger.info(f"[PipelineRouter] Image is truly single-color (std={color_std.mean():.1f}). Using 1-color halftone.")
                    kmeans_colors = 1
                else:
                    kmeans_colors = 2  # Need 2 colors for tonal separation
            else:
                kmeans_colors = 2
        else:
            kmeans_colors = max(target_colors, 2) if should_halftone else target_colors
        
        # 🔥 FIX: When halftone is selected, always do color separation (even with 1 color)
        # Halftone needs grayscale output from color separation, not binary
        if target_colors == 1 and not should_halftone:
            # Non-halftone single color: use fast binary path
            from core.router_utils import _make_single_color_separation
            gray = cv2.cvtColor(preprocessed, cv2.COLOR_BGR2GRAY)
            m = edge_aware_binarize(gray)
            m = self.controller.enforce_polarity(
                m, 
                stage="artwork_1color",
                alpha_mask=self.alpha_mask  # 🔥 Respect transparent pixels
            )
            sep_result = _make_single_color_separation(image)
            masks = [m]
        else:
            # Halftone mode OR multi-color: do proper color separation
            logger.info(f"[PipelineRouter] Color separation for halftone: {kmeans_colors} colors, grayscale_output={should_halftone}")
            # 🔥 Pass alpha_mask to exclude transparent pixels from color clustering
            sep_result = self.separator.separate(
                preprocessed, 
                num_colors=kmeans_colors,
                alpha_mask=self.alpha_mask
            )
            masks = self.mask_gen.generate_masks(preprocessed, sep_result, grayscale_output=should_halftone)
        
        if should_halftone:
            logger.info(f"[PipelineRouter] ✓✓✓ ENTERING HALFTONE PIPELINE - {len(masks)} masks")
            masks = apply_halftone_pipeline(masks, args, self.halftone_gen)
            logger.info(f"[PipelineRouter] ✓✓✓ HALFTONE PIPELINE COMPLETE - {len(masks)} masks processed")
        
        processed_masks = []
        for i, m in enumerate(masks):
            if not args.halftone and len(np.unique(m)) > 2:
                m = edge_aware_binarize(m)
            
            # 🔥 CRITICAL FIX: Apply alpha mask to ensure transparent pixels are background (255)
            if self.alpha_mask is not None:
                if m.shape != self.alpha_mask.shape:
                    # Resize alpha mask to match mask
                    alpha_resized = cv2.resize(
                        self.alpha_mask.astype(np.uint8),
                        (m.shape[1], m.shape[0]),
                        interpolation=cv2.INTER_NEAREST
                    ).astype(bool)
                else:
                    alpha_resized = self.alpha_mask
                
                # Set transparent pixels to 255 (background/white)
                # alpha_mask=True means visible, False means transparent
                m = m.copy()
                m[~alpha_resized] = 255
                transparent_count = np.sum(~alpha_resized)
                logger.info(f"[PipelineRouter] Mask {i}: Set {transparent_count} transparent pixels to background (255)")
            
            try:
                self.controller.validate_mask_coverage(m, f"artwork_mask_{i}")
                processed_masks.append(m)
            except ValueError:
                continue 

        # 🎯 PRO PREPRESS: Apply Underbase and Trapping
        processed_masks, sep_result = self._apply_pro_prepress(processed_masks, args, sep_result)

        # FIX Issue #11: Progress/routing label accuracy
        # Use 'artwork_halftone' to indicate artwork pipeline with halftone export format
        # This distinguishes from true 'photo' pipeline while ensuring raster PDF export
        if should_halftone:
            export_class = 'artwork_halftone'  # Artwork pipeline + halftone rendering
        else:
            export_class = 'artwork'

        return PipelineResult(
            masks=processed_masks,
            separation_result=sep_result,
            image_class=export_class,
            skip_binarization=False,
            effective_smoothing=args.smoothing_factor
        )

    def _run_photo(self, image: np.ndarray, args: argparse.Namespace, analysis=None) -> PipelineResult:
        """Photo Pipeline: Grayscale -> CLAHE -> High-DPI Raster Halftone."""
        from core.router_utils import preprocess_photo, _make_single_color_separation
        from core.raster_halftone import RasterHalftoneEngine, RasterHalftoneConfig
        
        preprocessed_gray = preprocess_photo(image)

        # Use RasterHalftoneEngine at high DPI for professional output
        output_dpi = getattr(args, 'dpi', 450)
        # Target raster DPI: at minimum 2x the output DPI for sharp dots
        # For screen printing films: 1200 DPI is standard, 2400 is premium
        raster_dpi = max(1200, output_dpi * 2)
        raster_cfg = RasterHalftoneConfig(
            lpi=args.lpi,
            dpi=raster_dpi,
            angle=getattr(args, 'halftone_angle', 45.0),
            dot_fn=getattr(args, 'dot_shape', 'round'),
            gamma=1.6,
            oversample=2,
        )
        ht_engine = RasterHalftoneEngine(raster_cfg)
        
        # Smart auto-fix loop: Try processing, adjust if result is empty
        for attempt in range(2):
            ht_mask = ht_engine.generate(preprocessed_gray)
            
            # Check Quality (Ink Coverage)
            filled = np.sum(ht_mask == 0)
            if filled > (ht_mask.size * 0.01):  # At least 1% ink
                break
            
            # Low contrast? Try boosting
            logger.info(f"[SmartFix] Attempt {attempt+1}: low ink coverage, boosting contrast")
            preprocessed_gray = cv2.convertScaleAbs(preprocessed_gray, alpha=1.2, beta=0)

        logger.info(f"[Photo] Raster halftone @ {raster_dpi} DPI, {args.lpi} LPI")
        self.controller.validate_mask_coverage(ht_mask, "photo_halftone")
        sep_result = _make_single_color_separation(image)
        
        # PRO PREPRESS: Apply Underbase (usually just white for photo)
        masks = [ht_mask]
        masks, sep_result = self._apply_pro_prepress(masks, args, sep_result)

        return PipelineResult(
            masks=masks,
            separation_result=sep_result,
            image_class='photo',
            skip_binarization=True
        )
