import cv2
import numpy as np
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

# ── Lazy import of anti_alias_preserve (avoids circular deps) ─────────────────
def _get_preserver(image_type: str):
    """Return an AntiAliasPreserver preset for the given image type."""
    try:
        from core.anti_alias_preserve import AntiAliasPreserver
        presets = {
            'logo':  AntiAliasPreserver.for_logo,
            'photo': AntiAliasPreserver.for_photo,
            'mixed': AntiAliasPreserver.for_mixed,
        }
        return presets.get(image_type, AntiAliasPreserver.for_mixed)()
    except ImportError:
        logger.warning("[RouterUtils] anti_alias_preserve not available — using raw image")
        return None

def preprocess_text_logo(image: np.ndarray) -> np.ndarray:
    """
    Edge-preserving preprocessing for logos/text.
    Phase 2 upgrade: uses AntiAliasPreserver (logo preset) before sharpening.
    NO binarization at this stage.
    """
    preserver = _get_preserver('logo')
    if preserver is not None:
        # AntiAliasPreserver returns grayscale for logos — convert back to BGR
        gray = preserver.process(image)
        bilat = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR) if len(gray.shape) == 2 else gray
    else:
        bilat = cv2.bilateralFilter(image, 5, 50, 50)
    # Sharpening pass (unsharp mask — less destructive than the 3×3 kernel)
    blurred = cv2.GaussianBlur(bilat, (0, 0), 1.0)
    sharpened = cv2.addWeighted(bilat, 1.5, blurred, -0.5, 0)
    return sharpened

def preprocess_artwork(image: np.ndarray) -> np.ndarray:
    """
    Edge-preserving preprocessing for illustrations (mixed preset).
    Phase 2 upgrade: AntiAliasPreserver with colour preservation.
    NO binarization at this stage.
    """
    preserver = _get_preserver('mixed')
    if preserver is not None:
        return preserver.process(image)
    # Fallback
    return cv2.bilateralFilter(image, 9, 75, 75)

def preprocess_photo(image: np.ndarray) -> np.ndarray:
    """
    Shadow/texture-preserving preprocessing for photographs (photo preset).
    Phase 2 upgrade: AntiAliasPreserver with gamma + bilateral for halftone.
    Output is grayscale (required by halftone engine).
    NO binarization at this stage.
    """
    preserver = _get_preserver('photo')
    if preserver is not None:
        return preserver.process(image)   # returns uint8 grayscale
    # Fallback
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    bilat = cv2.bilateralFilter(gray, 15, 75, 75)
    blurred = cv2.GaussianBlur(bilat, (5, 5), 1.0)
    return cv2.addWeighted(bilat, 1.5, blurred, -0.5, 0)

def _make_single_color_separation(image: np.ndarray, white_threshold: int = 240) -> dict:
    """Bypasses K-means for TEXT_LOGO / monochrome images."""
    h, w = image.shape[:2]
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    label_map = np.full((h, w), -1, dtype=np.int32)
    label_map[gray < white_threshold] = 0
    
    ink_pixels = int(np.sum(label_map == 0))
    coverage = (ink_pixels / label_map.size) * 100 if label_map.size > 0 else 0
    
    if ink_pixels > 0:
        if len(image.shape) == 3:
            center_bgr = np.mean(image[label_map == 0], axis=0).astype(np.float32)
        else:
            center_bgr = np.array([0, 0, 0], dtype=np.float32)
    else:
        center_bgr = np.array([0, 0, 0], dtype=np.float32)
    
    return {
        'label_map': label_map,
        'centers': np.array([center_bgr]),
        'num_colors': 1,
        'colors': [(0, 0, 0)],
        'color_names': ["Black"],
        'compactness': 0.0,
        'color_info': [{'index': 0, 'pixel_count': ink_pixels, 'percentage': coverage}]
    }

# FIX GROUP 5.3: Standard CMYK angles for multi-color halftone
CMYK_ANGLES = [45.0, 15.0, 75.0, 0.0]  # C, M, Y, K standard screen angles


