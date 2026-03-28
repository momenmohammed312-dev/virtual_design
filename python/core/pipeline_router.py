"""
pipeline_router.py — Specialized Pipeline Routing Logic
Virtual Design Silk Screen Studio
"""

import cv2
import numpy as np
import logging
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

@dataclass
class PipelineResult:
    masks: List[np.ndarray]
    separation_result: Dict
    image_class: str
    skip_binarization: bool = False

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

        # Execute specific pipeline
        if image_class == 'text_logo':
            return self._run_text_logo(image, args)
        elif image_class == 'photo':
            return self._run_photo(image, args)
        else:
            # Default to artwork (illustrations)
            return self._run_artwork(image, args)

    def _run_text_logo(self, image: np.ndarray, args: argparse.Namespace) -> PipelineResult:
        """Pipeline for high-contrast logos/type: Sharpening + Pure Threshold + 1 Color."""
        # pure text_logo pipeline only handles 1 color (binary).
        if args.colors > 1:
            logger.info(f"[Router] Multi-color logo detected ({args.colors} colors). Routing to ARTWORK pipeline for separation.")
            return self._run_artwork(image, args)
            
        logger.info("[Router] Executing TEXT_LOGO pipeline...")
        from core.router_utils import preprocess_text_logo, _make_single_color_separation
        
        # 1. Preprocess
        preprocessed = preprocess_text_logo(image)
        gray = cv2.cvtColor(preprocessed, cv2.COLOR_BGR2GRAY)
        
        # 2. Otsu Binarization (Best for high contrast)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 3. Enforce Polarity & Validate
        binary = self.controller.enforce_polarity(binary, stage="text_logo")
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

    def _run_artwork(self, image: np.ndarray, args: argparse.Namespace) -> PipelineResult:
        """Pipeline for illustrations: Multi-color K-means."""
        logger.info("[Router] Executing ARTWORK pipeline...")
        from core.router_utils import preprocess_artwork, apply_halftone_pipeline
        
        # 1. Preprocess
        preprocessed = preprocess_artwork(image)
        
        # 2. Color Separation
        target_colors = args.colors if args.colors > 0 else 4
        sep_result = self.separator.separate(preprocessed, num_colors=target_colors)
        
        # 3. Generate Masks
        # If halftoning, generate grayscale intensity masks.
        masks = self.mask_gen.generate_masks(preprocessed, sep_result, grayscale_output=args.halftone)
        
        # 4. Halftone (if requested for artwork)
        if args.halftone:
            masks = apply_halftone_pipeline(masks, args, self.halftone_gen)
        
        # 5. Polarity & Coverage check per mask
        processed_masks = []
        for i, m in enumerate(masks):
            # If not halftoning and not already binary, make binary now
            if not args.halftone and len(np.unique(m)) > 2:
                _, m = cv2.threshold(m, 127, 255, cv2.THRESH_BINARY)
            
            try:
                self.controller.validate_mask_coverage(m, f"artwork_mask_{i}", min_coverage=0.001)
                processed_masks.append(m)
            except ValueError:
                logger.warning(f"[Router] Skipping empty color mask {i}")
                processed_masks.append(m) 

        # Task 18 override: cap smoothing for artwork
        args.smoothing_factor = min(args.smoothing_factor, 0.15) if not args.halftone else 0.0

        return PipelineResult(
            masks=processed_masks,
            separation_result=sep_result,
            image_class='artwork'
        )

    def _run_photo(self, image: np.ndarray, args: argparse.Namespace) -> PipelineResult:
        """Pipeline for photos: Forced halftone gradients."""
        logger.info("[Router] Executing PHOTO pipeline (Halftone Mandatory)...")
        from core.router_utils import preprocess_photo, _make_single_color_separation, apply_halftone_pipeline
        
        # 1. Preprocess (Bilateral + Grayscale + Unsharp)
        preprocessed_gray = preprocess_photo(image)
        
        # 2. Mandatory Halftone
        # Calculate safe LPI
        args.lpi = self.job_config.validate_lpi(args.lpi)
        
        masks = apply_halftone_pipeline([preprocessed_gray], args, self.halftone_gen)
        ht_mask = masks[0]
        
        # 3. Validate coverage (sparse dots OK)
        self.controller.validate_mask_coverage(ht_mask, "photo_halftone", min_coverage=0.0005)
        
        # 4. Synthetic separation (num_colors=1 for photo)
        sep_result = _make_single_color_separation(image)

        # Skip later binarization/smoothing
        return PipelineResult(
            masks=[ht_mask],
            separation_result=sep_result,
            image_class='photo',
            skip_binarization=True
        )
