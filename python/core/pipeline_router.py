"""
pipeline_router.py — Specialized Pipeline Routing Logic
Virtual Design Silk Screen Studio
"""

import cv2
import numpy as np
import logging
import argparse
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass

# Local imports
from core.print_job_config import PrintJobConfig
from core.pipeline_controller import PipelineController
from core.color_separator import ColorSeparator
from core.mask_generator import MaskGenerator
from core.halftone_generator import HalftoneGenerator
from core.underbase_generator import UnderbaseGenerator
from core.router_utils import edge_aware_binarize

logger = logging.getLogger(__name__)

@dataclass
class PipelineResult:
    masks: List[np.ndarray]
    separation_result: Dict
    image_class: str
    skip_binarization: bool = False
    effective_smoothing: float = None
    mask_dpi: Optional[int] = None

class PipelineRouter:
    """
    Routes an image to the most appropriate processing pipeline.
    Stateless executor of the Decision Oracle's plan.
    """
    def __init__(self, job_config: PrintJobConfig, alpha_mask: Optional[np.ndarray] = None):
        self.job_config = job_config
        self.controller = PipelineController()
        self.separator = ColorSeparator()
        self.mask_gen = MaskGenerator()
        self.halftone_gen = HalftoneGenerator()
        self.alpha_mask = alpha_mask

    def route_deterministic(self, image: np.ndarray, decision: Any) -> PipelineResult:
        """
        Main routing entry point using the Unified Decision Engine output.
        """
        image_class = decision.image_class
        params = decision.parameters
        
        logger.info(f"[PipelineRouter] Executing Decision: class={image_class.upper()}")
        
        if image_class == 'text_logo':
            if params.get('colors', 1) > 1:
                return self._run_artwork(image, params)
            return self._run_text_logo(image, params)
        elif image_class == 'photo':
            return self._run_photo(image, params)
        else:
            return self._run_artwork(image, params)

    def route(self, image: np.ndarray, analysis, args: argparse.Namespace) -> PipelineResult:
        """Legacy compatibility wrapper."""
        from core.decision_engine import DecisionOracle
        from core.physical_print_model import PhysicalPrintModel
        from core import ai_vision_bridge
        
        ppm = PhysicalPrintModel(mesh_count=getattr(args, 'mesh_count', 280))
        oracle = DecisionOracle()
        decision = oracle.solve(image, args, ai_vision_bridge, ppm)
        
        return self.route_deterministic(image, decision)

    def _run_text_logo(self, image: np.ndarray, params: Dict[str, Any]) -> PipelineResult:
        from core.router_utils import preprocess_text_logo, _make_single_color_separation
        preprocessed = preprocess_text_logo(image)
        gray = cv2.cvtColor(preprocessed, cv2.COLOR_BGR2GRAY)
        
        binary = edge_aware_binarize(gray, use_adaptive=False)
        binary = self.controller.enforce_polarity(
            binary, stage="text_logo", force_black_ink=True, alpha_mask=self.alpha_mask
        )
        
        # Noise removal
        num, labels, stats, _ = cv2.connectedComponentsWithStats(cv2.bitwise_not(binary), 8, cv2.CV_32S)
        clean = np.full_like(binary, 255)
        min_area = params.get('contour_min_area', 5)
        for i in range(1, num):
            if stats[i, cv2.CC_STAT_AREA] >= min_area: 
                clean[labels == i] = 0
        binary = (clean > 127).astype(np.uint8) * 255
        
        masks = [binary]
        sep_result = _make_single_color_separation(image)
        masks, sep_result = self._apply_pro_prepress(masks, params, sep_result)

        return PipelineResult(
            masks=masks, separation_result=sep_result,
            image_class='text_logo', skip_binarization=True
        )

    def _run_artwork(self, image: np.ndarray, params: Dict[str, Any]) -> PipelineResult:
        from core.router_utils import preprocess_artwork, apply_halftone_pipeline
        preprocessed = preprocess_artwork(image)
        target_colors = params.get('colors', 1)
        should_halftone = params.get('halftone', False)

        if target_colors == 1 and not should_halftone:
            from core.router_utils import _make_single_color_separation
            gray = cv2.cvtColor(preprocessed, cv2.COLOR_BGR2GRAY)
            m = edge_aware_binarize(gray, use_adaptive=False)
            m = self.controller.enforce_polarity(m, stage="artwork_1color", alpha_mask=self.alpha_mask)
            masks = [(m > 127).astype(np.uint8) * 255]
            sep_result = _make_single_color_separation(image)
        elif target_colors == 1 and should_halftone:
            from core.router_utils import _make_single_color_separation
            gray = cv2.cvtColor(preprocessed, cv2.COLOR_BGR2GRAY)
            # Apply alpha mask for halftone input
            if self.alpha_mask is not None:
                alpha_resized = self._resize_alpha(self.alpha_mask, gray.shape)
                gray = gray.copy()
                gray[~alpha_resized] = 255
            masks = [gray]
            sep_result = _make_single_color_separation(image)
        else:
            sep_result = self.separator.separate(preprocessed, num_colors=target_colors, alpha_mask=self.alpha_mask)
            masks = self.mask_gen.generate_masks(preprocessed, sep_result, grayscale_output=should_halftone)
        
        if should_halftone:
            # We need to wrap params in an object that looks like args for router_utils
            class ParamProxy:
                def __init__(self, p): self.p = p
                def __getattr__(self, k): return self.p.get(k)
            masks = apply_halftone_pipeline(masks, ParamProxy(params), self.halftone_gen)

        processed_masks = []
        for i, m in enumerate(masks):
            # Enforce binary for non-halftone or final step
            if not should_halftone:
                m = edge_aware_binarize(m, use_adaptive=False)
            
            if self.alpha_mask is not None:
                alpha_resized = self._resize_alpha(self.alpha_mask, m.shape)
                m = m.copy()
                m[~alpha_resized] = 255
            
            m = (m > 127).astype(np.uint8) * 255
            try:
                self.controller.validate_mask_coverage(m, f"artwork_mask_{i}")
                processed_masks.append(m)
            except ValueError: continue

        processed_masks, sep_result = self._apply_pro_prepress(processed_masks, params, sep_result)
        mask_dpi = params.get('_halftone_raster_dpi', params.get('dpi', 300))

        return PipelineResult(
            masks=processed_masks, separation_result=sep_result,
            image_class='artwork_halftone' if should_halftone else 'artwork',
            effective_smoothing=params.get('smoothing_factor', 0.25),
            mask_dpi=mask_dpi
        )

    def _run_photo(self, image: np.ndarray, params: Dict[str, Any]) -> PipelineResult:
        from core.router_utils import preprocess_photo, _make_single_color_separation
        from core.raster_halftone import RasterHalftoneEngine, RasterHalftoneConfig
        preprocessed_gray = preprocess_photo(image)
        
        output_dpi = params.get('dpi', 450)
        raster_dpi = max(1200, output_dpi * 2)
        params['_halftone_raster_dpi'] = raster_dpi
        
        cfg = RasterHalftoneConfig(
            lpi=params.get('lpi', 55), dpi=raster_dpi, angle=params.get('halftone_angle', 45.0),
            dot_fn=params.get('dot_shape', 'round'), gamma=1.6, oversample=2
        )
        ht_engine = RasterHalftoneEngine(cfg)
        
        ht_mask = ht_engine.generate(preprocessed_gray)
        self.controller.validate_mask_coverage(ht_mask, "photo_halftone")
        sep_result = _make_single_color_separation(image)
        
        masks = [ht_mask]
        masks, sep_result = self._apply_pro_prepress(masks, params, sep_result)

        return PipelineResult(
            masks=masks, separation_result=sep_result,
            image_class='photo', skip_binarization=True, mask_dpi=raster_dpi
        )

    def _apply_pro_prepress(self, masks: List[np.ndarray], params: Dict[str, Any], sep_result: Dict) -> Tuple[List[np.ndarray], Dict]:
        ub_gen = UnderbaseGenerator()
        if params.get('use_underbase', False):
            under_mask = ub_gen.generate_underbase(masks, choke_px=params.get('choke_px', 2))
            if under_mask is not None:
                masks.insert(0, under_mask)
                sep_result['colors'].insert(0, (255, 255, 255))
                sep_result['color_names'].insert(0, "White_Underbase")
        
        trap_px = params.get('trapping_px', 0)
        if trap_px > 0 and masks:
            min_half_stroke = float('inf')
            for m in masks:
                inv = cv2.bitwise_not(m)
                dt = cv2.distanceTransform(inv, cv2.DIST_L2, 3)
                min_half_stroke = min(min_half_stroke, float(dt.max()))
            if (min_half_stroke * 2) >= (2 * trap_px):
                masks = ub_gen.apply_trapping(masks, trap_px=trap_px)
        return masks, sep_result

    def _resize_alpha(self, alpha: np.ndarray, shape: Tuple[int, int]) -> np.ndarray:
        if alpha.shape == shape: return alpha
        return cv2.resize(alpha.astype(np.uint8), (shape[1], shape[0]), interpolation=cv2.INTER_NEAREST).astype(bool)