def apply_halftone_pipeline(masks: List[np.ndarray], args, halftone_gen=None) -> List[np.ndarray]:
    """
    Decoupled halftone pipeline using high-DPI RasterHalftoneEngine.
    halftone_gen parameter is ignored (kept for API compatibility).
    """
    logger.info(f"[HalftonePipeline] ===== ENTERING with {len(masks)} masks =====")
    logger.info(f"[HalftonePipeline] Args: dpi={getattr(args, 'dpi', 'N/A')}, lpi={getattr(args, 'lpi', 'N/A')}, dot_shape={getattr(args, 'dot_shape', 'N/A')}")

    try:
        from core.raster_halftone import RasterHalftoneEngine, RasterHalftoneConfig
        logger.info("[HalftonePipeline] ✓ RasterHalftoneEngine imported successfully")
    except ImportError as e:
        logger.warning(f"[HalftonePipeline] RasterHalftoneEngine not available: {e}, falling back to legacy")
        if halftone_gen is None:
            try:
                from core.halftone_generator import HalftoneGenerator
                halftone_gen = HalftoneGenerator()
                logger.info("[HalftonePipeline] ✓ Legacy HalftoneGenerator initialized")
            except ImportError as e2:
                logger.error(f"[HalftonePipeline] HalftoneGenerator not available: {e2}")
                return masks
        return _apply_legacy_halftone(masks, args, halftone_gen)

    output_dpi = getattr(args, 'dpi', 450)

    # FIX 2: Unified raster_dpi formula — max(1200, output_dpi*2) everywhere.
    # For high detail mode, we push to 3600 DPI internally.
    if getattr(args, '_is_high_detail', False):
        raster_dpi = max(3600, output_dpi * 3)
    else:
        raster_dpi = max(1200, output_dpi * 2)
        
    logger.info(f"[HalftonePipeline] Config: output_dpi={output_dpi}, raster_dpi={raster_dpi}")

    # FIX A-12/C-10: Store the raster DPI on args so _run_artwork() can propagate
    # it to PipelineResult.mask_dpi and the exporter can use it for px_to_pt().
    args._halftone_raster_dpi = raster_dpi

    # FIX: Delegate LPI validation to PrintJobConfig — single source of truth.
    # Previously this block re-implemented mesh/3.5 + dpi/4 inline, drifting from
    # print_job_config.validate_lpi() whenever one side was updated independently.
    mesh_count = getattr(args, 'mesh_count', 160)
    dpi_lpi_ratio = 4.5
    auto_lpi = min(150, max(65, int(output_dpi / dpi_lpi_ratio)))
    requested_lpi = args.lpi if args.lpi != 85 else auto_lpi
    try:
        from core.print_job_config import PrintJobConfig
        _job_cfg = PrintJobConfig(mesh_count=mesh_count, dpi=output_dpi)
        effective_lpi = _job_cfg.validate_lpi(requested_lpi, output_dpi=output_dpi, auto_fix=True)
        max_safe_lpi = _job_cfg.max_safe_lpi(output_dpi)
    except Exception as _e:
        # Fallback: inline formula so the pipeline never crashes on import error.
        logger.warning(f"[HalftonePipeline] PrintJobConfig unavailable ({_e}), using inline LPI fallback")
        mesh_ceiling = int(mesh_count / 3.5)
        dpi_ceiling  = output_dpi // 4
        max_safe_lpi = max(25, min(mesh_ceiling, dpi_ceiling))
        effective_lpi = min(requested_lpi, max_safe_lpi)

    logger.info(f"[HalftonePipeline] Final LPI: {effective_lpi} (DPI={output_dpi}, mesh={mesh_count}, max_safe={max_safe_lpi})")
    result = []
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    for i, mask in enumerate(masks):
        total_pixels = mask.size
        design_pixels = np.sum(mask < 128)
        coverage_percentage = (design_pixels / total_pixels) * 100

        if coverage_percentage < 1.0:
            logger.warning(f"[Halftone] Skipping empty mask {i+1} ({coverage_percentage:.1f}% coverage)")
            result.append(mask)
            continue

        if coverage_percentage > 95.0:
            # FIX 4: Near-solid mask passed as-is to avoid halftone on flood-fill areas.
            # RISK: If this is a legitimate dark design (not a background fill), the lack
            # of halftone may cause ink flooding on press.  Operator must verify.
            logger.warning(
                f"[Halftone] Mask {i+1} has {coverage_percentage:.1f}% ink coverage — "
                f"exceeds 95%% threshold. Skipping halftone to avoid dot merging. "
                f"VERIFY on press: if this is a dark tone area (not solid black), "
                f"consider reducing LPI or using solid-ink mode instead."
            )
            result.append(mask)
            continue

        enhanced = mask.astype(np.uint8) if mask.dtype != np.uint8 else mask.copy()
        unique_vals = np.unique(enhanced)
        is_binary_mask = len(unique_vals) <= 2
        if not is_binary_mask:
            # required: grayscale must be cleaned (bilateral filter required before halftone dot generation)
            enhanced = cv2.bilateralFilter(enhanced, 5, 50, 50)
            enhanced = clahe.apply(enhanced)

        angle = CMYK_ANGLES[i % 4]
        dot_shape = getattr(args, 'dot_shape', 'round')

        raster_cfg = RasterHalftoneConfig(
            lpi=effective_lpi,
            dpi=raster_dpi,
            angle=angle,
            dot_fn=dot_shape,
            gamma=1.6,
            oversample=2,
            source_dpi=output_dpi,
        )
        ht_engine = RasterHalftoneEngine(raster_cfg)
        ht = ht_engine.generate(enhanced)
        
        # FINAL FIX: enforce strict binary integrity on halftone dots
        ht = (ht > 127).astype(np.uint8) * 255
        result.append(ht)

    logger.info(f"[Halftone] Raster halftone @ {raster_dpi} DPI, {effective_lpi} LPI")
    return result


