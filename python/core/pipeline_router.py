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

# Local imports (using absolute paths or relative depending on structure)
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
    Orchestrates specialized pipelines for different image types:
    - TEXT_LOGO: High-contrast, Otsu-based, no halftone.
    - ARTWORK: Multi-color, K-means based, optional halftone.
    - PHOTO: Grayscale gradients, mandatory halftone.
    """
    
    def __init__(self, job_config: PrintJobConfig):
        self.job_config = job_config
        self.controller = PipelineController()
        self.separator = ColorSeparator()
        self.mask_gen = MaskGenerator()
        self.halftone_gen = HalftoneGenerator(dpi=job_config.dpi)

    def route(self, image: np.ndarray, analysis: any, args: argparse.Namespace) -> PipelineResult:
        """Entry point for routing the image to the correct pipeline."""
        img_class = analysis.image_class.value if hasattr(analysis.image_class, 'value') else str(analysis.image_class)
        logger.info(f"[Router] Routing image as: {img_class}")

        if img_class == 'text_logo':
            return self._run_text_logo(image, args)
        elif img_class == 'photo':
            return self._run_photo(image, args)
        elif img_class == 'low_quality':
            logger.warning("[Router] Image quality is low/blurry. Proceeding with ARTWORK pipeline as fallback.")
            from main import preprocess_artwork
            return self._run_artwork(image, args)
        else:
            # Default to artwork for 'mixed', 'unknown', or 'artwork'
            return self._run_artwork(image, args)

    def _run_text_logo(self, image: np.ndarray, args: argparse.Namespace) -> PipelineResult:
        """Pipeline for pure logos and text: Clean Otsu thresholding."""
        # SENIOR FIX: If user requested more than 1 color, we MUST separate them!
        # pure text_logo pipeline only handles 1 color (binary).
        if args.colors > 1:
            logger.info(f"[Router] Multi-color logo detected ({args.colors} colors). Routing to ARTWORK pipeline for separation.")
            return self._run_artwork(image, args)
            
        logger.info("[Router] Executing TEXT_LOGO pipeline...")
        from main import preprocess_text_logo, _make_single_color_separation
        
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
        from main import preprocess_artwork
        
        # 1. Preprocess
        preprocessed = preprocess_artwork(image)
        
        # 2. Color Separation (Task 15 retry logic inside)
        target_colors = args.colors if args.colors > 0 else 4
        sep_result = self.separator.separate(preprocessed, num_colors=target_colors)
        
        # 3. Generate Masks
        # If halftoning, generate grayscale intensity masks.
        masks = self.mask_gen.generate_masks(preprocessed, sep_result, grayscale_output=args.halftone)
        
        # 4. Halftone (if requested for artwork)
        if args.halftone:
            from main import step5_halftone
            masks = step5_halftone(masks, args)
        
        # 5. Polarity & Coverage check per mask
        processed_masks = []
        for i, m in enumerate(masks):
            # If not halftoning and not already binary, make binary now
            if not args.halftone and len(np.unique(m)) > 2:
                _, m = cv2.threshold(m, 127, 255, cv2.THRESH_BINARY)
            
            m = self.controller.enforce_polarity(m, stage=f"artwork_mask_{i}")
            
            # Use lenient coverage for individual color layers
            try:
                self.controller.validate_mask_coverage(m, f"artwork_mask_{i}", min_coverage=0.001)
                processed_masks.append(m)
            except ValueError:
                logger.warning(f"[Router] Skipping empty color mask {i}")
                # We still keep the slot to maintain index syncing? No, better to remove if truly blank.
                # But sep_result says it exists. We'll keep it but it might fail later.
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
        from main import preprocess_photo
        
        # 1. Preprocess (Bilateral + Grayscale + Unsharp)
        preprocessed_gray = preprocess_photo(image)
        
        # 2. Mandatory Halftone
        # Calculate safe LPI
        args.lpi = self.job_config.validate_lpi(args.lpi)
        
        # Dot Radius Cap (0.85) is inside HalftoneGenerator (Task 16)
        ht_mask = self.halftone_gen.generate(
            preprocessed_gray, 
            lpi=args.lpi, 
            angle=45.0, 
            dot_shape=args.dot_shape, 
            dpi=self.job_config.dpi, 
            gamma=1.6
        )
        
        # 3. Validate coverage (sparse dots OK)
        self.controller.validate_mask_coverage(ht_mask, "photo_halftone", min_coverage=0.0005)
        
        # 4. Synthetic separation (num_colors=1 for photo)
        # Note: Colors are already represented by dots in a single black film.
        from main import _make_single_color_separation
        sep_result = _make_single_color_separation(image)

        # Skip later binarization/smoothing
        return PipelineResult(
            masks=[ht_mask],
            separation_result=sep_result,
            image_class='photo',
            skip_binarization=True
        )
