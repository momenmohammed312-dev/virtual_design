import cv2
import numpy as np
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

def safe_float(val, default=0.0):
    """Safely cast value to float, handling strings or None."""
    if val is None: return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

def safe_int(val, default=0):
    """Safely cast value to int."""
    if val is None: return default
    try:
        if isinstance(val, str) and '.' in val:
            return int(float(val))
        return int(val)
    except (ValueError, TypeError):
        return default

def edge_aware_binarize(gray: np.ndarray, use_adaptive: bool = False, denoise_strength: int = 9) -> np.ndarray:
    """
    Production-grade binarization for vector extraction.
    Ensures: Bilateral (noise) -> Slight Blur (anti-spike) -> Otsu (integrity).
    MEMORY FIX: Uses chunk processing for large images to prevent MemoryError.
    
    Args:
        gray: Input grayscale image
        use_adaptive: Whether to use adaptive thresholding for small images
        denoise_strength: Bilateral filter diameter (0-15). Higher = stronger denoising.
                         Default 9 matches original hardcoded value.
    """
    h, w = gray.shape[:2]
    total_pixels = h * w
    
    # MEMORY SAFETY: Downscale very large images before processing
    max_safe_pixels = 4_000_000  # 4MP limit for binarization
    if total_pixels > max_safe_pixels:
        scale = np.sqrt(max_safe_pixels / total_pixels)
        new_h, new_w = int(h * scale), int(w * scale)
        logger.warning(f"[edge_aware_binarize] Image too large ({h}x{w}={total_pixels}px), downscaling to {new_h}x{new_w} for memory safety")
        gray = cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_AREA)
        h, w = new_h, new_w
        total_pixels = h * w
    
    # 1. Bilateral filter treats surfaces vs edges differently
    if denoise_strength > 0:
        sigma = denoise_strength * 10
        try:
            bilateral = cv2.bilateralFilter(gray, denoise_strength, sigma, sigma)
        except cv2.error as e:
            # If bilateral fails (memory), fall back to Gaussian
            logger.warning(f"[edge_aware_binarize] Bilateral filter failed, falling back to Gaussian: {e}")
            bilateral = cv2.GaussianBlur(gray, (denoise_strength, denoise_strength), sigma / 10)
    else:
        bilateral = gray
    
    # 2. Slight Gaussian blur to prevent findContours spikes/artifacts
    # High-quality vectorization needs slightly anti-aliased transitions
    smooth = cv2.GaussianBlur(bilateral, (3, 3), 0.5)

    # 3. Primary Otsu Thresholding
    _, th_otsu = cv2.threshold(smooth, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

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
    
    # MEMORY EFFICIENT: Use in-place operations to avoid extra allocations
    result = np.zeros_like(base, dtype=np.uint8)
    result[base > 127] = 255
    return result

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

def preprocess_text_logo(image: np.ndarray, denoise_strength: int = 5) -> np.ndarray:
    """
    Edge-preserving preprocessing for logos/text.
    Phase 2 upgrade: uses AntiAliasPreserver (logo preset) before sharpening.
    NO binarization at this stage.
    
    Args:
        image: Input BGR image
        denoise_strength: Bilateral filter diameter (0-15, 0=skip). Higher = stronger denoising.
    """
    preserver = _get_preserver('logo')
    if preserver is not None:
        # AntiAliasPreserver returns grayscale for logos — convert back to BGR
        gray = preserver.process(image)
        bilat = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR) if len(gray.shape) == 2 else gray
    else:
        # Apply denoise_strength-aware bilateral filter
        if denoise_strength > 0:
            sigma = denoise_strength * 10
            bilat = cv2.bilateralFilter(image, denoise_strength, sigma, sigma)
        else:
            bilat = image
    # Subtle Sharpening (less destructive for text)
    blurred = cv2.GaussianBlur(bilat, (0, 0), 0.5)
    sharpened = cv2.addWeighted(bilat, 1.3, blurred, -0.3, 0)
    return sharpened

def preprocess_artwork(image: np.ndarray, denoise_strength: int = 9) -> np.ndarray:
    """
    Edge-preserving preprocessing for illustrations (mixed preset).
    Phase 2 upgrade: AntiAliasPreserver with colour preservation.
    NO binarization at this stage.
    
    Args:
        image: Input BGR image
        denoise_strength: Bilateral filter diameter (0-15, 0=skip). Higher = stronger denoising.
    """
    preserver = _get_preserver('mixed')
    if preserver is not None:
        return preserver.process(image)
    # Fallback with denoise_strength-aware bilateral filter
    if denoise_strength > 0:
        sigma = denoise_strength * 10
        return cv2.bilateralFilter(image, denoise_strength, sigma, sigma)
    return image

