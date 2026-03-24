"""
main.py — Silk Screen Processing Pipeline (CLI Entry Point)
Virtual Design Silk Screen Studio

FIXES applied:
  - FATAL #3: Print OUTPUT_DIR: at the end so Dart can read it
  - FATAL #4: Print Step X/9 for each step so Dart can stream progress
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import cv2
import numpy as np

# ─── Optional imports with graceful fallback ─────────────────────────────────
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("ERROR:reportlab_missing:PDF export requires: pip install reportlab", flush=True)
    # Don't exit yet, fallback may be possible for PNG.

# Local imports
sys.path.insert(0, str(Path(__file__).parent))

from core.color_separator import ColorSeparator
from core.image_loader import load_image_safely
from core.mask_generator import MaskGenerator
from core.edge_cleaner import EdgeCleaner

# Try importing optional modules (halftone, binarizer, etc.)
try:
    from core.halftone_generator import HalftoneGenerator
    HAS_HALFTONE = True
except ImportError:
    HAS_HALFTONE = False

try:
    from core.binarizer import Binarizer
    HAS_BINARIZER = True
except ImportError:
    HAS_BINARIZER = False

try:
    from core.stroke_validator import StrokeValidator
    HAS_STROKE_VALIDATOR = True
except ImportError:
    HAS_STROKE_VALIDATOR = False

try:
    from core.registration_marks import (
        RegistrationMarksGenerator,
        RegistrationConfig,
        MarkStyle,
    )
    HAS_REG_MARKS = True
except ImportError as e:
    HAS_REG_MARKS = False
    print(f"[WARNING] Registration marks not available: {e}", flush=True)

try:
    from core.exporter import Exporter
    HAS_EXPORTER = True
except ImportError:
    HAS_EXPORTER = False

try:
    from core.pantone_library import PantoneLibrary
    HAS_PANTONE = True
except ImportError:
    HAS_PANTONE = False

# ─── Logging ────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
    stream=sys.stderr,  # stderr للـ logs، stdout للـ progress فقط
)
logger = logging.getLogger(__name__)

TOTAL_STEPS = 9


def _step(n: int, name: str) -> None:
    """
    طباعة تقدم الخطوة على stdout — Dart يقرأ هذا real-time.
    FATAL #4 fix: flush=True ضروري لضمان وصول السطر فوراً.
    """
    print(f"Step {n}/{TOTAL_STEPS}: {name}", flush=True)


def _output_dir_signal(path: str) -> None:
    """
    FATAL #3 fix: إخبار Dart بمسار output directory.
    يجب أن يكون آخر سطر يُطبَع على stdout.
    """
    print(f"OUTPUT_DIR:{path}", flush=True)


def _progress(overall_fraction: float, message: str = '') -> None:
    """
    طباعة تقدم دقيق بصيغة IPC بسيطة: PROGRESS:<0.0-1.0>:message
    Dart سيقرأ هذا السطر ويحدّث شريط التقدم بشكل فوري.
    """
    try:
        frac = float(overall_fraction)
    except Exception:
        frac = 0.0
    # Clamp
    if frac < 0:
        frac = 0.0
    if frac > 1:
        frac = 1.0
    print(f"PROGRESS:{frac:.4f}:{message}", flush=True)


def step2_5_underbase_creation(separation_result: Dict, args: argparse.Namespace) -> Dict:
    """
    Automatic underbase creation for dark colors.
    Adds white underbase layer that prints under all dark colors to improve print quality.
    """
    _step(2.5, "Underbase creation (automatic)")
    
    try:
        pantone_lib = PantoneLibrary()
        colors = separation_result["colors"]
        color_names = separation_result["color_names"]
        label_map = separation_result["label_map"]
        
        # Calculate dark color indices based on original colors before sorting
        original_colors = colors.copy()  # Save original colors
        dark_color_indices = []
        for i, color_rgb in enumerate(original_colors):
            # Find nearest Pantone
            pantone_match = pantone_lib.find_nearest_pantone(color_rgb)
            
            # Check if color is dark (needs underbase)
            brightness = sum(color_rgb) / 3.0
            
            dark_pantone_codes = [
                'Black', 'Process Black', 'Black 6', 'Black 7',
                'Navy Blue', 'Reflex Blue', 'Process Blue',
                'Rhodamine Red', 'Rubine Red', 'Warm Red',
                'Purple', 'Violet', 'Medium Purple'
            ]
            
            is_dark = (
                brightness < 128 or
                any(code in pantone_match.name for code in dark_pantone_codes) or
                pantone_match.name.startswith(('Black', 'Dark', 'Navy'))
            )
            
            # Exclude white underbase if already added (check color channels individually)
            r, g, b = int(color_rgb[0]), int(color_rgb[1]), int(color_rgb[2])
            is_white = (r > 240 and g > 240 and b > 240)
            
            if is_dark and not is_white: 
                dark_color_indices.append(i)
                logger.info(f"Dark color detected {i+1}: {pantone_match.name} (brightness: {brightness:.1f})")
        
        if not dark_color_indices or len(colors) <= 1:
            logger.info("No dark colors found or single color design, skipping underbase")
            return separation_result
        
        # Add white underbase layer at the beginning
        white_rgb = (255, 255, 255)
        
        # Store original label_map before shifting
        original_label_map = label_map.copy()
        
        # Shift all labels by 1 to make room for underbase
        new_label_map = label_map + 1
        new_label_map[label_map == -1] = -1  # keep background as -1
        
        # Set underbase (label 0) where original dark colors were
        for i in dark_color_indices:
            new_label_map[original_label_map == i] = 0
        
        # Create new color list with white first
        new_colors = [white_rgb] + colors
        
        # Update color names
        new_color_names = ["underbase_white"] + color_names
        
        # Update separation result
        updated_result = separation_result.copy()
        updated_result["colors"] = new_colors
        updated_result["color_names"] = new_color_names
        updated_result["label_map"] = new_label_map
        updated_result["num_colors"] = len(new_colors)
        
        logger.info(f"Added underbase for {len(dark_color_indices)} dark colors. Total layers: {len(new_colors)}")
        return updated_result
        
    except Exception as e:
        logger.warning(f"Underbase creation failed, continuing without underbase: {e}")
        return separation_result


# ─── Pipeline Steps ──────────────────────────────────────────────────────────

def step1_load_image(input_path: str) -> np.ndarray:
    _step(1, "Loading image")
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Image not found: {input_path}")
    
    logger.info(f"Attempting to load: {input_path}")
    
    # Use robust image loader (no extension reliance)
    try:
        image = load_image_safely(input_path)
        logger.info(f"Loaded image via robust loader: shape={image.shape}, dtype={image.dtype}, channels={image.shape[2] if len(image.shape) > 2 else 1}")
        if image.shape[2] == 4:
            image = image[:, :, :3]
        
        # Auto upscale small images to prevent stroke validation failures
        h, w = image.shape[:2]
        min_width = 1500
        if w < min_width:
            scale_factor = min_width / w
            new_w = int(w * scale_factor)
            new_h = int(h * scale_factor)
            # Phase 16: Use Lanczos4 for high-quality upscaling (prevents jagged logo edges)
            image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
            logger.info(f"Auto-upscaled small image: {w}x{h} → {new_w}x{new_h} (scale: {scale_factor:.2f}) [LANCZOS4]")
        
        return image
    except Exception as e:
        logger.error(f"Robust image loader failed: {e}")
        raise ValueError(f"Cannot read image {input_path}: {e}")


def step0_auto_crop(image: np.ndarray) -> np.ndarray:
    """
    Auto-crop the image to its non-white bounding box to improve K-means and remove artifacts.
    """
    _step(0.5, "Auto-cropping (Senior Opt)")
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # Assuming white/near-white is background
        _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        coords = cv2.findNonZero(thresh)
        if coords is not None:
            x, y, w, h = cv2.boundingRect(coords)
            # Add small padding 
            p = 15
            x = max(0, x - p)
            y = max(0, y - p)
            w = min(image.shape[1] - x, w + 2 * p)
            h = min(image.shape[0] - y, h + 2 * p)
            cropped = image[y:y+h, x:x+w]
            logger.info(f"  Cropped area: {w}x{h} at ({x}, {y})")
            return cropped
        return image
    except Exception as e:
        logger.warning(f"Auto-crop failed: {e}")
        return image


def step2_separate_colors(
    image: np.ndarray,
    num_colors: int,
    auto_detect: bool = False,
    white_threshold: int = 240,
) -> dict:
    _step(2, f"Color separation {'(auto-detect)' if auto_detect else f'{num_colors} colors'}")
    separator = ColorSeparator()
    _progress((2 - 1) / TOTAL_STEPS + 0.1, 'K-means starting')

    result = separator.separate(
        image,
        num_colors=max(num_colors, 1) if not auto_detect else 4,
        auto_detect=auto_detect,
        white_threshold=white_threshold,
    )
    _progress((2 - 1) / TOTAL_STEPS + 0.9, f'K-means complete: {result["num_colors"]} colors')
    return result


def step3_generate_masks(image: np.ndarray, separation_result: dict, halftone_mode: bool = False) -> list:
    _step(3, "Generating color masks")
    generator = MaskGenerator()
    # For halftone mode, generate grayscale intensity masks instead of binary
    masks = generator.generate_masks(
        image, 
        separation_result,
        grayscale_output=halftone_mode,
        apply_cleanup=not halftone_mode  # Skip cleanup for grayscale to preserve intensities
    )
    stats = generator.get_mask_stats(masks)
    total = max(1, len(masks))
    for i, s in enumerate(stats):
        # emit subprogress across this step
        sub = (i + 1) / total
        overall = ((3 - 1) + sub) / TOTAL_STEPS
        _progress(overall, f"Mask {i+1}/{total} generated")
        logger.info(f"  Mask {s['index']+1}: {s['coverage_percent']}% coverage")
    return masks


def step4_clean_edges(masks: list) -> list:
    _step(4, "Cleaning edges (small kernel, noise-only)")
    # Small kernel: removes scattered noise without merging Arabic diacritics
    kernel_noise = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    result = []
    for mask in masks:
        # Remove small scattered noise pixels
        clean = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_noise)
        # Close tiny gaps (2x2 only — avoids merging Arabic dots/strokes)
        clean = cv2.morphologyEx(clean, cv2.MORPH_CLOSE, kernel_close)
        result.append(clean)
    logger.info(f"  Cleaned {len(masks)} masks (kernel=2x2 open + 2x2 close)")
    return result


def step5_halftone(masks: list, args: argparse.Namespace) -> list:
    is_halftone_enabled = args.halftone and not getattr(args, 'skip_halftone', False)
    _step(5, "Halftone generation" if is_halftone_enabled else "Halftone (skipped)")
    
    if not is_halftone_enabled or not HAS_HALFTONE:
        return masks
    
    # Auto-calculate LPI based on DPI if user didn't set it explicitly
    # Rule: LPI = DPI / 8, clamped to [35, 85]
    effective_lpi = args.lpi
    if effective_lpi == 65:  # default value = user didn't set it
        effective_lpi = min(85, max(35, args.dpi // 8))
        logger.info(f"  Auto-calculated LPI: {effective_lpi} (based on DPI {args.dpi})")
    
    # Standard CMYK angles for best results (avoid moiré patterns)
    # Cyan: 15°, Magenta: 75°, Yellow: 0°, Black: 45°
    cmyk_angles = [15.0, 75.0, 0.0, 45.0]
    
    try:
        generator = HalftoneGenerator()
        result = []
        total = max(1, len(masks))
        
        # CLAHE for contrast enhancement before halftoning
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        
        for i, mask in enumerate(masks):
            # Check if mask is mostly solid (should not be halftoned)
            total_pixels = mask.size
            design_pixels = np.sum(mask == 255)  # design=255, background=0
            coverage_percentage = (design_pixels / total_pixels) * 100
            
            # If the user explicitly chose HALTONE finish, we usually want to process it
            # But if it's already a very simple solid shape, we might skip
            # The user's analysis suggests they want SOLID if they didn't choose halftone.
            if coverage_percentage > 95.0:
                logger.info(f"  Skipping halftone for mask {i+1} ({coverage_percentage:.1f}% coverage) - too dense")
                result.append(mask)
            else:
                # Contrast enhancement: CLAHE pushes shadows darker and highlights whiter
                # This produces cleaner, more regular halftone dots instead of scattered spray
                if mask.dtype != np.uint8:
                    enhanced = mask.astype(np.uint8)
                else:
                    enhanced = mask.copy()
                enhanced = clahe.apply(enhanced)
                
                # Use CMYK angle for this color index, fallback to default
                angle = cmyk_angles[i] if i < len(cmyk_angles) else args.angle
                ht = generator.generate(enhanced, lpi=effective_lpi, angle=angle, dot_shape=args.dot_shape, dpi=args.dpi)
                result.append(ht)
                logger.info(f"  Halftoned mask {i+1} ({coverage_percentage:.1f}% coverage) angle={angle}° LPI={effective_lpi} CLAHE=ON")
            
            overall = ((5 - 1) + (i + 1) / total) / TOTAL_STEPS
            _progress(overall, f"Processed {i+1}/{total} (solid: {coverage_percentage:.1f}%)")
        return result
    except Exception as e:
        logger.warning(f"Halftone generation failed, skipping: {e}")
        _step(5, "Halftone (skipped due to error)")
        return masks


def step6_binarize(masks: list, args: argparse.Namespace) -> list:
    _step(6, "Binarizing")
    if not HAS_BINARIZER:
        # Fallback: simple threshold
        result = []
        total = max(1, len(masks))
        for i, mask in enumerate(masks):
            _, binarized = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
            result.append(binarized)
            _progress(((6 - 1) + (i + 1) / total) / TOTAL_STEPS, f"Binarized {i+1}/{total}")
        return result
    binarizer = Binarizer()
    total = max(1, len(masks))
    out = []
    for i, m in enumerate(masks):
        out.append(binarizer.binarize(m))
        _progress(((6 - 1) + (i + 1) / total) / TOTAL_STEPS, f"Binarized {i+1}/{total}")
    return out


def step7_validate_strokes(masks: list, args: argparse.Namespace) -> list:
    _step(7, "Validating & fixing thin strokes")
    
    if not HAS_STROKE_VALIDATOR:
        logger.info("  StrokeValidator not available, skipping")
        return masks
    
    # Minimum stroke width: 0.15mm converted to pixels
    min_stroke_mm = 0.15
    min_stroke_px = max(1, int(args.dpi * min_stroke_mm / 25.4))
    
    result = []
    for i, mask in enumerate(masks):
        if mask.dtype != np.uint8:
            mask = mask.astype(np.uint8)
        
        # Find connected components
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8, cv2.CV_32S)
        
        thin_found = False
        for lbl in range(1, num_labels):
            area = stats[lbl, cv2.CC_STAT_AREA]
            w_comp = stats[lbl, cv2.CC_STAT_WIDTH]
            h_comp = stats[lbl, cv2.CC_STAT_HEIGHT]
            # Check if component is thin (width or height < min_stroke_px)
            if area > 10 and (w_comp < min_stroke_px or h_comp < min_stroke_px):
                thin_found = True
                break
        
        if thin_found:
            logger.warning(f"  Mask {i+1}: thin strokes detected (<{min_stroke_px}px), auto-thickening")
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (min_stroke_px * 2 + 1, min_stroke_px * 2 + 1))
            mask = cv2.dilate(mask, kernel, iterations=1)
        
        result.append(mask)
    
    logger.info(f"  Stroke validation complete (min={min_stroke_px}px = {min_stroke_mm}mm)")
    return result


def step7_5_strict_binarization(masks: list, args: argparse.Namespace) -> list:
    """
    Apply strict binarization and noise removal to ensure clean solid films.
    """
    is_halftone = args.halftone and not getattr(args, 'skip_halftone', False)
    _step(7.5, f"Strict binarization ({'halftone' if is_halftone else 'solid'} mode)")
    
    result = []
    total = max(1, len(masks))
    
    # Use global-threshold if provided, fallback to 200 for solid, 45 for halftone
    threshold_val = getattr(args, 'global_threshold', 200 if not is_halftone else 45)
    noise_min_area = getattr(args, 'noise_removal', 10)
    
    for i, mask in enumerate(masks):
        if mask.dtype != np.uint8:
            mask = mask.astype(np.uint8)

        # ── BINARY MASK GUARD: Ensure clean edges and preserved dots ──────
        
        is_solid = not is_halftone
        
        if is_solid:
            # NEW: Skip upscale+blur for text/logo (simple type or low smooth_factor)
            # This preserves razor-sharp edges and prevents dot merging in Arabic/Latin text
            img_type = getattr(args, 'image_type', 'auto')
            cli_smooth = getattr(args, 'smoothing_factor', 0.3)
            skip_upscale_blur = (img_type == 'simple') or (cli_smooth <= 0.15)
            
            if skip_upscale_blur:
                # Direct threshold with threshold_val — sharp, no smoothing
                _, binary_mask = cv2.threshold(mask, threshold_val, 255, cv2.THRESH_BINARY)
                logger.info(f"  [Solid] Mask {i+1}: sharp binarization (no upscale-blur) [image_type={img_type}, smooth={cli_smooth:.2f}]")
            else:
                # Standard: upscale 2x + blur(3x3) + threshold + downscale
                h_m, w_m = mask.shape[:2]
                up = cv2.resize(mask, (w_m * 2, h_m * 2), interpolation=cv2.INTER_CUBIC)
                up = cv2.GaussianBlur(up, (3, 3), 0)
                _, binary_mask = cv2.threshold(up, threshold_val, 255, cv2.THRESH_BINARY)
                binary_mask = cv2.resize(binary_mask, (w_m, h_m), interpolation=cv2.INTER_AREA)
                _, binary_mask = cv2.threshold(binary_mask, 127, 255, cv2.THRESH_BINARY)
                logger.info(f"  [Solid] Mask {i+1}: upscale-blur binarization (smooth edges)")
        else:
            # HALFTONE MODE: NO smoothing — raw dot preservation
            safe_thresh = 45  # low threshold to keep tiny halftone dots
            _, binary_mask = cv2.threshold(mask, safe_thresh, 255, cv2.THRESH_BINARY)
        
        # --- Inversion Guard (Coverage-based, safe for simple logos) ---
        # Only invert if design coverage is suspiciously low (< 2%)
        # This catches cases where mask generation produced inverted output
        # Do NOT invert based on white/black ratio — simple logos naturally have 90%+ white
        total_px = binary_mask.size
        design_coverage = np.sum(binary_mask == 255) / total_px
        
        if design_coverage < 0.02:
            logger.warning(f"  [Guard:Inversion] Very low coverage ({design_coverage:.1%}), inverting mask {i+1}")
            binary_mask = cv2.bitwise_not(binary_mask)
        
        # Noise removal (Area opening)
        if noise_min_area > 0:
            num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
                binary_mask, 8, cv2.CV_32S
            )
            clean = np.zeros_like(binary_mask)
            for lbl in range(1, num_labels):
                if stats[lbl, cv2.CC_STAT_AREA] >= noise_min_area:
                    clean[labels == lbl] = 255
            binary_mask = clean
        
        result.append(binary_mask)
        _progress(((7.5 - 1) + (i + 1) / total) / TOTAL_STEPS, f"Processed {i+1}/{total} [BINARY-GUARD]")
        
    return result




def step3_5_trapping(masks: list, separation_result: dict, args: argparse.Namespace) -> list:
    """
    Automatic color trapping to prevent registration issues between colors.
    Adds small overlaps between adjacent colors to ensure proper printing.
    """
    _step(3.5, "Trapping (automatic)")
    try:
        if len(masks) < 2:
            logger.info("Only one color layer, skipping trapping")
            return masks
        
        trapping_pixels = max(1, int(args.dpi * 0.1 / 25.4))
        logger.info(f"Applying trapping with {trapping_pixels} pixel overlap")
        
        kernel_size = trapping_pixels * 2 + 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        trapped_masks = []
        
        for i, mask in enumerate(masks):
            trapped = mask.copy()
            for j, other_mask in enumerate(masks):
                if i == j:
                    continue
                overlap = cv2.bitwise_and(mask, other_mask)
                if np.any(overlap > 127):
                    dilated_overlap = cv2.dilate(overlap, kernel, iterations=1)
                    trapped = cv2.bitwise_or(trapped, dilated_overlap)
                    logger.info(f"Added trapping between color {i+1} and {j+1}")
            trapped_masks.append(trapped)
        
        logger.info(f"Trapping applied to {len(trapped_masks)} layers")
        return trapped_masks
    except Exception as e:
        logger.warning(f"Trapping failed, continuing without trapping: {e}")
        return masks


def step8_registration_marks(masks: list, output_dir: str, args: argparse.Namespace) -> list:
    _step(8, "Adding registration marks")
    
    if not HAS_REG_MARKS:
        logger.warning("Skipping registration marks (module not found)")
        return masks
    
    # DPI-aware sizing: all measurements in mm converted to pixels
    quiet_zone_mm = 22       # 22mm quiet zone (above 20mm standard)
    mark_target_mm = 5       # 5mm mark size
    line_target_mm = 0.2     # 0.2mm line thickness
    dpi = args.dpi
    
    safe_border = max(120, int(dpi * quiet_zone_mm / 25.4))
    safe_mark_size = max(40, int(dpi * mark_target_mm / 25.4))
    safe_line_thickness = max(1, int(dpi * line_target_mm / 25.4))
    
    config = RegistrationConfig(
        add_border=True,
        border_size=safe_border,
        mark_type='full',
        dpi=dpi,
        style=MarkStyle(
            mark_size=safe_mark_size,
            line_thickness=safe_line_thickness,
            show_circle=True,
            show_cross=True,
            show_corner_marks=True,
            show_crop_marks=True,
            show_color_label=True,
            show_color_bar=(len(masks) > 1),
        )
    )
    
    generator = RegistrationMarksGenerator(dpi=args.dpi)
    result_masks = []
    
    for idx, raw_mask in enumerate(masks):
        # 1. المرحلة الأولى: معالجة التصميم فقط (Artwork Preparation)
        if not args.halftone:
            # Use raw mask directly to preserve sharpest detail
            processed_mask = raw_mask.copy()
            
            # Simple threshold to ensure it's still binary after morph
            _, processed_mask = cv2.threshold(processed_mask, 127, 255, cv2.THRESH_BINARY)
            logger.info(f"  Applied sharp artwork preparation (morph only) to mask {idx+1}")
        else:
            processed_mask = raw_mask.copy()

        # 2. المرحلة الثانية: تحويل التمثيل (Inversion for Paper Export)
        # SILK SCREEN POSITIVES: 0 (Black Ink) on 255 (White/Clear Paper)
        # Since MaskGenerator returns 255 as Design, we MUST invert it here.
        paper_mask = cv2.bitwise_not(processed_mask)
        
        # 3. المرحلة الثالثة: إضافة العلامات والاسم الحاد (Marks & Branding)
        # Now we apply marks directly to the inverted (0-ink / 255-paper) canvas
        marked = generator.add_marks(
            image=paper_mask,
            color_name=f"Film_{idx+1}",
            color_index=idx + 1,
            total_colors=len(masks),
            color_rgb=(0, 0, 0),
            config=config,
        )
        
        # Add custom film label if provided
        if args.film_label:
            h_marked, w_marked = marked.shape[:2]
            label_scale = max(0.5, min(1.0, w_marked / 2000))
            (lw, lh), _ = cv2.getTextSize(args.film_label, cv2.FONT_HERSHEY_SIMPLEX, label_scale, 1)
            label_margin = max(40, int(w_marked * 0.03))
            cv2.putText(
                marked, 
                args.film_label, 
                (label_margin, h_marked - label_margin),
                cv2.FONT_HERSHEY_SIMPLEX, 
                label_scale, (0, 0, 0), 1, cv2.LINE_AA
            )

        # Add "Developed By MO2" branding — safe coordinates based on actual text size
        h_brand, w_brand = marked.shape[:2]
        brand_text = "Developed By MO2"
        brand_scale = max(0.5, min(1.0, w_brand / 2000))
        (tw, th), _ = cv2.getTextSize(brand_text, cv2.FONT_HERSHEY_SIMPLEX, brand_scale, 1)
        brand_margin = max(40, int(w_brand * 0.03))
        x_pos = w_brand - tw - brand_margin
        y_pos = h_brand - brand_margin
        cv2.putText(
            marked, 
            brand_text, 
            (x_pos, y_pos),
            cv2.FONT_HERSHEY_SIMPLEX, 
            brand_scale, (0, 0, 0), 1, cv2.LINE_AA
        )

        result_masks.append(marked)
        _progress(((8-1) + (idx+1)/len(masks)) / TOTAL_STEPS, f"Marks {idx+1}/ {len(masks)}")
    
    return result_masks


def step9_export(
    masks: list,
    separation_result: dict,
    output_dir: str,
    args: argparse.Namespace,
) -> list:
    _step(9, "Exporting films (PNG + PDF + SVG)")
    os.makedirs(output_dir, exist_ok=True)
    output_dir = os.path.normpath(output_dir)

    exported_paths = []
    pdf_paths = []

    try:
        total = max(1, len(masks))
        
        # Conditional smoothing: use CLI arg if provided, else auto-detect based on colors
        cli_smooth = getattr(args, 'smoothing_factor', None)
        if cli_smooth is not None and cli_smooth > 0:
            eff_smooth = cli_smooth
        else:
            num_colors = len(masks)
            if num_colors <= 3:
                eff_smooth = 0.15
            else:
                eff_smooth = 0.30
        
        # Import vector exporter
        from core.vector_exporter import export_vector_pdf
        from core.exporter import Exporter, SVGWRITE_AVAILABLE
        
        # We collect all valid masks for the combined PDF
        all_masks_for_pdf = []
        all_colors_for_pdf = []
        all_names_for_pdf = []
        
        # A4 size in points
        a4_w, a4_h = A4
        margin = 36  # 0.5 inch margin
        max_w = a4_w - 2 * margin
        max_h = a4_h - 2 * margin

        for i, mask in enumerate(masks):
            if mask.dtype != np.uint8:
                mask = mask.astype(np.uint8)
            
            # Skip masks with no design pixels (all black -> now all white 255 since we inverted)
            if len(mask.shape) == 3:
                is_empty = np.sum(cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY) < 128) == 0
            else:
                is_empty = np.sum(mask < 128) == 0
                
            if is_empty:
                logger.info(f"  Skipping empty mask {i+1}")
                continue

            # Get color info for this mask from separation_result
            color_entry = separation_result['colors'][i] if i < len(separation_result['colors']) else (0,0,0)
            name_entry = separation_result['color_names'][i] if i < len(separation_result['color_names']) else f"Film_{i+1}"
            
            # 1. Save PNG for UI preview (Pure Binary)
            png_filename = f"film_{i+1}.png"
            png_filepath = os.path.join(output_dir, png_filename)
            # Ensure consistent film polarity for previews: black artwork (ink) on white background (paper)
            # Internally, vector tracing uses design=255, but film output is 0-ink / 255-paper.
            # Save PNG in final film polarity to match PDFs.
            preview_mask = mask.copy()
            if len(preview_mask.shape) == 3:
                preview_gray = cv2.cvtColor(preview_mask, cv2.COLOR_BGR2GRAY)
            else:
                preview_gray = preview_mask
            # If majority pixels are black, it's likely already film polarity; otherwise invert.
            black_ratio = float(np.sum(preview_gray < 128)) / float(preview_gray.size)
            if black_ratio < 0.50:
                preview_mask = cv2.bitwise_not(preview_mask)
            # Save PNG with correct DPI metadata (cv2.imwrite ignores DPI)
            try:
                from PIL import Image as _PIL
                _arr = preview_mask if len(preview_mask.shape) == 2 \
                       else cv2.cvtColor(preview_mask, cv2.COLOR_BGR2RGB)
                _PIL.fromarray(_arr).save(png_filepath, dpi=(args.dpi, args.dpi))
            except Exception:
                cv2.imwrite(png_filepath, preview_mask)  # fallback
            exported_paths.append(png_filepath)
            
            # 2. Save SVG (True Vector)
            if SVGWRITE_AVAILABLE:
                # Exporter logic (findContours) needs design pixels as 255
                # But our current mask has design as 0 (black ink on white paper)
                # So we re-invert for the vector tracing
                if len(mask.shape) == 3:
                    ink_mask = cv2.bitwise_not(cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY))
                else:
                    ink_mask = cv2.bitwise_not(mask)
                    
                svg_filename = f"film_{i+1}.svg"
                svg_filepath = os.path.join(output_dir, svg_filename)
                exporter = Exporter(output_dir, args.dpi)
                exporter.export_svg(
                    ink_mask, svg_filename,
                    smooth_factor=eff_smooth,
                    corner_threshold=getattr(args, 'corner_threshold', 150.0),
                    no_vector_blur=getattr(args, 'no_vector_blur', False)
                )
                exported_paths.append(svg_filepath)
                logger.info(f"  Exported {svg_filename} (SVG Vector)")
            
            # 3. Save individual PDF (True Vector)
            if REPORTLAB_AVAILABLE:
                pdf_filename = f"film_{i+1}.pdf"
                pdf_filepath = os.path.join(output_dir, pdf_filename)
                
                # Vector exporter expects design pixels as 255
                ink_mask_pdf = cv2.bitwise_not(
                    mask if len(mask.shape) == 2 else cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
                )
                
                export_vector_pdf(
                    masks=[ink_mask_pdf],
                    colors=[color_entry],
                    color_names=[name_entry],
                    output_path=Path(pdf_filepath),
                    dpi=args.dpi,
                    smooth_factor=eff_smooth,
                    corner_threshold=getattr(args, 'corner_threshold', 150.0),
                    no_vector_blur=getattr(args, 'no_vector_blur', False)
                )
                pdf_paths.append(pdf_filepath)
                exported_paths.append(pdf_filepath)
                logger.info(f"  Exported {pdf_filename} (PDF Vector)")

            # Add to collection for combined PDF
            all_masks_for_pdf.append(mask if len(mask.shape) == 2 else cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY))
            all_colors_for_pdf.append(color_entry)
            all_names_for_pdf.append(name_entry)

            _progress(((9 - 1) + (i + 1) / total) / TOTAL_STEPS, f"Exported {i+1}/{total}")
        
        # 4. Save combined PDF (True Vector)
        if args.combine_pdf and REPORTLAB_AVAILABLE and all_masks_for_pdf:
            combined_pdf_path = os.path.join(output_dir, "all_films_combined.pdf")
            
            # Re-invert all masks for vector_exporter (needs design=255)
            ink_masks_combined = [cv2.bitwise_not(m) for m in all_masks_for_pdf]
            
            export_vector_pdf(
                masks=ink_masks_combined,
                colors=all_colors_for_pdf,
                color_names=all_names_for_pdf,
                output_path=Path(combined_pdf_path),
                dpi=args.dpi,
                smooth_factor=eff_smooth,
                corner_threshold=getattr(args, 'corner_threshold', 150.0),
                no_vector_blur=getattr(args, 'no_vector_blur', False)
            )
            exported_paths.append(combined_pdf_path)
            logger.info(f"  Exported all_films_combined.pdf (PDF Vector)")
            
        logger.info(f"Export complete: {len(exported_paths)} files saved")
        
    except Exception as e:
        logger.error(f"Export failed: {e}", exc_info=True)

    # Save color info JSON with metadata
    img = separation_result.get('image')
    width = img.shape[1] if img is not None else 0
    height = img.shape[0] if img is not None else 0

    _save_color_info(separation_result, output_dir, {
        'dpi': args.dpi,
        'width': width,
        'height': height,
        'print_method': 'Screen Printing',
        'halftone': args.halftone,
        'lpi': args.lpi if args.halftone else 0,
    })

    _progress(1.0, 'Finished')
    return exported_paths


def _save_color_info(separation_result: dict, output_dir: str, metadata: dict = None) -> None:
    """حفظ معلومات الألوان كـ JSON — يقرأها الـ PreviewController."""
    import json
    from core.color_separator import ColorSeparator

    separator = ColorSeparator()
    color_info = separator.get_color_info(separation_result)

    info_path = os.path.join(output_dir, "color_info.json")
    with open(info_path, "w", encoding="utf-8") as f:
        data = {
            "num_colors": separation_result["num_colors"],
            "colors": color_info,
        }
        if metadata:
            data["metadata"] = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "dpi": metadata.get('dpi', 300),
                "width": metadata.get('width', 0),
                "height": metadata.get('height', 0),
                "print_method": metadata.get('print_method', 'Screen Printing'),
                "halftone": metadata.get('halftone', False),
                "lpi": metadata.get('lpi', 65),
            }
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info(f"  Saved color info: {info_path}")


# ─── Main ────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Silk Screen Film Generator — Virtual Design Studio"
    )
    parser.add_argument("--input", required=True, help="Path to input image")
    parser.add_argument("--output", required=True, help="Output directory path")
    parser.add_argument(
        '--colors', type=int, default=0,
        help='Number of colors (0 = auto-detect)'
    )
    parser.add_argument(
        '--auto-colors', action='store_true',
        help='Auto-detect optimal color count'
    )
    parser.add_argument("--dpi", type=int, default=600, help="Output DPI (higher = smoother edges)")
    parser.add_argument("--halftone", action="store_true", help="Enable halftone mode")
    parser.add_argument("--lpi", type=int, default=65, help="Halftone LPI (lines per inch)")
    parser.add_argument("--dot-shape", choices=["round", "square", "ellipse"], default="round", help="Halftone dot shape")
    parser.add_argument("--detail-level", choices=["high", "medium", "low"], default="medium")
    parser.add_argument("--clean", action="store_true", help="Apply edge cleaning")
    parser.add_argument("--validate-strokes", action="store_true", help="Validate stroke widths")
    parser.add_argument("--min-stroke", type=float, default=0.0, help="Min stroke width in mm (disabled)")
    parser.add_argument("--edge-enhance", choices=["none", "light", "strong"], default="light")
    parser.add_argument(
        '--combine-pdf', action='store_true', default=True,
        help='Combine all films into one PDF (default: True)'
    )
    parser.add_argument(
        '--separate-pdfs', dest='combine_pdf', action='store_false',
        help='Export each film as a separate PDF'
    )
    parser.add_argument(
        '--skip-halftone', action='store_true',
        help='Skip halftone generation entirely'
    )
    parser.add_argument(
        '--pantone-matching', choices=['automatic', 'manual', 'disabled'], default='automatic',
        help='Pantone color matching mode'
    )
    parser.add_argument(
        '--underbase-mode', choices=['automatic', 'manual', 'disabled'], default='automatic',
        help='Underbase creation mode'
    )
    parser.add_argument(
        '--trapping-mode', choices=['automatic', 'manual', 'disabled'], default='automatic',
        help='Color trapping mode'
    )
    parser.add_argument(
        '--overprint-mode', choices=['automatic', 'manual', 'disabled'], default='automatic',
        help='Overprint mode'
    )
    parser.add_argument(
        '--gradient-mesh-mode', choices=['automatic', 'manual', 'disabled'], default='automatic',
        help='Gradient mesh conversion mode'
    )
    parser.add_argument(
        '--typography-mode', choices=['automatic', 'manual', 'disabled'], default='automatic',
        help='Advanced typography mode'
    )
    parser.add_argument(
        '--mesh-preview-mode', choices=['automatic', 'manual', 'disabled'], default='automatic',
        help='Mesh preview and simulation mode'
    )
    
    # Advanced Tuning (Phase 8 Senior Optimizations)
    parser.add_argument("--global-threshold", type=int, default=127, help="Global threshold for solid masks (0-255)")
    parser.add_argument("--smoothing-factor", type=float, default=0.3, help="Bezier smoothing factor (0-1.0)")
    parser.add_argument("--corner-threshold", type=float, default=150.0, help="Angle threshold to preserve sharp corners (degrees)")
    parser.add_argument("--noise-removal", type=int, default=3, help="Minimum contour area to keep (pixels)")
    parser.add_argument("--auto-crop", action="store_true", help="Auto-crop image before processing")
    parser.add_argument("--adaptive-threshold", action="store_true", help="Use adaptive/Otsu thresholding instead of global")
    parser.add_argument("--image-type", choices=["simple", "mixed", "complex", "auto"], default="auto", 
                        help="Engine mode: simple (logo), mixed (normal), complex (details), or auto")
    parser.add_argument("--film-label", type=str, default="", help="Custom label to print on each film")
    parser.add_argument(
        "--no-vector-blur", action="store_true",
        help="Disable pre-trace Gaussian blur for sharpest text edges (overrides image-type settings)"
    )
    parser.add_argument(
        "--white-threshold", type=int, default=240,
        help="Pixel value above which is considered white background (0-255)"
    )
    
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    start_time = time.time()

    # ═══ Auto-set parameters based on image type ═══
    # When image_type is simple/mixed/complex, override all related params unconditionally.
    # When image_type is auto, respect CLI-provided values or defaults.
    img_type = getattr(args, 'image_type', 'auto')

    if img_type == 'simple':
        args.smoothing_factor = 0.20
        args.corner_threshold = 150.0
        args.global_threshold = 160
        logger.info("[ImageType] Simple (text/logo): smooth=%.2f, corner=%.1f°, threshold=%d" % (args.smoothing_factor, args.corner_threshold, args.global_threshold))
    elif img_type == 'mixed':
        args.smoothing_factor = 0.20
        args.corner_threshold = 150.0
        args.global_threshold = 200
        logger.info("[ImageType] Mixed: smooth=%.2f, corner=%.1f°, threshold=%d" % (args.smoothing_factor, args.corner_threshold, args.global_threshold))
    elif img_type == 'complex':
        args.smoothing_factor = 0.30
        args.corner_threshold = 160.0
        args.global_threshold = 200
        logger.info("[ImageType] Complex: smooth=%.2f, corner=%.1f°, threshold=%d" % (args.smoothing_factor, args.corner_threshold, args.global_threshold))
    else:
        # Auto: keep CLI-provided values or defaults (smoothing_factor, corner_threshold, global_threshold)
        logger.info("[ImageType] Auto: using CLI/default parameters (smooth=%.2f, corner=%.1f°, threshold=%d)" % (args.smoothing_factor, args.corner_threshold, args.global_threshold))

    logger.info("=" * 50)
    logger.info("Virtual Design — Silk Screen Processing Pipeline")
    logger.info(f"Input:  {args.input}")
    logger.info(f"Output: {args.output}")
    logger.info(f"Colors: {args.colors} | DPI: {args.dpi} | Halftone: {args.halftone}")
    logger.info("=" * 50)

    output_dir = args.output
    logger.info(f"Root Output Directory: {output_dir}")

    try:
        # Step 1 — Load
        image = step1_load_image(args.input)
        
        # Step 1.5 — Auto Crop (Senior Optimization)
        if args.auto_crop:
            image = step0_auto_crop(image)

        # Step 2 — Color Separation
        separation_result = step2_separate_colors(
            image,
            args.colors if args.colors > 0 else 4,
            auto_detect=(args.colors == 0) or args.auto_colors,
            white_threshold=getattr(args, 'white_threshold', 240),
        )

        # Step 2.5 — Automatic Underbase Creation
        if args.underbase_mode == 'automatic' and HAS_PANTONE:
            separation_result = step2_5_underbase_creation(separation_result, args)

        # Step 3 — Mask Generation (with grayscale if halftone enabled)
        masks = step3_generate_masks(image, separation_result, halftone_mode=args.halftone)
        
        # Step 3.5 — Automatic Trapping
        if args.trapping_mode == 'automatic' and HAS_PANTONE:
            masks = step3_5_trapping(masks, separation_result, args)

        # DEBUG: Save masks after generation (only in debug mode)
        # for idx, mask in enumerate(masks):
        #     debug_path = os.path.join(output_dir, f"debug_mask_{idx+1}_after_generation.png")
        #     cv2.imwrite(debug_path, mask)
        #     logger.info(f"DEBUG: Saved mask {idx+1} after generation: {debug_path}")

        # Step 4 — Edge Cleaning (always enabled for solid, skip for halftone)
        if not args.halftone:
            masks = step4_clean_edges(masks)
        else:
            _step(4, "Edge cleaning (skipped for halftone)")

        # Step 5 — Halftone (applied to grayscale masks)
        masks = step5_halftone(masks, args)

        # Step 6 — Binarize (after halftone if enabled)
        if args.halftone:
            masks = step6_binarize(masks, args)
        else:
            _step(6, "Binarizing (skipped - masks already binary)")

        # Step 7 — Stroke Validation
        masks = step7_validate_strokes(masks, args)

        # Step 7.5 — Strict Binarization (prevents false halftoning)
        masks = step7_5_strict_binarization(masks, args)

        # Step 8 — Registration Marks
        masks = step8_registration_marks(masks, output_dir, args)
        
        # DEBUG: Save masks after registration marks
        for idx, mask in enumerate(masks):
            debug_path = os.path.join(output_dir, f"debug_mask_{idx+1}_after_registration.png")
            cv2.imwrite(debug_path, mask)
            logger.info(f"DEBUG: Saved mask {idx+1} after registration marks: {debug_path}")

        # Step 9 — Export
        exported = step9_export(masks, separation_result, output_dir, args)

        elapsed = round(time.time() - start_time, 1)
        logger.info(f"Pipeline complete in {elapsed}s. {len(exported)} films exported.")

        # FATAL #3 FIX: آخر سطر دائماً — Dart يقرأه ليعرف مسار الـ output
        _output_dir_signal(output_dir)
        return 0

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return 2
    except ValueError as e:
        logger.error(f"Invalid input: {e}")
        return 3
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
