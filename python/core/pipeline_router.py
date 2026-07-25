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
        
        # FIX: If user explicitly enforced halftone mode, route to artwork pipeline
        # regardless of image class. The artwork pipeline handles halftone generation.
        user_enforced_halftone = params.get('halftone', False)
        if user_enforced_halftone and image_class == 'text_logo':
            print(f"🎯 [PipelineRouter] User enforced HALFTONE on text_logo - routing to artwork pipeline", flush=True)
            logger.info(f"[PipelineRouter] User enforced HALFTONE on text_logo - routing to artwork pipeline")
            return self._run_artwork(image, params, image_class)
        
        if image_class == 'text_logo':
            if params.get('colors', 1) > 1:
                return self._run_artwork(image, params, image_class)
            return self._run_text_logo(image, params)
        elif image_class == 'photo':
            return self._run_photo(image, params)
        else:
            return self._run_artwork(image, params, image_class)

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
        from core.router_utils import preprocess_text_logo, _make_single_color_separation, apply_upscale_factor
        denoise_strength = params.get('denoise_strength', 5)
        # Disable upscale for text_logo to prevent artifacts
        upscale_factor = 1.0 
        preprocessed = preprocess_text_logo(image, denoise_strength=denoise_strength)
        preprocessed = apply_upscale_factor(preprocessed, upscale_factor)
        gray = cv2.cvtColor(preprocessed, cv2.COLOR_BGR2GRAY)
        
        binary = edge_aware_binarize(gray, use_adaptive=False, denoise_strength=denoise_strength)

        # Morphological cleanup للـ solid mode
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN,  kernel, iterations=1)

        # Adaptive smoothing based on edge roughness measurement AND image size
        edges = cv2.Canny(binary, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
        # Higher edge density = more detail = less smoothing needed
        # Lower edge density = smoother = more smoothing needed
        h, w = binary.shape[:2]
        max_dim = max(h, w)
        res_q = np.clip((max_dim - 300) / (4000 - 300), 0.0, 1.0)

        # Edge-density-based auto smoothing
        auto_smooth = max(0.05, min(0.5, 0.3 - (edge_density - 0.1) * 0.5))

        # Blend with existing params (from AI/decision engine) instead of full override
        # 60% auto (edge-based) + 40% existing (AI/user preference)
        existing_smooth = params.get('smoothing_factor', 0.25)
        params['smoothing_factor'] = float(np.clip(
            existing_smooth * 0.4 + auto_smooth * 0.6, 0.05, 0.50
        ))

        # ── FIX 1-A: Apply alpha mask BEFORE enforce_polarity ──────────────────
        # If we have an alpha mask, blank-out (white) any pixel outside the subject
        # BEFORE the polarity check. This prevents the background from being treated
        # as ink when the image has no transparent layer.
        if self.alpha_mask is not None:
            alpha_resized = self._resize_alpha(self.alpha_mask, binary.shape)
            binary = binary.copy()
            binary[~alpha_resized] = 255  # force background to white

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

    def _run_artwork(self, image: np.ndarray, params: Dict[str, Any], image_class: str = 'artwork') -> PipelineResult:
        from core.router_utils import preprocess_artwork, apply_halftone_pipeline, apply_upscale_factor
        logger.info(f"[_run_artwork] Params: halftone={params.get('halftone')}, lpi={params.get('lpi')}, dpi={params.get('dpi')}, colors={params.get('colors')}, image_class={image_class}")
        denoise_strength = params.get('denoise_strength', 9)
        upscale_factor = params.get('upscale_factor', 1.0)
        preprocessed = preprocess_artwork(image, denoise_strength=denoise_strength)
        preprocessed = apply_upscale_factor(preprocessed, upscale_factor)
        target_colors = params.get('colors', 1)
        should_halftone = params.get('halftone', False)

        if target_colors == 1 and not should_halftone:
            from core.router_utils import _make_single_color_separation
            gray = cv2.cvtColor(preprocessed, cv2.COLOR_BGR2GRAY)

            # ── FIX 1-B: Apply alpha mask to gray BEFORE binarization ──────────
            # This prevents the white/light background pixels from being classified
            # as ink when the background hasn't been removed (no transparency).
            if self.alpha_mask is not None:
                alpha_resized = self._resize_alpha(self.alpha_mask, gray.shape)
                gray = gray.copy()
                gray[~alpha_resized] = 255  # background → white before Otsu

            # ── FIX 5: Border-based background detection for JPEG/no-alpha ────
            # When alpha_mask is all-opaque or None, the alpha check does nothing.
            # Detect background by analyzing image borders; if consistently light,
            # flood-fill from corners to remove background before Otsu.
            if self.alpha_mask is not None and np.mean(alpha_resized) > 0.90:
                needs_floodfill = True
            elif self.alpha_mask is None:
                needs_floodfill = True
            else:
                needs_floodfill = False

            if needs_floodfill:
                h, w = gray.shape
                border_sample = np.concatenate([
                    gray[:3, :].ravel(), gray[-3:, :].ravel(),
                    gray[:, :3].ravel(), gray[:, -3:].ravel(),
                ])
                if float(np.median(border_sample)) > 200:
                    ff_mask = np.zeros((h+2, w+2), dtype=np.uint8)
                    for sx, sy in [(0,0), (w-1,0), (0,h-1), (w-1,h-1)]:
                        cv2.floodFill(gray, ff_mask, (sx, sy), 255,
                                      loDiff=20, upDiff=20)

            m = edge_aware_binarize(gray, use_adaptive=False, denoise_strength=params.get('denoise_strength', 9))

            # ── FIX 1-C: enforce_polarity AFTER alpha-mask application ──────────
            # Pass alpha_mask so polarity can use it as a secondary check,
            # but the primary guard (above) already white-filled the background.
            m = self.controller.enforce_polarity(m, stage="artwork_1color", alpha_mask=self.alpha_mask)

            # Final boundary clip: make absolutely sure nothing is outside alpha
            if self.alpha_mask is not None:
                alpha_resized = self._resize_alpha(self.alpha_mask, m.shape)
                m = m.copy()
                m[~alpha_resized] = 255

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
            # ── FIX 1-D: Multi-color — strip background color from separations ──
            # ColorSeparator may include the background as a cluster.
            # We tell it to exclude colors that are dominated by the alpha boundary.
            sep_result = self.separator.separate(
                preprocessed,
                num_colors=target_colors,
                alpha_mask=self.alpha_mask,
            )

            # Post-separation background filter:
            # Remove any color cluster that is ≥ 80 % outside the alpha region.
            if self.alpha_mask is not None:
                sep_result = self._filter_background_colors(sep_result, self.alpha_mask, preprocessed.shape)

            masks = self.mask_gen.generate_masks(preprocessed, sep_result, grayscale_output=should_halftone)
        
        if should_halftone:
            # We need to wrap params in an object that looks like args for router_utils
            class ParamProxy:
                def __init__(self, p): 
                    self.p = p
                    self._halftone_raster_dpi = None  # Will be set by apply_halftone_pipeline
                    # Critical: Propagate explicit overrides for safety rules
                    self.overrides = p.get('overrides', [])
                def __getattr__(self, k):
                    # ── FIX 2-A: dot_size / dot_shape disambiguation ────────────
                    # The CLI uses 'dot-shape' (hyphen) while internal params use
                    # 'dot_shape' (underscore).  Previously ParamProxy only exposed
                    # the exact key, causing apply_halftone_pipeline to fall back to
                    # 'round' even when the user picked a different shape.
                    if k == 'dot_shape':
                        return self.p.get('dot_shape') or self.p.get('dot-shape') or 'round'
                    if k == 'dot-shape':
                        return self.p.get('dot-shape') or self.p.get('dot_shape') or 'round'
                    if k not in self.p and k not in ('_halftone_raster_dpi', 'overrides'):
                        raise AttributeError(f"No such parameter: {k}")
                    val = self.p.get(k)
                    if k in ['lpi', 'dpi', 'halftone', 'mesh_count']:
                        logger.info(f"[ParamProxy] Accessing {k} = {val}")
                    return val

            logger.info(f"[PipelineRouter] Applying halftone with params: lpi={params.get('lpi')}, dpi={params.get('dpi')}, dot_shape={params.get('dot_shape') or params.get('dot-shape')}, image_class={image_class}")
            proxy = ParamProxy(params)
            masks = apply_halftone_pipeline(masks, proxy, self.halftone_gen, image_class=image_class)
            # Propagate raster DPI that apply_halftone_pipeline stored on proxy
            params['_halftone_raster_dpi'] = proxy._halftone_raster_dpi

        processed_masks = []
        _binarize_denoise = params.get('denoise_strength', 9)
        for i, m in enumerate(masks):
            # For non-halftone: binarize to 0/255
            # For halftone: keep grayscale values (0-255) for dot patterns
            if not should_halftone:
                m = edge_aware_binarize(m, use_adaptive=False, denoise_strength=_binarize_denoise)
                m = (m > 127).astype(np.uint8) * 255  # Binary: only for non-halftone
            
            if self.alpha_mask is not None:
                alpha_resized = self._resize_alpha(self.alpha_mask, m.shape)
                m = m.copy()
                m[~alpha_resized] = 255
            
            # Note: For halftone, we keep m as grayscale (0-255) to preserve dot patterns
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
        from core.router_utils import preprocess_photo, _make_single_color_separation, apply_upscale_factor
        from core.raster_halftone import RasterHalftoneEngine, RasterHalftoneConfig
        denoise_strength = params.get('denoise_strength', 15)
        upscale_factor = params.get('upscale_factor', 1.0)
        preprocessed_gray = preprocess_photo(image, denoise_strength=denoise_strength)
        preprocessed_gray = apply_upscale_factor(preprocessed_gray, upscale_factor)
        
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

    # ── FIX 1-D helper ────────────────────────────────────────────────────────
    def _filter_background_colors(
        self,
        sep_result: Dict,
        alpha_mask: np.ndarray,
        image_shape: Tuple[int, ...],
    ) -> Dict:
        """
        Remove color clusters that predominantly fall outside the alpha region.

        A cluster is considered 'background' when ≥ 80 % of its pixels lie
        outside the subject (alpha_mask == False).  We drop those clusters and
        renumber the label_map so downstream code remains consistent.
        """
        label_map = sep_result.get('label_map')
        if label_map is None:
            return sep_result

        # Resize alpha to label_map resolution
        alpha_resized = cv2.resize(
            alpha_mask.astype(np.uint8),
            (label_map.shape[1], label_map.shape[0]),
            interpolation=cv2.INTER_NEAREST,
        ).astype(bool)

        keep_indices = []
        for idx in range(sep_result.get('num_colors', 0)):
            cluster_mask = label_map == idx
            total_px = np.sum(cluster_mask)
            if total_px == 0:
                keep_indices.append(idx)
                continue
            outside_px = np.sum(cluster_mask & ~alpha_resized)
            outside_ratio = outside_px / total_px
            if outside_ratio < 0.80:
                keep_indices.append(idx)
            else:
                logger.info(
                    f"[PipelineRouter] Dropping background cluster {idx} "
                    f"({outside_ratio*100:.1f}% outside alpha)"
                )

        if len(keep_indices) == sep_result.get('num_colors', 0):
            return sep_result  # nothing to drop

        # Rebuild sep_result with only kept clusters
        new_label_map = np.full_like(label_map, -1)
        for new_idx, old_idx in enumerate(keep_indices):
            new_label_map[label_map == old_idx] = new_idx

        sep_result = dict(sep_result)  # shallow copy — don't mutate caller's dict
        sep_result['label_map'] = new_label_map
        sep_result['num_colors'] = len(keep_indices)

        for key in ('colors', 'color_names', 'color_info'):
            if key in sep_result and isinstance(sep_result[key], list):
                sep_result[key] = [sep_result[key][i] for i in keep_indices]

        if 'centers' in sep_result and hasattr(sep_result['centers'], '__len__'):
            sep_result['centers'] = sep_result['centers'][keep_indices]

        logger.info(
            f"[PipelineRouter] Background filter: kept {len(keep_indices)}/{sep_result.get('num_colors', '?')} clusters → {keep_indices}"
        )
        return sep_result

    def _resize_alpha(self, alpha: np.ndarray, shape: Tuple[int, int]) -> np.ndarray:
        if alpha.shape == shape: return alpha
        return cv2.resize(alpha.astype(np.uint8), (shape[1], shape[0]), interpolation=cv2.INTER_NEAREST).astype(bool)