def preprocess_photo(image: np.ndarray, denoise_strength: int = 15) -> np.ndarray:
    """
    Shadow/texture-preserving preprocessing for photographs (photo preset).
    Phase 2 upgrade: AntiAliasPreserver with gamma + bilateral for halftone.
    Output is grayscale (required by halftone engine).
    NO binarization at this stage.
    
    Args:
        image: Input BGR or grayscale image
        denoise_strength: Bilateral filter diameter (0-20, 0=skip). Higher = stronger denoising.
                         Photos typically benefit from higher values (10-20).
    """
    preserver = _get_preserver('photo')
    if preserver is not None:
        return preserver.process(image)   # returns uint8 grayscale
    # Fallback with denoise_strength-aware bilateral filter
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    if denoise_strength > 0:
        sigma = denoise_strength * 5  # Photos use lower sigma ratio for texture preservation
        bilat = cv2.bilateralFilter(gray, denoise_strength, sigma, sigma)
    else:
        bilat = gray
    blurred = cv2.GaussianBlur(bilat, (5, 5), 1.0)
    return cv2.addWeighted(bilat, 1.5, blurred, -0.5, 0)

def apply_upscale_factor(image: np.ndarray, upscale_factor: float, max_dimension: int = 3000) -> np.ndarray:
    """
    Apply AI-suggested upscale factor after preprocessing.
    This runs AFTER the DecisionOracle has determined the optimal upscale_factor.
    
    Args:
        image: Input image (BGR or grayscale)
        upscale_factor: Factor from AI/DecisionOracle (1.0-4.0, 1.0 = no change)
        max_dimension: Maximum allowed dimension in pixels (safety guard)
    
    Returns:
        Potentially upscaled image
    """
    if upscale_factor <= 1.0:
        return image
    
    h, w = image.shape[:2]
    new_w = int(w * upscale_factor)
    new_h = int(h * upscale_factor)
    
    # Safety guard: don't exceed max_dimension
    if max(new_w, new_h) > max_dimension:
        scale = max_dimension / max(new_w, new_h)
        new_w = int(new_w * scale)
        new_h = int(new_h * scale)
        logger.info(f"[UpscaleFactor] Capped to {max_dimension}px: {w}x{h} -> {new_w}x{new_h} (factor ~{scale * upscale_factor:.2f})")
    else:
        logger.info(f"[UpscaleFactor] Applied {upscale_factor:.2f}x: {w}x{h} -> {new_w}x{new_h}")
    
    # Use LANCZOS4 for quality upscale
    return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

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


