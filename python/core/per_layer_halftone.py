import cv2
import numpy as np
import logging
import traceback

logger = logging.getLogger(__name__)

CMYK_ANGLES = [45.0, 15.0, 75.0, 0.0]

def parse_dot_sizes_from_args(args, num_layers):
    """
    Parses `--dot-sizes` string from CLI. Example: "1.0,0.8,1.2".
    If missing or invalid, fallbacks to `--dot-size` global multiplier.
    Multipliers are clamped between 0.5 and 1.5.
    """
    dot_sizes_raw = getattr(args, 'dot_sizes', None)
    global_size = getattr(args, 'dot_size', 1.0)
    
    if dot_sizes_raw:
        try:
            # Parse commas
            sizes = [float(x.strip()) for x in str(dot_sizes_raw).split(',') if x.strip()]
            # Clamp between 0.5 (Very Fine) and 1.5 (Very Bold)
            sizes = [max(0.5, min(1.5, s)) for s in sizes]
            
            # Pad or truncate to match num_layers
            if len(sizes) >= num_layers:
                return sizes[:num_layers]
            else:
                return sizes + [max(0.5, min(1.5, float(global_size)))] * (num_layers - len(sizes))
        except Exception as e:
            logger.warning(f"Failed to parse dot sizes {dot_sizes_raw}, using global fallback. Error: {e}")
            
    # Global fallback
    if global_size is None:
        global_size = 1.0
    return [max(0.5, min(1.5, float(global_size)))] * num_layers


def multiplier_to_lpi(base_lpi, multiplier, mesh_count):
    """
    Converts dot size multiplier to an effective LPI for halftone execution.
    - Larger dot -> smaller LPI -> coarse halftone
    - Smaller dot -> larger LPI -> fine halftone
    Applies safety bounds: 25 <= LPI <= mesh/3.5
    """
    if multiplier <= 0:
        multiplier = 0.7
        
    # Standardize: 0.7 is the "Normal" base.
    # If multiplier = 0.7, effective = base_lpi.
    # If multiplier = 1.0 (Bold), effective = base_lpi / (1.42) -> Lower LPI -> Larger dots.
    # If multiplier = 0.3 (Fine), effective = base_lpi / (0.42) -> Higher LPI -> Smaller dots.
    effective = base_lpi / (multiplier / 0.7)
    
    max_lpi = mesh_count / 3.5 if mesh_count else 150
    
    return int(max(25, min(max_lpi, effective)))


def apply_per_layer_halftone(masks, args, base_lpi, raster_dpi, dot_size_multipliers):
    """
    Applies halftone per layer with specific LPI adjusted by dot size multiplier.
    """
    mesh_count = getattr(args, 'mesh_count', 160)
    greyscale_preview = getattr(args, '_greyscale_preview', False)
    dot_shape = getattr(args, 'dot_shape', None) or getattr(args, 'dot-shape', None) or 'round'
    
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    result = []
    
    try:
        from core.raster_halftone import RasterHalftoneEngine, RasterHalftoneConfig
    except ImportError as e:
        logger.error(f"[PerLayerHalftone] RasterHalftoneEngine unavailable: {e}")
        return masks

    for i, (mask, multiplier) in enumerate(zip(masks, dot_size_multipliers)):
        try:
            total_pixels = mask.size
            design_pixels = np.sum(mask < 128)
            coverage_percentage = (design_pixels / total_pixels) * 100

            if coverage_percentage < 1.0:
                logger.warning(f"[Halftone] Skipping empty mask {i+1} ({coverage_percentage:.1f}% coverage)")
                result.append(mask)
                continue

            # Safety check: Near-solid coverage handling
            if coverage_percentage > 95.0:
                is_explicit = getattr(args, 'halftone', False) and 'halftone' in getattr(args, 'overrides', [])
                if is_explicit:
                    logger.info(f"[Halftone] Mask {i+1} is {coverage_percentage:.1f}% solid but FORCE HALFTONE is ON. Proceeding.")
                else:
                    logger.warning(f"[Halftone] Mask {i+1} exceeds 95% threshold. Skipping halftone (Auto-Safe).")
                    result.append(mask)
                    continue

            # Binary mask to edge-softened gradient
            enhanced_raw = mask.astype(np.uint8) if mask.dtype != np.uint8 else mask.copy()
            unique_vals = np.unique(enhanced_raw)
            is_binary_mask = len(unique_vals) <= 2

            if is_binary_mask:
                ink_region = (enhanced_raw < 128).astype(np.uint8)
                dist = cv2.distanceTransform(ink_region, cv2.DIST_L2, 5)
                max_dist = max(dist.max(), 1.0)
                dist_norm = np.clip(dist / min(max_dist, 20.0), 0, 1)
                enhanced = np.where(ink_region == 1,
                                   (10 + (1 - dist_norm) * 90).astype(np.uint8),
                                   255).astype(np.uint8)
            else:
                enhanced = cv2.bilateralFilter(enhanced_raw, 5, 50, 50)
                enhanced = clahe.apply(enhanced)

            # Apply multiplier and instantiate engine for this specific layer
            angle = CMYK_ANGLES[i % 4]
            layer_lpi = multiplier_to_lpi(base_lpi, multiplier, mesh_count)

            raster_cfg = RasterHalftoneConfig(
                lpi=layer_lpi,
                dpi=raster_dpi,
                angle=angle,
                dot_fn=dot_shape,
                gamma=1.6,
                oversample=2,
                source_dpi=getattr(args, 'dpi', 450),
                greyscale_output=greyscale_preview,
            )
            ht_engine = RasterHalftoneEngine(raster_cfg)
            ht = ht_engine.generate(enhanced)

            logger.info(f"[Halftone] Mask {i+1}: applied LPI={layer_lpi} (base={base_lpi}, mult={multiplier:.2f})")

            # Final constraint: Dots appear only inside artwork boundary
            if mask.ndim == 2:
                artwork_binary = (mask < 128).astype(np.uint8) * 255
                erode_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
                artwork_eroded = cv2.erode(artwork_binary, erode_kernel, iterations=1)
                
                if artwork_eroded.shape != ht.shape:
                    artwork_eroded = cv2.resize(artwork_eroded, (ht.shape[1], ht.shape[0]), 
                                               interpolation=cv2.INTER_NEAREST)
                
                ht_constrained = np.where(artwork_eroded == 255, ht, 255)
                
                # Remove micro noise
                dots_only = (ht_constrained < 128).astype(np.uint8)
                n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(dots_only, connectivity=8)
                cleaned = ht_constrained.copy()
                for lbl in range(1, n_labels):
                    if stats[lbl, cv2.CC_STAT_AREA] < 4:
                        cleaned[labels == lbl] = 255
                ht = cleaned
            else:
                ht = (ht > 127).astype(np.uint8) * 255

            result.append(ht)

        except Exception as e:
            logger.error(f"[Halftone] CRITICAL ERROR processing mask {i+1}: {e}\n{traceback.format_exc()}")
            result.append(mask)

    return result