def _apply_legacy_halftone(masks: List[np.ndarray], args, halftone_gen) -> List[np.ndarray]:
    """Fallback legacy halftone if RasterHalftoneEngine unavailable."""
    dpi_lpi_ratio = 4.5
    auto_lpi = min(150, max(65, int(args.dpi / dpi_lpi_ratio)))
    effective_lpi = args.lpi if args.lpi != 85 else auto_lpi

    # FIX A-03: Apply the same corrected formula as the primary path
    mesh_count = getattr(args, 'mesh_count', 160)
    mesh_ceiling = mesh_count // 4
    dpi_ceiling  = args.dpi // 4
    max_safe_lpi = max(25, min(mesh_ceiling, dpi_ceiling))
    if effective_lpi > max_safe_lpi:
        logger.warning(f"[LegacyHalftone] LPI {effective_lpi} clamped to {max_safe_lpi} (mesh={mesh_count}, dpi={args.dpi})")
        effective_lpi = max_safe_lpi

    logger.info(f"[LegacyHalftone] Auto LPI: {effective_lpi} (DPI={args.dpi}, mesh={mesh_count}, max_safe={max_safe_lpi})")
    result = []
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    for i, mask in enumerate(masks):
        total_pixels = mask.size
        design_pixels = np.sum(mask < 128)
        coverage_percentage = (design_pixels / total_pixels) * 100
        if coverage_percentage < 1.0:
            result.append(mask)
            continue
        if coverage_percentage > 95.0:
            # FIX 4: Same flood-risk warning as primary halftone path.
            logger.warning(
                f"[LegacyHalftone] Mask {i+1} has {coverage_percentage:.1f}% ink coverage — "
                f"exceeds 95%% threshold. Skipping halftone. VERIFY on press for flood risk."
            )
            result.append(mask)
            continue
        enhanced = mask.astype(np.uint8) if mask.dtype != np.uint8 else mask.copy()
        unique_vals = np.unique(enhanced)
        is_binary_mask = len(unique_vals) <= 2
        if not is_binary_mask:
            enhanced = clahe.apply(enhanced)
        angle = CMYK_ANGLES[i % 4]
        dot_shape = getattr(args, 'dot_shape', 'round')
        ht = halftone_gen.generate(enhanced, lpi=effective_lpi, angle=angle,
                                   dot_shape=dot_shape, dpi=args.dpi, gamma=1.6)
        
        # FINAL FIX: enforce strict binary integrity on legacy halftone
        ht = (ht > 127).astype(np.uint8) * 255
        result.append(ht)
    logger.info(f"[HalftonePipeline] ===== COMPLETE - {len(result)} masks processed =====")
    return result