def apply_halftone_pipeline(masks: List[np.ndarray], args, halftone_gen=None, image_class: str = 'auto') -> List[np.ndarray]:
    """
    Decoupled halftone pipeline using high-DPI RasterHalftoneEngine.
    halftone_gen parameter is ignored (kept for API compatibility).
    
    HYBRID MODE: For 'artwork' class with mixed edges + gradients, uses HybridHalftoneEngine
    which combines Vector dots (sharp edges) + Raster dots (smooth gradients).
    """
    print(f"🔵 [HalftonePipeline] ===== ENTERING with {len(masks)} masks =====", flush=True)
    print(f"🔵 [HalftonePipeline] Args: dpi={getattr(args, 'dpi', 'N/A')}, lpi={getattr(args, 'lpi', 'N/A')}, dot_shape={getattr(args, 'dot_shape', 'N/A')}, image_class={image_class}", flush=True)
    logger.info(f"[HalftonePipeline] ===== ENTERING with {len(masks)} masks =====")
    logger.info(f"[HalftonePipeline] Args: dpi={getattr(args, 'dpi', 'N/A')}, lpi={getattr(args, 'lpi', 'N/A')}, dot_shape={getattr(args, 'dot_shape', 'N/A')}, image_class={image_class}")
    
    # HYBRID HALFTONE: Use for artwork with mixed content (edges + gradients)
    use_hybrid = image_class == 'artwork' and getattr(args, '_use_hybrid_halftone', True)
    if use_hybrid:
        try:
            from core.hybrid_halftone import HybridHalftoneEngine, HybridHalftoneConfig
            logger.info("[HalftonePipeline] ✓ HybridHalftoneEngine selected for artwork")
        except ImportError:
            logger.warning("[HalftonePipeline] HybridHalftoneEngine not available, falling back to Raster")
            use_hybrid = False

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
    
    # FIX: Get LPI for DPI constraints
    current_lpi = getattr(args, 'lpi', 45)
    
    # FIX: DPI constraints based on LPI (industry standard: DPI = LPI * 16 ideal, max LPI * 20)
    # Screen printing practical limit: 300 DPI min, 2400 DPI max
    ideal_dpi = current_lpi * 16
    max_sensible_dpi = min(current_lpi * 20, 2400)  # Hard cap at 2400
    min_dpi = max(300, current_lpi * 8)  # Minimum 300 or LPI*8
    
    # Clamp user DPI to sensible range
    if output_dpi > max_sensible_dpi:
        logger.warning(f"[HalftonePipeline] DPI {output_dpi} exceeds sensible max {max_sensible_dpi} for LPI={current_lpi}, clamping")
        output_dpi = max_sensible_dpi
    elif output_dpi < min_dpi:
        logger.warning(f"[HalftonePipeline] DPI {output_dpi} below minimum {min_dpi} for LPI={current_lpi}, using minimum")
        output_dpi = min_dpi
    
    logger.info(f"[HalftonePipeline] DPI constraints: LPI={current_lpi}, ideal={ideal_dpi}, clamped DPI={output_dpi}")

    # FIX 2: Unified raster_dpi formula — smarter scaling based on actual needs.
    # For high detail mode, we push to higher internal resolution.
    # Raster DPI should be 2x output for quality, but capped reasonably.
    if getattr(args, '_is_high_detail', False):
        raster_dpi = min(max(1200, output_dpi * 2), 3600)
    else:
        raster_dpi = min(max(600, output_dpi * 2), 2400)
        
    logger.info(f"[HalftonePipeline] Config: output_dpi={output_dpi}, raster_dpi={raster_dpi}")

    # FIX A-12/C-10: Store the raster DPI on args so _run_artwork() can propagate
    # it to PipelineResult.mask_dpi and the exporter can use it for px_to_pt().
    args._halftone_raster_dpi = raster_dpi

    # FIX: Delegate LPI validation to PrintJobConfig — single source of truth.
    # Previously this block re-implemented mesh/3.5 + dpi/4 inline, drifting from
    # print_job_config.validate_lpi() whenever one side was updated independently.
    mesh_count = getattr(args, 'mesh_count', None)
    if mesh_count is None:
        mesh_count = 160  # Fallback to standard mesh
        logger.warning(f"[HalftonePipeline] mesh_count not provided, using fallback: {mesh_count}")
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
        # FIX: Use correct industry standard mesh/4.5 ratio
        mesh_ceiling = int(mesh_safe / 4.5)
        dpi_ceiling  = output_dpi // 4
        max_safe_lpi = max(25, min(mesh_ceiling, dpi_ceiling))
        effective_lpi = min(requested_lpi, max_safe_lpi)

    from core.per_layer_halftone import parse_dot_sizes_from_args, multiplier_to_lpi
    dot_sizes = parse_dot_sizes_from_args(args, len(masks))

    logger.info(f"[HalftonePipeline] Final Base LPI: {effective_lpi} (DPI={output_dpi}, mesh={mesh_count}, max_safe={max_safe_lpi})")
    result = []
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    for i, (mask, multiplier) in enumerate(zip(masks, dot_sizes)):
        layer_lpi = multiplier_to_lpi(effective_lpi, multiplier, mesh_count)
        try:
            total_pixels = mask.size
            design_pixels = np.sum(mask < 128)
            coverage_percentage = (design_pixels / total_pixels) * 100

            # Rule: Fallback to solid if coverage is too low (prevents faint/invisible dots)
            # Level 1 Override: If user forced it, we obey, otherwise fallback.
            user_forced_halftone = getattr(args, 'halftone', False) and 'halftone' in getattr(args, 'overrides', [])
            
            if coverage_percentage < 5.0 and not user_forced_halftone:
                logger.warning(f"[Halftone] Low coverage {coverage_percentage:.1f}% for mask {i+1} - Falling back to SOLID.")
                # Re-binarize for solid mode fallback
                _, binary = cv2.threshold(mask.astype(np.uint8) if mask.dtype != np.uint8 else mask, 127, 255, cv2.THRESH_BINARY)
                result.append(binary)
                continue

            if coverage_percentage < 1.0:
                logger.warning(f"[Halftone] Skipping empty mask {i+1} ({coverage_percentage:.1f}% coverage)")
                result.append(mask)
                continue

            # SAFETY CHECK: Near-solid coverage handling
            if coverage_percentage > 95.0:
                # Policy: If User EXPLICITLY forced halftone (Level 1), obey even if solid.
                # Otherwise (Auto/Default), skip to avoid flooding.
                if user_forced_halftone:
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
            dot_shape = getattr(args, 'dot_shape', None) or getattr(args, 'dot-shape', None) or 'round'

            # HYBRID HALFTONE: Use for artwork with mixed edges + gradients
            ht = None
            # Check if preview mode (greyscale dots for visualization)
            greyscale_preview = getattr(args, '_greyscale_preview', False)
            if use_hybrid:
                try:
                    from core.hybrid_halftone import HybridHalftoneConfig
                    hybrid_cfg = HybridHalftoneConfig(
                        lpi=layer_lpi,
                        dpi=raster_dpi,
                        angle=angle,
                        dot_shape=dot_shape,
                        gamma=1.6,
                        greyscale_output=greyscale_preview,
                    )
                    ht_engine = HybridHalftoneEngine(hybrid_cfg)
                    ht = ht_engine.generate(enhanced)
                    if greyscale_preview:
                        logger.info(f"[Halftone] ✅ Hybrid GREYSCALE halftone generated for mask {i+1}")
                    else:
                        logger.info(f"[Halftone] ✅ Hybrid BINARY halftone generated for mask {i+1}")
                except Exception as e:
                    print(f"❌ [Halftone] Hybrid halftone failed: {e}", flush=True)
                    logger.error(f"[Halftone] ❌ Hybrid halftone failed: {e}, falling back to raster")
                    import traceback
                    tb_str = traceback.format_exc()
                    print(f"[Halftone] Traceback: {tb_str}", flush=True)
                    logger.error(f"[Halftone] Traceback: {tb_str}")
                    ht = None  # Trigger fallback
            
            # FALLBACK: Use RasterHalftone if hybrid failed or not applicable
            if ht is None:
                try:
                    raster_cfg = RasterHalftoneConfig(
                        lpi=layer_lpi,
                        dpi=raster_dpi,
                        angle=angle,
                        dot_fn=dot_shape,
                        gamma=1.6,
                        oversample=2,
                        source_dpi=output_dpi,
                        greyscale_output=greyscale_preview,
                    )
                    ht_engine = RasterHalftoneEngine(raster_cfg)
                    ht = ht_engine.generate(enhanced)
                    if greyscale_preview:
                        logger.info(f"[Halftone] ✅ Raster GREYSCALE halftone generated for mask {i+1}")
                    else:
                        logger.info(f"[Halftone] ✅ Raster BINARY halftone generated for mask {i+1}")
                except Exception as e:
                    print(f"❌❌ [Halftone] RASTER HALFTONE FAILED: {e}", flush=True)
                    logger.error(f"[Halftone] ❌❌ RASTER HALFTONE ALSO FAILED: {e}")
                    import traceback
                    tb_str = traceback.format_exc()
                    print(f"[Halftone] Traceback: {tb_str}", flush=True)
                    logger.error(f"[Halftone] Traceback: {tb_str}")
                    # Last resort: return original mask
                    result.append(mask)
                    continue
        
        except Exception as e:
            error_msg = f"❌❌❌ [Halftone] CRITICAL ERROR processing mask {i+1}: {e}"
            print(error_msg, flush=True)
            logger.error(f"[Halftone] ❌❌❌ CRITICAL ERROR processing mask {i+1}: {e}")
            import traceback
            tb_str = traceback.format_exc()
            print(f"[Halftone] Traceback: {tb_str}", flush=True)
            logger.error(f"[Halftone] Traceback: {tb_str}")
            result.append(mask)  # Return original mask as fallback
            continue
        
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
    mesh_count = getattr(args, 'mesh_count', None)
    if mesh_count is None:
        mesh_count = 160
    # FIX: Use correct industry standard mesh/4.5 ratio
    mesh_ceiling = int(mesh_count / 4.5)
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
        dot_shape = getattr(args, 'dot_shape', None) or getattr(args, 'dot-shape', None) or 'round'
        ht = halftone_gen.generate(enhanced, lpi=effective_lpi, angle=angle,
                                   dot_shape=dot_shape, dpi=args.dpi, gamma=1.6)
        
        # FINAL FIX: enforce strict binary integrity on legacy halftone
        ht = (ht > 127).astype(np.uint8) * 255
        result.append(ht)
    logger.info(f"[HalftonePipeline] ===== COMPLETE - {len(result)} masks processed =====")
    return result
