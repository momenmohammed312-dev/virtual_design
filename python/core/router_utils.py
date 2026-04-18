import cv2
import numpy as np
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

def edge_aware_binarize(gray: np.ndarray, use_adaptive: bool = False) -> np.ndarray:
    """
    Production-grade binarization for vector extraction.
    Ensures: Bilateral (noise) -> Slight Blur (anti-spike) -> Otsu (integrity).
    """
    # 1. Bilateral filter treats surfaces vs edges differently
    bilateral = cv2.bilateralFilter(gray, 9, 75, 75)
    
    # 2. Slight Gaussian blur to prevent findContours spikes/artifacts
    # High-quality vectorization needs slightly anti-aliased transitions
    smooth = cv2.GaussianBlur(bilateral, (3, 3), 0.5)

    # 3. Primary Otsu Thresholding
    _, th_otsu = cv2.threshold(smooth, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    h, w = smooth.shape[:2]
    # Adaptive thresholding for smaller complex logos
    if use_adaptive and min(h, w) < 800:
        block_size = max(31, min(101, int(min(h, w) * 0.1) | 1))
        th_adaptive = cv2.adaptiveThreshold(
            smooth, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, block_size, 5
        )
        # Intersection preserves only strong features
        base = cv2.bitwise_and(th_otsu, th_adaptive)
    else:
        base = th_otsu

    # 4. Morphological hardening
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    base = cv2.morphologyEx(base, cv2.MORPH_CLOSE, kernel, iterations=1)
    
    return (base > 127).astype(np.uint8) * 255

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
    # Subtle Sharpening (less destructive for text)
    blurred = cv2.GaussianBlur(bilat, (0, 0), 0.5)
    sharpened = cv2.addWeighted(bilat, 1.3, blurred, -0.3, 0)
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
        mesh_safe = mesh_count if mesh_count is not None else 160
        mesh_ceiling = int(mesh_safe / 3.5)
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

        # SAFETY CHECK: Near-solid coverage handling
        if coverage_percentage > 95.0:
            # Policy: If User EXPLICITLY forced halftone (Level 1), obey even if solid.
            # Otherwise (Auto/Default), skip to avoid flooding.
            is_explicit = getattr(args, 'halftone', False) and 'halftone' in getattr(args, 'overrides', [])
            
            if is_explicit:
                logger.info(f"[Halftone] Mask {i+1} is {coverage_percentage:.1f}% solid but FORCE HALFTONE is ON. Proceeding.")
            else:
                # FIX 4: Near-solid mask passed as-is to avoid halftone on flood-fill areas.
                logger.warning(
                    f"[Halftone] Mask {i+1} has {coverage_percentage:.1f}% ink coverage — "
                    f"exceeds 95%% threshold. Skipping halftone (Auto-Safe). "
                    f"Use Force Halftone to override."
                )
                result.append(mask)
                continue

        # FIX 2b: [Halftone Coverage] Binary mask -> edge-softened gradient
        enhanced_raw = mask.astype(np.uint8) if mask.dtype != np.uint8 else mask.copy()
        unique_vals = np.unique(enhanced_raw)
        is_binary_mask = len(unique_vals) <= 2

        if is_binary_mask:
            # Apply distance transform to create gradient near edges
            # This gives the halftone engine tonal information for edge dots
            ink_region = (enhanced_raw < 128).astype(np.uint8)
            dist = cv2.distanceTransform(ink_region, cv2.DIST_L2, 5)
            # Normalize: center of ink = 0 (dark), edge = gradient, background = 255 (white)
            max_dist = max(dist.max(), 1.0)
            dist_norm = np.clip(dist / min(max_dist, 20.0), 0, 1)  # cap at 20px feather
            # Convert to grayscale: ink center = 10, ink edge = 100, background = 255
            enhanced = np.where(ink_region == 1,
                               (10 + (1 - dist_norm) * 90).astype(np.uint8),
                               255).astype(np.uint8)
            logger.info(f"[Halftone] Binary mask -> edge-softened gradient for halftone")
        else:
            # required: grayscale must be cleaned (bilateral filter required before halftone dot generation)
            enhanced = cv2.bilateralFilter(enhanced_raw, 5, 50, 50)
            enhanced = clahe.apply(enhanced)

        angle = CMYK_ANGLES[i % 4]
        dot_shape = getattr(args, 'dot_shape', None) or 'round'

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
        
        # FINAL FIX: [Fix 2a] Mask constraint + micro noise removal
        # Prevent halftone dots from appearing outside artwork boundary
        # mask convention: 0=ink(artwork), 255=background
        if mask.ndim == 2:
            # Create strict artwork boundary (ink areas)
            artwork_binary = (mask < 128).astype(np.uint8) * 255
            
            # Slight erosion to prevent edge bleeding
            erode_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            artwork_eroded = cv2.erode(artwork_binary, erode_kernel, iterations=1)
            
            # Apply: keep halftone dots only inside artwork
            # ht convention: 0=ink dot, 255=background
            # We want to keep 0s (dots) only where artwork_eroded=255
            
            # FIX: Resize mask to match upsampled halftone result resolution
            if artwork_eroded.shape != ht.shape:
                artwork_eroded = cv2.resize(artwork_eroded, (ht.shape[1], ht.shape[0]), 
                                           interpolation=cv2.INTER_NEAREST)
            
            ht_constrained = np.where(artwork_eroded == 255, ht, 255)
            
            # Remove micro noise (connected components < 4px²)
            dots_only = (ht_constrained < 128).astype(np.uint8)
            n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(dots_only, connectivity=8)
            cleaned = ht_constrained.copy()
            for lbl in range(1, n_labels):
                if stats[lbl, cv2.CC_STAT_AREA] < 4:
                    cleaned[labels == lbl] = 255
            ht = cleaned
            
            # Log actual coverage after constraint
            final_coverage = 100 * np.mean(ht < 128)
            logger.info(f"[Halftone] Post-constraint coverage: {final_coverage:.2f}%")
        else:
            # ensure strict binary integrity on halftone dots
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
