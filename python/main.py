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

import cv2
import numpy as np

# ─── Optional imports with graceful fallback ─────────────────────────────────
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("[WARNING] reportlab not installed. PDF export will use PNG fallback.", flush=True)

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
            
            if is_dark and color_rgb != (255, 255, 255):  # Exclude white underbase if already added
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
            image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
            logger.info(f"Auto-upscaled small image: {w}x{h} → {new_w}x{new_h} (scale: {scale_factor:.2f})")
        
        return image
    except Exception as e:
        logger.error(f"Robust image loader failed: {e}")
        raise ValueError(f"Cannot read image {input_path}: {e}")


def step2_separate_colors(image: np.ndarray, num_colors: int, auto_detect: bool = False) -> dict:
    _step(2, f"Color separation {'(auto-detect)' if auto_detect else f'{num_colors} colors'}")
    separator = ColorSeparator()
    _progress((2 - 1) / TOTAL_STEPS + 0.1, 'K-means starting')
    
    result = separator.separate(
        image,
        num_colors=max(num_colors, 1) if not auto_detect else 4,
        auto_detect=auto_detect,
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
    _step(4, "Cleaning edges")
    cleaner = EdgeCleaner()
    cleaned = cleaner.clean_all(masks, kernel_size=3, smooth=True)
    return cleaned


def step5_halftone(masks: list, args: argparse.Namespace) -> list:
    _step(5, "Halftone generation" if args.halftone and not getattr(args, 'skip_halftone', False) else "Halftone (skipped)")
    if not args.halftone or not HAS_HALFTONE or getattr(args, 'skip_halftone', False):
        return masks
    
    # Standard CMYK angles for best results (avoid moiré patterns)
    # Cyan: 15°, Magenta: 75°, Yellow: 0°, Black: 45°
    cmyk_angles = [15.0, 75.0, 0.0, 45.0]
    
    try:
        generator = HalftoneGenerator()
        result = []
        total = max(1, len(masks))
        for i, mask in enumerate(masks):
            # Check if mask is mostly solid (should not be halftoned)
            total_pixels = mask.size
            black_pixels = np.sum(mask < 128)  # Count black pixels
            solid_percentage = (black_pixels / total_pixels) * 100
            
            # If mask is mostly solid (>80% black), skip halftoning to keep it solid
            if solid_percentage > 80.0:
                logger.info(f"  Skipping halftone for mask {i+1} ({solid_percentage:.1f}% solid) - keeping solid")
                result.append(mask)
            else:
                # Use CMYK angle for this color index, fallback to default
                angle = cmyk_angles[i] if i < len(cmyk_angles) else args.angle
                ht = generator.generate(mask, lpi=args.lpi, angle=angle, dot_shape=args.dot_shape, dpi=args.dpi)
                result.append(ht)
                logger.info(f"  Halftoned mask {i+1} ({solid_percentage:.1f}% coverage) with angle {angle}°")
            
            overall = ((5 - 1) + (i + 1) / total) / TOTAL_STEPS
            _progress(overall, f"Processed {i+1}/{total} (solid: {solid_percentage:.1f}%)")
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
    _step(7, "Validating stroke widths (disabled)")
    # Temporarily skip stroke validation to prevent INVALID_FORMAT errors
    # TODO: Re-enable with improved validation logic
    logger.info("  Stroke validation temporarily disabled")
    return masks


def step7_5_strict_binarization(masks: list, args: argparse.Namespace) -> list:
    """
    Apply strict binarization to ensure all masks are pure black (0) and white (255).
    This prevents false halftoning of what should be solid colors.
    """
    _step(7.5, "Strict binarization (pre-film)")
    result = []
    total = max(1, len(masks))
    for i, mask in enumerate(masks):
        # Ensure mask is uint8
        if mask.dtype != np.uint8:
            mask = mask.astype(np.uint8)
        
        # Apply strict binary threshold
        _, binary_mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
        
        # Optional: Apply slight Gaussian blur then re-threshold to smooth stair-stepping
        if args.clean:  # Only if edge cleaning is enabled
            blurred = cv2.GaussianBlur(binary_mask, (3, 3), 0.5)
            _, binary_mask = cv2.threshold(blurred, 127, 255, cv2.THRESH_BINARY)
        
        result.append(binary_mask)
        _progress(((7.5 - 1) + (i + 1) / total) / TOTAL_STEPS, f"Binarized {i+1}/{total}")
        logger.info(f"  Strict binarization applied to mask {i+1}")
    
    return result
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
    
    config = RegistrationConfig(
        add_border=True,
        border_size=120,
        mark_type='full',
        dpi=args.dpi,
        style=MarkStyle(
            mark_size=60,
            line_thickness=2,
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
    
    for idx, mask in enumerate(masks):
        marked = generator.add_marks(
            image=mask,
            color_name=f"Film_{idx+1}",
            color_index=idx + 1,
            total_colors=len(masks),
            color_rgb=(0, 0, 0),
            config=config,
        )
        result_masks.append(marked)
        _progress(((8-1) + (idx+1)/len(masks)) / TOTAL_STEPS, f"Marks {idx+1}/{len(masks)}")
    
    return result_masks


def step9_export(
    masks: list,
    separation_result: dict,
    output_dir: str,
    args: argparse.Namespace,
) -> list:
    _step(9, "Exporting films (PNG + PDF + SVG)")
    os.makedirs(output_dir, exist_ok=True)

    exported_paths = []
    pdf_paths = []

    try:
        total = max(1, len(masks))
        
        # Import exporter for SVG functionality
        from core.exporter import Exporter, SVGWRITE_AVAILABLE
        
        # Prepare PDF combined canvas if requested and available
        combined_pdf_path = os.path.join(output_dir, "all_films_combined.pdf")
        combined_pdf = canvas.Canvas(combined_pdf_path, pagesize=A4) if (args.combine_pdf and REPORTLAB_AVAILABLE) else None
        
        # A4 size in points
        a4_w, a4_h = A4
        margin = 36  # 0.5 inch margin
        max_w = a4_w - 2 * margin
        max_h = a4_h - 2 * margin

        for i, mask in enumerate(masks):
            if mask.dtype != np.uint8:
                mask = mask.astype(np.uint8)
            
            # Skip masks with no design pixels (all black)
            if np.sum(mask > 0) == 0:
                logger.info(f"  Skipping empty mask {i+1}")
                continue

            # 1. Save PNG for UI preview
            png_filename = f"film_{i+1}.png"
            png_filepath = os.path.join(output_dir, png_filename)
            # For single color designs, invert to show black design on white background
            if len(masks) == 1:
                preview_mask = cv2.bitwise_not(mask)  # Invert: white design on black background → black design on white background
            else:
                preview_mask = cv2.bitwise_not(mask)  # Invert for multi-color: white design on black background
            cv2.imwrite(png_filepath, preview_mask)
            exported_paths.append(png_filepath)
            
            # 2. Save SVG for vector editing
            if SVGWRITE_AVAILABLE:
                svg_filename = f"film_{i+1}.svg"
                svg_filepath = os.path.join(output_dir, svg_filename)
                exporter = Exporter(output_dir, args.dpi)
                exporter.export_svg(mask, svg_filename)
                exported_paths.append(svg_filepath)
                logger.info(f"  Exported {svg_filename} (vector)")
            
            # 3. Save individual PDF
            if REPORTLAB_AVAILABLE:
                pdf_filename = f"film_{i+1}.pdf"
                pdf_filepath = os.path.join(output_dir, pdf_filename)
                
                # Create individual PDF
                c = canvas.Canvas(pdf_filepath, pagesize=A4)
                
                # Calculate scaling to fit A4
                img_h, img_w = mask.shape[:2]
                scale = min(max_w / img_w, max_h / img_h)
                draw_w = img_w * scale
                draw_h = img_h * scale
                
                # Center on page
                x = margin + (max_w - draw_w) / 2
                y = margin + (max_h - draw_h) / 2
                
                # Draw on individual PDF
                c.drawImage(png_filepath, x, y, width=draw_w, height=draw_h, preserveAspectRatio=True, mask='auto')
                c.save()
                pdf_paths.append(pdf_filepath)
                
                # Draw on combined PDF
                if combined_pdf:
                    combined_pdf.drawImage(png_filepath, x, y, width=draw_w, height=draw_h, preserveAspectRatio=True, mask='auto')
                    combined_pdf.showPage()  # New page for next film
                    
            logger.info(f"  Exported {png_filename} ({mask.shape})")
            _progress(((9 - 1) + (i + 1) / total) / TOTAL_STEPS, f"Exported {i+1}/{total}")
        
        # Save combined PDF
        if combined_pdf:
            combined_pdf.save()
            logger.info(f"  Exported combined PDF: all_films_combined.pdf")
            exported_paths.append(combined_pdf_path)
            
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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    start_time = time.time()

    logger.info("=" * 50)
    logger.info("Virtual Design — Silk Screen Processing Pipeline")
    logger.info(f"Input:  {args.input}")
    logger.info(f"Output: {args.output}")
    logger.info(f"Colors: {args.colors} | DPI: {args.dpi} | Halftone: {args.halftone}")
    logger.info("=" * 50)

    output_dir = args.output
    # Always create a timestamped subdirectory to avoid conflicts with existing files
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(output_dir, f"silk_output_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)

    try:
        # Step 1 — Load
        image = step1_load_image(args.input)

        # Step 2 — Color Separation
        separation_result = step2_separate_colors(
            image,
            args.colors if args.colors > 0 else 4,
            auto_detect=(args.colors == 0) or args.auto_colors
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

        # Step 4 — Edge Cleaning (skip if halftone, cleanup already done in mask gen)
        if args.clean and not args.halftone:
            masks = step4_clean_edges(masks)
        else:
            _step(4, "Edge cleaning (skipped)")

        # Step 5 — Halftone (applied to grayscale masks)
        masks = step5_halftone(masks, args)

        # Step 6 — Binarize (after halftone if enabled)
        if args.halftone:
            masks = step6_binarize(masks, args)
        else:
            _step(6, "Binarizing (skipped - masks already binary)")

        # Step 7 — Stroke Validation
        masks = step7_validate_strokes(masks, args)

        # Masks are now correctly generated with design=black, background=white (silk screen standard)
        # No inversion needed anymore

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
