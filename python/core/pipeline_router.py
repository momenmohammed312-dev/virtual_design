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
    def __init__(self, job_config: PrintJobConfig):
        self.job_config = job_config
        self.controller = PipelineController()
        self.separator = ColorSeparator()
        self.mask_gen = MaskGenerator()
        self.halftone_gen = HalftoneGenerator()

    def route(self, image: np.ndarray, analysis, args: argparse.Namespace) -> PipelineResult:
        img_type = getattr(args, 'image_type', 'auto')

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
            force_black_ink=True   # Always black ink on white background for silk screen
        )
        
        num, labels, stats, _ = cv2.connectedComponentsWithStats(cv2.bitwise_not(binary), 8, cv2.CV_32S)
        clean = np.full_like(binary, 255)
        for i in range(1, num):
            if stats[i, cv2.CC_STAT_AREA] >= 5: 
                clean[labels == i] = 0
        binary = clean
        sep_result = _make_single_color_separation(image)
        
        return PipelineResult(
            masks=[binary],
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
        if target_colors == 1:
            from core.router_utils import _make_single_color_separation
            gray = cv2.cvtColor(preprocessed, cv2.COLOR_BGR2GRAY)
            m = edge_aware_binarize(gray)
            m = self.controller.enforce_polarity(m, stage="artwork_1color")
            sep_result = _make_single_color_separation(image)
            masks = [m]
            should_halftone = False
        else:
            kmeans_colors = max(target_colors, 2)
            sep_result = self.separator.separate(preprocessed, num_colors=kmeans_colors)
            should_halftone = args.halftone or (analysis and (analysis.score_photo > 0.4 or analysis.use_halftone))
            masks = self.mask_gen.generate_masks(preprocessed, sep_result, grayscale_output=should_halftone)
        
        if should_halftone:
            masks = apply_halftone_pipeline(masks, args, self.halftone_gen)
        
        processed_masks = []
        for i, m in enumerate(masks):
            if not args.halftone and len(np.unique(m)) > 2:
                m = edge_aware_binarize(m)
            try:
                self.controller.validate_mask_coverage(m, f"artwork_mask_{i}")
                processed_masks.append(m)
            except ValueError:
                continue 

        # 🎯 PRO PREPRESS: Apply Underbase and Trapping
        processed_masks, sep_result = self._apply_pro_prepress(processed_masks, args, sep_result)

        return PipelineResult(
            masks=processed_masks,
            separation_result=sep_result,
            image_class='artwork',
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
