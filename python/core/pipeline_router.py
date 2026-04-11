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

def edge_aware_binarize(gray: np.ndarray, use_adaptive: bool = False) -> np.ndarray:
    """
    Improved binarization that preserves solid fill for large text characters.
    FIX A-07: Use Otsu threshold (not hardcoded 180).
    """
    bilateral = cv2.bilateralFilter(gray, 9, 75, 75)

    _, th_otsu = cv2.threshold(bilateral, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    h, w = bilateral.shape[:2]
    # FINAL FIX: allow completely disabling adaptive threshold
    if use_adaptive and min(h, w) < 800:
        block_size = max(31, min(101, int(min(h, w) * 0.1) | 1))
        th_adaptive = cv2.adaptiveThreshold(
            bilateral, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, block_size, 5
        )
        base = cv2.bitwise_and(th_otsu, th_adaptive)
    else:
        # Large images, or when explicitly requested: Otsu alone
        base = th_otsu

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    base = cv2.morphologyEx(base, cv2.MORPH_CLOSE, kernel, iterations=1)
    
    # FINAL FIX: enforce strict binary integrity
    return (base > 127).astype(np.uint8) * 255

@dataclass
class PipelineResult:
    masks: List[np.ndarray]
    separation_result: Dict
    image_class: str
    skip_binarization: bool = False
    effective_smoothing: float = None
    # FIX A-12/C-10: Actual DPI of the mask pixels (may differ from output_dpi
    # when the raster halftone engine runs at a higher raster_dpi).
    mask_dpi: Optional[int] = None

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

        # FIX 5: Improved alpha synthesis using flood-fill from all four corners.
        # The previous border-sampling approach picked the most common border color
        # and used a flat tolerance=5, which failed on JPEG-compressed images where
        # the border may have mixed artifacts, and incorrectly silenced real ink pixels
        # that happened to share the background color.
        # FloodFill from corners is connectivity-aware — it only reaches pixels that
        # are contiguously connected to the border at the given tolerance, which is
        # the correct semantic for "background".
        if self.alpha_mask is None:
            h, w = image.shape[:2]
            gray_for_flood = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()
            flood_mask = np.zeros((h + 2, w + 2), dtype=np.uint8)
            # JPEG tolerance: use 15 (larger than original 5) so compression artifacts
            # don't isolate background pixels from the flood fill.
            FLOOD_TOLERANCE = 15
            corners = [(0, 0), (0, w - 1), (h - 1, 0), (h - 1, w - 1)]
            bg_fill = gray_for_flood.copy()
            for (fy, fx) in corners:
                if 0 <= fy < h and 0 <= fx < w:
                    cv2.floodFill(
                        bg_fill, flood_mask,
                        seedPoint=(fx, fy),
                        newVal=0,
                        loDiff=FLOOD_TOLERANCE, upDiff=FLOOD_TOLERANCE,
                        flags=cv2.FLOODFILL_MASK_ONLY | (1 << 8),
                    )
            # flood_mask pixels == 1 are background (reached by flood fill)
            # NOTE: flood_mask is (h+2, w+2); crop to image size
            bg_region = flood_mask[1:-1, 1:-1].astype(bool)
            self.alpha_mask = bg_region   # True = background, False = foreground ink
            logger.info(
                f"[PipelineRouter] FIX5: FloodFill alpha synthesis — "
                f"BG={np.sum(bg_region)}px, FG={np.sum(~bg_region)}px "
                f"(tolerance={FLOOD_TOLERANCE})"
            )

        # user_selected_halftone is the ONLY authority for halftone routing.
        # SmartAnalyzer and AI bridge are advisory for image_class only.
        user_selected_halftone = getattr(args, 'halftone', False)
        logger.info(f"[PipelineRouter] ENTRY: user_selected_halftone={user_selected_halftone}, img_type={img_type}")

        # CRITICAL: If user selected halftone, bypass all auto-routing and go
        # straight to artwork pipeline.  No AI/analyzer override allowed.
        if user_selected_halftone:
            logger.info("[PipelineRouter] USER SELECTED HALFTONE → forcing ARTWORK pipeline")
            return self._run_artwork(image, args, analysis)

        if img_type == 'auto':
            try:
                from core.ai_vision_bridge import analyze_image as ai_analyze, apply_to_args, is_available
                if is_available():
                    ai_result = ai_analyze(image)
                    if ai_result is not None:
                        # FIX 3: Preserve user-locked halftone flag across apply_to_args.
                        # apply_to_args may overwrite args.halftone if the AI model
                        # returns a halftone recommendation — we must not let it.
                        halftone_before = args.halftone
                        apply_to_args(ai_result, args)
                        args.halftone = halftone_before  # RESTORE — user intent is law

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

        if image_class == 'low_quality':
            # FIX: Explicit LOW_QUALITY route — previously fell through to artwork
            # silently, giving no feedback to the operator about image quality issues.
            logger.warning(
                "[PipelineRouter] LOW_QUALITY image detected. "
                "Output quality will be degraded. Consider providing a higher-resolution source. "
                "Routing to artwork pipeline with conservative settings."
            )
            # Apply conservative settings to minimize artifacts on poor-quality input
            args.smoothing_factor = getattr(args, 'smoothing_factor', 0.20)
            return self._run_artwork(image, args, analysis)
        elif image_class == 'text_logo':
            # FIX 3 (separation always active): If the user requests multiple colors,
            # the text_logo shortcut (which skips KMeans) must not run.
            # Force _run_artwork so color separation is always executed.
            if getattr(args, 'colors', 1) > 1:
                logger.info(
                    f"[PipelineRouter] FIX3: colors={args.colors} — overriding text_logo → artwork "
                    "to ensure color separation runs"
                )
                return self._run_artwork(image, args, analysis)
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
        
        # FINAL FIX: disable adaptive threshold for text_logo (Otsu only)
        binary = edge_aware_binarize(gray, use_adaptive=False)
        
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
        
        # FINAL FIX: enforce strict binary integrity
        binary = (binary > 127).astype(np.uint8) * 255
        
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
            under_mask = ub_gen.generate_underbase(masks, choke_px=getattr(args, 'choke_px', 2))
            if under_mask is not None:
                masks.insert(0, under_mask)
                sep_result['colors'].insert(0, (255, 255, 255))
                sep_result['color_names'].insert(0, "White_Underbase")
                logger.info("[Prepress] White Underbase generated.")

        # 2. Ink Trapping
        trap_px = getattr(args, 'trapping_px', 0)
        if trap_px > 0:
            # FIX 4: Guard trapping against thin strokes.
            # Trapping expands every ink shape by trap_px pixels.
            # If the thinnest stroke in any mask is narrower than 2*trap_px,
            # the expansion merges adjacent strokes and destroys geometry.
            # Estimate minimum stroke width via distance transform:
            #   the maximum value of dt inside an ink region ≈ half the stroke width.
            min_half_stroke = float('inf')
            for m in masks:
                inv = cv2.bitwise_not(m)           # ink = 255
                dt  = cv2.distanceTransform(inv, cv2.DIST_L2, 3)
                half = float(dt.max())              # max radius of inscribed disk
                min_half_stroke = min(min_half_stroke, half)

            min_stroke_px = min_half_stroke * 2    # full width
            safe_to_trap  = min_stroke_px >= (2 * trap_px)

            if safe_to_trap:
                masks = ub_gen.apply_trapping(masks, trap_px=trap_px)
                logger.info(f"[Prepress] Trapping applied ({trap_px}px, min_stroke={min_stroke_px:.1f}px).")
            else:
                logger.warning(
                    f"[Prepress] Trapping SKIPPED — min stroke {min_stroke_px:.1f}px "
                    f"< 2×trap_px ({2*trap_px}px). Would destroy thin geometry."
                )

        return masks, sep_result

    def _run_artwork(self, image: np.ndarray, args: argparse.Namespace, analysis=None) -> PipelineResult:
        from core.router_utils import preprocess_artwork, apply_halftone_pipeline
        preprocessed = preprocess_artwork(image)

        if args.colors == 0:
            args.colors = analysis.num_colors if analysis else 4

        target_colors = args.colors

        # FIX 3 (separation decoupling): should_halftone is derived ONLY from
        # args.halftone (explicit user intent).  Analysis recommendations are
        # advisory for image-class routing only, never for halftone activation.
        # The early-return at route() already ensures that when user_selected_halftone
        # is True we are in this method — so args.halftone is always the authority.
        should_halftone = args.halftone

        # ─── FIX A-01: Three fully-separated routing branches ────────────────
        # The old code had a single KMeans block shared by both 1-color-halftone
        # and multi-color paths, leading to KMeans clustering a 1-cluster job then
        # feeding a near-binary result to the halftone engine (producing uniform
        # dot coverage over the background area).
        #
        # Branch 1: Non-halftone single color → fast binary path (unchanged)
        # Branch 2: Halftone single color     → grayscale direct, NO KMeans
        # Branch 3: Multi-color (±halftone)   → KMeans path (unchanged)
        # ─────────────────────────────────────────────────────────────────────

        if target_colors == 1 and not should_halftone:
            # ── Branch 1: Non-halftone single color ──────────────────────────
            from core.router_utils import _make_single_color_separation
            gray = cv2.cvtColor(preprocessed, cv2.COLOR_BGR2GRAY)
            
            # FINAL FIX: target_colors == 1 is solid artwork. Disable adaptive threshold.
            m = edge_aware_binarize(gray, use_adaptive=False)
            m = self.controller.enforce_polarity(
                m,
                stage="artwork_1color",
                alpha_mask=self.alpha_mask
            )
            m = (m > 127).astype(np.uint8) * 255
            sep_result = _make_single_color_separation(image)
            masks = [m]

        elif target_colors == 1 and should_halftone:
            # ── Branch 2: Single-color halftone ──────────────────────────────
            # FIX A-01: Bypass KMeans entirely — use the grayscale channel
            # directly.  KMeans on 1 cluster just returns the mean color, which
            # produces a near-uniform intensity input to the halftone engine and
            # places dots over background regions.
            from core.router_utils import _make_single_color_separation
            logger.info("[PipelineRouter] Branch 2: single-color halftone — grayscale direct (no KMeans)")
            gray = cv2.cvtColor(preprocessed, cv2.COLOR_BGR2GRAY)

            # Set transparent pixels to white (background = no ink)
            if self.alpha_mask is not None:
                alpha_resized = self.alpha_mask
                if gray.shape != self.alpha_mask.shape:
                    alpha_resized = cv2.resize(
                        self.alpha_mask.astype(np.uint8),
                        (gray.shape[1], gray.shape[0]),
                        interpolation=cv2.INTER_NEAREST
                    ).astype(bool)
                gray = gray.copy()
                gray[~alpha_resized] = 255
                logger.info(f"[PipelineRouter] Branch 2: applied alpha mask ({np.sum(~alpha_resized)} transparent px → 255)")

            sep_result = _make_single_color_separation(image)
            # Grayscale mask — will be passed directly to halftone engine
            masks = [gray]

        else:
            # ── Branch 3: Multi-color separation (with optional halftone) ────
            kmeans_colors = max(target_colors, 2) if should_halftone else target_colors
            logger.info(f"[PipelineRouter] Branch 3: color separation — {kmeans_colors} colors, grayscale_output={should_halftone}")
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
                # FINAL FIX: solid artwork, disable adaptive threshold
                m = edge_aware_binarize(m, use_adaptive=False)
                m = (m > 127).astype(np.uint8) * 255

            # Apply alpha mask: transparent pixels must be background (255)
            if self.alpha_mask is not None:
                if m.shape != self.alpha_mask.shape:
                    alpha_resized = cv2.resize(
                        self.alpha_mask.astype(np.uint8),
                        (m.shape[1], m.shape[0]),
                        interpolation=cv2.INTER_NEAREST
                    ).astype(bool)
                else:
                    alpha_resized = self.alpha_mask
                m = m.copy()
                m[~alpha_resized] = 255
                logger.info(f"[PipelineRouter] Mask {i}: {np.sum(~alpha_resized)} transparent px → 255")

            # FINAL FIX: binary integrity everywhere
            m = (m > 127).astype(np.uint8) * 255

            try:
                self.controller.validate_mask_coverage(m, f"artwork_mask_{i}")
                processed_masks.append(m)
            except ValueError:
                continue

        # PRO PREPRESS: Apply Underbase and Trapping
        processed_masks, sep_result = self._apply_pro_prepress(processed_masks, args, sep_result)

        if should_halftone:
            export_class = 'artwork_halftone'
        else:
            export_class = 'artwork'

        # FIX A-12/C-10: Record the actual mask DPI so the exporter can compute
        # physical sizes correctly (raster halftone runs at raster_dpi, not output_dpi).
        mask_dpi = getattr(args, '_halftone_raster_dpi', getattr(args, 'dpi', 300))

        return PipelineResult(
            masks=processed_masks,
            separation_result=sep_result,
            image_class=export_class,
            skip_binarization=False,
            effective_smoothing=args.smoothing_factor,
            mask_dpi=mask_dpi,
        )

    def _run_photo(self, image: np.ndarray, args: argparse.Namespace, analysis=None) -> PipelineResult:
        """Photo Pipeline: Grayscale -> CLAHE -> High-DPI Raster Halftone."""
        from core.router_utils import preprocess_photo, _make_single_color_separation
        from core.raster_halftone import RasterHalftoneEngine, RasterHalftoneConfig
        
        preprocessed_gray = preprocess_photo(image)

        # Use RasterHalftoneEngine at high DPI for professional output
        output_dpi = getattr(args, 'dpi', 450)
        raster_dpi = max(1200, output_dpi * 2)
        # FIX 2/DPI: Store on args so mask_dpi propagation in _run_photo matches
        # the same key used by apply_halftone_pipeline.
        args._halftone_raster_dpi = raster_dpi
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
