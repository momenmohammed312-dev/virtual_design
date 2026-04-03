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
import gc
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field

import cv2
import numpy as np

# ─── Optional imports with graceful fallback ─────────────────────────────────
try:
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    REPORTLAB_AVAILABLE = True
except ImportError as e:
    REPORTLAB_AVAILABLE = False
    # Use a specific signal that the bridge can detect
    print(f"\nFATAL:DEPENDENCY_MISSING:reportlab:PDF export requires: pip install reportlab. Error: {e}", flush=True)
    print(f"FATAL:DEPENDENCY_MISSING:reportlab", flush=True)

# Important local imports for vector export
try:
    from core.vector_exporter import export_vector_pdf, render_vector_halftone, render_raster_halftone
    HAS_VECTOR_EXPORTER = True
except ImportError:
    HAS_VECTOR_EXPORTER = False


# ─── ProcessedFilmCache — Lock Preview Output Architecture ─────────────────────
@dataclass
class LockedFilm:
    """Immutable snapshot of a processed film mask with metadata."""
    final_mask: np.ndarray      # uint8, film polarity (ink=0, bg=255)
    color_rgb: tuple             # (R, G, B)
    color_name: str
    film_index: int
    image_class: str
    smooth_factor: float
    corner_threshold: float
    use_potrace_style: bool
    is_halftone: bool

@dataclass
class ProcessedFilmCache:
    """Cache for final processed masks - export reads from here, never re-processes."""
    films: List[LockedFilm] = field(default_factory=list)
    locked: bool = False

    def lock(self):
        """Create immutable snapshots of all masks."""
        self.locked = True
        for f in self.films:
            f.final_mask = f.final_mask.copy()  # Immutable snapshot


# Local imports
sys.path.insert(0, str(Path(__file__).parent))

from core.color_separator import ColorSeparator
from core.image_loader import load_image_safely
from core.mask_generator import MaskGenerator
from core.edge_cleaner import EdgeCleaner

# Pipeline Controller — centralized polarity and validation
try:
    from core.pipeline_controller import PipelineController
    controller = PipelineController()
    HAS_CONTROLLER = True
except ImportError:
    HAS_CONTROLLER = False
    print("[WARNING] Pipeline Controller not available", flush=True)

from core.print_job_config import PrintJobConfig
from core.pipeline_router import PipelineRouter

# Smart Analysis import
try:
    from core.smart_analyzer import SmartAnalyzer
    HAS_SMART_ANALYZER = True
except ImportError:
    HAS_SMART_ANALYZER = False
    print("[WARNING] Smart Analyzer not available", flush=True)

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
    from core.edge_aware_binarizer import EdgeAwareBinarizer, EdgeAwareConfig
    HAS_EDGE_AWARE_BINARIZER = True
except ImportError:
    HAS_EDGE_AWARE_BINARIZER = False

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
    from core.exporter import Exporter, SVGWRITE_AVAILABLE
    HAS_EXPORTER = True
except ImportError:
    HAS_EXPORTER = False
    SVGWRITE_AVAILABLE = False


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

TOTAL_STEPS = 10


def _check_modules() -> None:
    """Check module availability."""
    optional = {
        'SmartAnalyzer': HAS_SMART_ANALYZER,
        'HalftoneGenerator': HAS_HALFTONE,
        'Binarizer': HAS_BINARIZER,
        'EdgeAwareBinarizer': HAS_EDGE_AWARE_BINARIZER,
        'StrokeValidator': HAS_STROKE_VALIDATOR,
        'RegistrationMarks': HAS_REG_MARKS,
        'Exporter': HAS_EXPORTER,
        'PantoneLibrary': HAS_PANTONE,
        'PipelineController': HAS_CONTROLLER,
        'ReportLab': REPORTLAB_AVAILABLE,
    }
    missing_optional = [name for name, available in optional.items() if not available]
    if missing_optional:
        logger.warning(f"[Modules] Optional modules NOT available: {', '.join(missing_optional)}")
    else:
        logger.info("[Modules] All optional modules loaded OK.")


def _step(n: float, name: str) -> None:
    """Print step progress for Dart."""
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
    
    # TASK 20: Proactive garbage collection to prevent memory errors with large images
    gc.collect()
    
    # Use robust image loader (no extension reliance)
    try:
        image = load_image_safely(input_path)
        logger.info(f"Loaded image via robust loader: shape={image.shape}, dtype={image.dtype}, channels={image.shape[2] if len(image.shape) > 2 else 1}")
        if image.shape[2] == 4:
            image = image[:, :, :3]
        
        # Compromise upscale for analysis quality - ensure good edge detection and clustering
        h, w = image.shape[:2]
        logger.info(f"Processing image at original resolution: {w}x{h}")
        
        # Scale to minimum 1200px for analysis quality (compromise between 300px and 2000px)
        target_width = 1200
        if w < target_width:
            scale_factor = target_width / w
            new_w = int(w * scale_factor)
            new_h = int(h * scale_factor)
            # Use CUBIC for smoother upscaling that reduces aliasing
            image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
            # Add GaussianBlur to smooth staircase artifacts from large upscaling
            image = cv2.GaussianBlur(image, (3, 3), 0)
            logger.info(f"Upscaled for analysis: {w}x{h} → {new_w}x{new_h} (scale: {scale_factor:.2f}) [CUBIC+GaussianBlur]")
        
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


def preprocess_text_logo(image: np.ndarray) -> np.ndarray:
    """[TASK 19] Enhanced sharpening for pure logos/text: Bilateral + Sharpening."""
    # 1. Bilateral filter removes noise
    bilat = cv2.bilateralFilter(image, 5, 50, 50)
    
    # 2. Sharpening kernel (Senior Standard for sharp vector lines)
    # Re-sharpens edges that might have been blurred by upscaling (LANCZOS4)
    kernel_sharpen = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    sharpened = cv2.filter2D(bilat, -1, kernel_sharpen)
    return sharpened

def preprocess_artwork(image: np.ndarray) -> np.ndarray:
    """[TASK 8] Balanced preprocessing for illustrations: Bilateral + Contrast."""
    bilat = cv2.bilateralFilter(image, 9, 75, 75)
    # alpha=1.3: moderate enhancement for K-means separating neighboring colors.
    return cv2.convertScaleAbs(bilat, alpha=1.3, beta=0)

def preprocess_photo(image: np.ndarray) -> np.ndarray:
    """[TASK 8] Shadow/Texture-preserving preprocessing for photographs."""
    # Strong bilateral for halftone-smooth gradients. grayscale + unsharp mask.
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    bilat = cv2.bilateralFilter(gray, 15, 75, 75)
    
    # Gaussian Unsharp Mask (Senior standard)
    blurred = cv2.GaussianBlur(bilat, (5, 5), 1.0)
    unsharp = cv2.addWeighted(bilat, 1.5, blurred, -0.5, 0)
    return unsharp

def step1_5_preprocess(image: np.ndarray) -> np.ndarray:
    """[DEPRECATED WORKER] Wraps artwork preprocess for old callers."""
    _step(1.5, "[Legacy] Pre-processing")
    return preprocess_artwork(image)


def step2_separate_colors(
    image: np.ndarray,
    num_colors: int,
) -> dict:
    """
    Wrapper around ColorSeparator.separate().
    num_colors is the effective count determined by the caller.
    auto_detect and white_threshold are NOT passed to separate() —
    they are caller-level concerns, not K-means parameters.
    """
    _step(2, f"Color separation ({num_colors} colors)")
    separator = ColorSeparator()
    _progress((2 - 1) / TOTAL_STEPS + 0.1, 'K-means starting')

    # FIX: Remove auto_detect + white_threshold — they are not in separate() signature.
    # Both branches of the old ternary computed max(num_colors, 2) identically — simplified.
    result = separator.separate(
        image,
        num_colors=max(num_colors, 2),
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
    
    total = max(1, len(masks))
    for i, m in enumerate(masks):
        m_stats = generator.get_mask_stats(m)
        # emit subprogress across this step
        sub = (i + 1) / total
        overall = ((3 - 1) + sub) / TOTAL_STEPS
        _progress(overall, f"Mask {i+1}/{total} generated")
        logger.info(f"  Mask {i+1}: {m_stats['coverage_pct']:.1f}% coverage")
        
    return masks


def step4_clean_edges(masks: list, image_class=None, dpi: int = 300) -> list:
    _step(6, "Cleaning edges (adaptive cleanup)")
    
    # Dynamic kernel size: 0.1mm relative to DPI
    # ~1.2px at 300dpi, ~2.4px at 600dpi
    base_size = max(1, int(dpi * 0.1 / 25.4))
    
    # Adaptive kernel sizing based on image class
    if image_class and hasattr(image_class, 'value'):
        if image_class.value == 'text_logo':
            # TEXT_LOGO: minimal cleanup to preserve sharp serifs
            sz = max(1, base_size)
            k_open  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (sz, sz))
            k_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (sz, sz))
            kernel_desc = f"{sz}x{sz} (text)"
        elif image_class.value == 'photo':
            # PHOTO: larger cleanup to suppress halftone-like noise
            sz = max(3, base_size + 1)
            k_open  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (sz, sz))
            k_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (sz, sz))
            kernel_desc = f"{sz}x{sz} (photo)"
        else:
            sz = max(2, base_size)
            k_open  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (sz, sz))
            k_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (sz, sz))
            kernel_desc = f"{sz}x{sz} (balanced)"
    else:
        sz = max(2, base_size)
        k_open  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (sz, sz))
        k_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (sz, sz))
        kernel_desc = f"{sz}x{sz} (default)"
    
    result = []
    for mask in masks:
        # Remove small scattered noise pixels
        clean = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k_open)
        # Close tiny gaps
        clean = cv2.morphologyEx(clean, cv2.MORPH_CLOSE, k_close)
        result.append(clean)
    
    logger.info(f"  Cleaned {len(masks)} masks (kernel={kernel_desc})")
    return result


def _apply_image_type_defaults(args: argparse.Namespace) -> None:
    """Set default parameters based on image type."""
    if args.image_type == 'simple':
        args.corner_threshold = 0.0
    elif args.image_type == 'text':
        args.corner_threshold = 15.0
    elif args.image_type == 'logo':
        args.corner_threshold = 30.0
    elif args.image_type == 'photo':
        args.corner_threshold = 45.0
    elif args.image_type == 'auto':
        args.corner_threshold = 45.0  # default value


def step5_halftone(masks: list, args: argparse.Namespace) -> list:
    """Generate halftone patterns for screen printing with gamma correction."""
    is_halftone_enabled = args.halftone and not getattr(args, 'skip_halftone', False)
    _step(5, "Halftone generation" if is_halftone_enabled else "Halftone (skipped)")
    
    if not is_halftone_enabled or not HAS_HALFTONE:
        return masks

    # TASK 7: Hard gate for TEXT_LOGO (never halftone vector-style logos)
    image_class = getattr(args, '_image_class', None)
    if image_class and hasattr(image_class, 'value') and image_class.value == 'text_logo':
        logger.info("  [Halftone] Hard gate triggered: TEXT_LOGO images bypass halftoning.")
        return masks
    
    # Auto-calculate LPI based on DPI if user didn't set it explicitly
    # Rule: LPI = DPI / 5, clamped to [55, 120] (better detail for screen printing)
    effective_lpi = args.lpi
    if effective_lpi == 65:  # default value = user didn't set it
        effective_lpi = min(120, max(55, args.dpi // 5))
        logger.info(f"  Auto-calculated LPI: {effective_lpi} (based on DPI {args.dpi})")
    
    # Standard CMYK angles for best results (avoid moiré patterns)
    # Cyan: 15°, Magenta: 75°, Yellow: 0°, Black: 45°
    cmyk_angles = [15.0, 75.0, 0.0, 45.0]
    
    # Gamma correction: controls dot growth curve
    # 1.6 = standard for screen printing (dots grow faster in shadows)
    halftone_gamma = 1.6
    
    try:
        generator = HalftoneGenerator(
            dpi=args.dpi,
            radius_gain=getattr(args, 'dot_gain_radius', 1.0),
            curve_type=getattr(args, 'dot_gain_curve', 'linear')
        )
        logger.info(f"  Halftone generator: radius_gain={args.dot_gain_radius}, curve={args.dot_gain_curve}")
        result = []
        total = max(1, len(masks))
        
        # CLAHE for contrast enhancement before halftoning
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        
        # Auto-select dot shape based on image class if not explicitly set
        if not hasattr(args, 'dot_shape') or args.dot_shape == 'round':
            image_class = getattr(args, '_image_class', None)
            if image_class and hasattr(image_class, 'value'):
                if HAS_SMART_ANALYZER:
                    from core.smart_analyzer import SmartAnalyzer
                    analyzer = SmartAnalyzer()
                    effective_dot_shape = analyzer.get_dot_shape(image_class)
                else:
                    # Fallback logic
                    dot_shape_map = {
                        'text_logo': 'square',   # تفاصيل حادة
                        'artwork':   'round',    # طبيعي
                        'photo':     'round',    # صور
                    }
                    effective_dot_shape = dot_shape_map.get(image_class.value, 'round')
                logger.info(f"  Auto-selected dot shape: {effective_dot_shape} for {image_class.value}")
            else:
                effective_dot_shape = 'round'
        else:
            effective_dot_shape = args.dot_shape
        
        for i, mask in enumerate(masks):
            # Check if mask is mostly solid (should not be halftoned)
            total_pixels = mask.size
            design_pixels = np.sum(mask < 128)  # design=0 (ink), background=255
            coverage_percentage = (design_pixels / total_pixels) * 100
            
            # Skip CLAHE for solid masks (no gradients)
            should_use_clahe = 5.0 <= coverage_percentage <= 85.0
            
            if coverage_percentage > 95.0:
                logger.info(f"  Skipping halftone for mask {i+1} ({coverage_percentage:.1f}% coverage) - too dense")
                result.append(mask)
            else:
                # Contrast enhancement: CLAHE only for masks with gradients
                if mask.dtype != np.uint8:
                    enhanced = mask.astype(np.uint8)
                else:
                    enhanced = mask.copy()
                
                if should_use_clahe:
                    enhanced = clahe.apply(enhanced)
                    logger.info(f"  Applied CLAHE to mask {i+1} (coverage={coverage_percentage:.1f}%)")
                else:
                    logger.info(f"  Skipped CLAHE for mask {i+1} (coverage={coverage_percentage:.1f}%)")
                
                # Use CMYK angle for this color index, fallback to default
                angle = cmyk_angles[i] if i < len(cmyk_angles) else args.angle
                ht = generator.generate(enhanced, lpi=effective_lpi, angle=angle, 
                                       dot_shape=effective_dot_shape, dpi=args.dpi, gamma=halftone_gamma)
                result.append(ht)
                logger.info(f"  Halftoned mask {i+1} ({coverage_percentage:.1f}%) angle={angle}° LPI={effective_lpi} gamma={halftone_gamma}")
            
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
    _step(7.5, "Validating & fixing thin strokes")
    
    if not HAS_STROKE_VALIDATOR:
        logger.info("  StrokeValidator not available, skipping")
        return masks
    
    # Minimum stroke width: 0.15mm converted to pixels
    min_stroke_mm = 0.15
    min_stroke_px = max(1, int(args.dpi * min_stroke_mm / 25.4))
    
    result = []
    for i, mask in enumerate(masks):
        # Ensure mask is binary for CC analysis
        if len(mask.shape) == 3: gray = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
        else: gray = mask.copy()
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)

        # Find connected components on binary mask
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, 8, cv2.CV_32S)
        
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
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            mask = cv2.dilate(mask, kernel, iterations=1)
            # Gentle smoothing after dilation to prevent amplifying staircase artifacts
            mask = cv2.medianBlur(mask, 5)  # Increased from 3 to 5 for better aliasing removal
        
        result.append(mask)
    
    logger.info(f"  Stroke validation complete (min={min_stroke_px}px = {min_stroke_mm}mm)")
    return result


def step7_final_binarization(masks: list, args: argparse.Namespace) -> list:
    """
    MERGED PRODUCTION BINARIZATION with Edge-aware support (Phase 2).
    Uses EdgeAwareBinarizer for ARTWORK when enabled, falls back to standard Binarizer.
    """
    _step(7, "Production Binarization & Validation")
    
    # Check if edge-aware binarization is enabled
    use_edge_aware = getattr(args, 'edge_aware_bin', False) and HAS_EDGE_AWARE_BINARIZER
    
    if use_edge_aware:
        logger.info("  Using Edge-aware Binarizer for superior ARTWORK processing")
        config = EdgeAwareConfig(
            method=getattr(args, 'binarization_method', 'sauvola'),
            edge_preserve=getattr(args, 'edge_preserve', True),
            k=0.34 if getattr(args, 'binarization_method', 'sauvola') == 'sauvola' else 0.2,
            window_size=51,
            min_area=getattr(args, 'noise_removal', 3)
        )
        binarizer = EdgeAwareBinarizer(config)
    elif HAS_BINARIZER:
        logger.info("  Using standard Binarizer")
        binarizer = Binarizer()
    else:
        logger.warning("Binarizer not found. Falling back to simple Otsu.")
        result = []
        for m in masks:
            _, b = cv2.threshold(m, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            result.append(b)
        return result

    out = []
    total = len(masks)
    start_bin = time.time()
    
    for i, m in enumerate(masks):
        m_start = time.time()
        
        if use_edge_aware:
            # Use edge-aware binarizer
            binary = binarizer.binarize(m)
            
            # Get quality metrics
            metrics = binarizer.get_quality_metrics(m, binary)
            logger.info(f"  [Edge-aware] Mask {i+1}: edge_pres={metrics['edge_preservation']:.3f}, "
                       f"noise_red={metrics['noise_reduction']:.3f}")
        else:
            # Use standard binarizer
            if HAS_BINARIZER:
                binarizer._method_cache = {}  # Force fresh method selection per mask
                image_class = getattr(args, '_image_class', None)
                image_class_val = image_class.value if image_class and hasattr(image_class, 'value') else 'auto'
                
                # --- CRITICAL FIX: Force higher smoothing for text_logo and logo classes ---
                if image_class_val in ['text_logo', 'logo']:
                    args.smoothing_factor = max(getattr(args, 'smoothing_factor', 0.25), 0.35)
                    logger.info(f"  [Smoothing Fix] Forced smoothing_factor={args.smoothing_factor} for {image_class_val}")
                # --------------------------------------------------------------------
                
                binary = binarizer.binarize(m, method='auto', image_class=image_class_val, 
                                          global_threshold=getattr(args, 'global_threshold', 200))
            else:
                _, binary = cv2.threshold(m, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        m_elapsed = (time.time() - m_start) * 1000
        
        # Check if binarizer rejected the mask
        total_px = binary.size
        white_px = np.count_nonzero(binary == 255)
        if white_px / total_px > 0.999:
            logger.warning(f"  [Binarizer] Mask {i+1} REJECTED")
        else:
            logger.info(f"  [Binarizer] Mask {i+1} PROCESSED in {m_elapsed:.0f}ms")

        # Final Guard: Enforce polarity and audit
        if HAS_CONTROLLER:
            binary = controller.enforce_polarity(binary, stage=f"final_bin/{i+1}")
            controller.audit(binary, stage=f"final_bin_audit/{i+1}")

        # Noise removal (skip if edge-aware already handled it)
        if not use_edge_aware:
            noise_min_area = getattr(args, 'noise_removal', 3)
            if noise_min_area > 0:
                inv = cv2.bitwise_not(binary)
                num, labels, stats, _ = cv2.connectedComponentsWithStats(inv, 8, cv2.CV_32S)
                clean = np.full_like(binary, 255)
                for lbl in range(1, num):
                    if stats[lbl, cv2.CC_STAT_AREA] >= noise_min_area:
                        clean[labels == lbl] = 0
                binary = clean
            
        out.append(binary)
        _progress(((7 - 1) + (i + 1) / total) / TOTAL_STEPS, f"Binarized {i+1}/{total}")
        
    return out




def step3_5_trapping(masks: list, separation_result: dict, args: argparse.Namespace) -> list:
    """
    [TASK 5 FIX] Automatic color trapping (Polarity-Aware).
    Adds small overlaps (ink=0) between adjacent colors.
    """
    _step(3.5, "Trapping (automatic)")
    try:
        if len(masks) < 2:
            logger.info("Only one color layer, skipping trapping")
            return masks
        
        trapping_px = max(1, int(args.dpi * 0.1 / 25.4))
        logger.info(f"Applying trapping with {trapping_px}px overlap [Pol-Corrected]")
        
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (trapping_px * 2 + 1, trapping_px * 2 + 1))
        trapped_masks = []
        
        for i, mask in enumerate(masks):
            trapped = mask.copy()
            for j, other_mask in enumerate(masks):
                if i == j: continue
                # Both pixels are ink (0) in film polarity
                overlap = (mask == 0) & (other_mask == 0)
                if np.any(overlap):
                    # Dilate ink zone
                    dilated = cv2.dilate(overlap.astype(np.uint8), kernel, iterations=1)
                    # Expand ink (set pixels to 0) wherever dilated > 0
                    trapped[dilated > 0] = 0
            trapped_masks.append(trapped)
        
        return trapped_masks
    except Exception as e:
        logger.warning(f"Trapping failed: {e}")
        return masks

def _make_single_color_separation(image: np.ndarray, white_threshold: int = 240) -> dict:
    """[TASK 10] Bypasses K-means for TEXT_LOGO / monochrome images."""
    h, w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Label mapping: bg >= white_threshold → -1, design < white_threshold → 0
    label_map = np.full((h, w), -1, dtype=np.int32)
    label_map[gray < white_threshold] = 0
    
    ink_pixels = int(np.sum(label_map == 0))
    coverage = (ink_pixels / label_map.size) * 100
    
    # Calculate average color of ink pixels
    if ink_pixels > 0:
        center_bgr = np.mean(image[label_map == 0], axis=0).astype(np.float32)
    else:
        center_bgr = np.array([0, 0, 0], dtype=np.float32)
    
    # Build minimalist separation result
    return {
        'label_map': label_map,
        'centers': np.array([center_bgr]),
        'num_colors': 1,
        'colors': [(0, 0, 0)], # Default to black ink
        'color_names': ["Black"],
        'compactness': 0.0,
        'color_info': [{'index': 0, 'pixel_count': ink_pixels, 'percentage': coverage}]
    }


def process_calibration(args: argparse.Namespace) -> None:
    """Generate calibration materials for print validation"""
    _step(0, "Generating calibration materials")
    
    try:
        from core.print_calibration import get_calibration, CalibrationGridGenerator, PrintAccuracyValidator
        
        calib = get_calibration(args.dpi)
        grid_gen = CalibrationGridGenerator(calib)
        validator = PrintAccuracyValidator(calib)
        
        output_dir = Path(args.output)
        output_dir.mkdir(exist_ok=True)
        
        # 1. Generate mm grid (100x100mm)
        logger.info("  Generating millimeter grid...")
        grid = grid_gen.create_mm_grid(100.0, 100.0, 10.0)
        grid_path = output_dir / "calibration_grid_100x100mm.png"
        cv2.imwrite(str(grid_path), grid)
        logger.info(f"  Saved: {grid_path}")
        
        # 2. Generate test pattern (100x100mm)
        logger.info("  Generating test pattern...")
        pattern = grid_gen.create_test_pattern(100.0, 100.0)
        pattern_path = output_dir / "test_pattern_100x100mm.png"
        cv2.imwrite(str(pattern_path), pattern)
        logger.info(f"  Saved: {pattern_path}")
        
        # 3. Generate validation info
        validation_info = {
            'calibration': {
                'dpi': args.dpi,
                'pixels_per_mm': calib.pixels_per_mm,
                'pixels_per_cm': calib.pixels_per_cm,
                'mm_per_pixel': calib.mm_per_pixel
            },
            'grid_info': {
                'size_mm': (100.0, 100.0),
                'size_px': (calib.mm_to_pixels(100.0), calib.mm_to_pixels(100.0)),
                'grid_spacing_mm': 10.0
            },
            'usage': {
                'print_test': 'Print the grid and measure with ruler to validate 1:1 scaling',
                'test_pattern': 'Check line resolution, circle roundness, and text readability',
                'tolerance': 'Industry standard: ±1mm or ±1%, whichever is stricter'
            }
        }
        
        # Save validation info
        import json
        info_path = output_dir / "calibration_info.json"
        with open(info_path, 'w') as f:
            json.dump(validation_info, f, indent=2)
        logger.info(f"  Saved calibration info: {info_path}")
        
        logger.info("✅ Calibration materials generated successfully!")
        logger.info("📏 Print the grid and measure to validate 1:1 scaling accuracy")
        
    except ImportError as e:
        logger.error(f"Calibration module not available: {e}")
    except Exception as e:
        logger.error(f"Calibration generation failed: {e}")


def process_scale_validation(args: argparse.Namespace, image: np.ndarray) -> None:
    """Generate measurement template for scale validation"""
    _step(0, "Generating scale validation template")
    
    try:
        from core.print_calibration import get_calibration, PrintAccuracyValidator
        
        calib = get_calibration(args.dpi)
        validator = PrintAccuracyValidator(calib)
        
        h, w = image.shape[:2]
        
        # Create measurement template
        template = validator.create_measurement_template((w, h))
        
        output_dir = Path(args.output)
        output_dir.mkdir(exist_ok=True)
        
        template_path = output_dir / "scale_validation_template.png"
        cv2.imwrite(str(template_path), template)
        
        # Calculate expected real-world size
        real_w_mm = calib.pixels_to_mm(w)
        real_h_mm = calib.pixels_to_mm(h)
        
        logger.info(f"  Template saved: {template_path}")
        logger.info(f"  Design size: {w}x{h}px = {real_w_mm:.1f}x{real_h_mm:.1f}mm @ {args.dpi} DPI")
        logger.info("  Print this template and measure to validate scaling accuracy")
        
    except ImportError as e:
        logger.error(f"Calibration module not available: {e}")
    except Exception as e:
        logger.error(f"Scale validation failed: {e}")


def step8_registration_marks(masks: list, output_dir: str, args: argparse.Namespace) -> list:
    if masks and len(masks[0].shape) == 2:
        img_h, img_w = masks[0].shape
    else:
        img_w, img_h = 1000, 1000  # fallback
    
    # Use args.dpi instead of undefined dpi variable
    current_dpi = args.dpi
    
    # Proportional sizing: 3% of smallest dimension for marks
    base_dim = min(img_w, img_h)
    mark_target_mm = max(5, (base_dim / current_dpi) * 25.4 * 0.03)  # 3% of image size, min 5mm
    line_target_mm = max(0.15, mark_target_mm * 0.04)  # 4% of mark size, min 0.15mm
    quiet_zone_mm = max(15, mark_target_mm * 3)  # 3x mark size, min 15mm
    
    safe_border = max(120, int(current_dpi * quiet_zone_mm / 25.4))
    safe_mark_size = max(40, int(current_dpi * mark_target_mm / 25.4))
    safe_line_thickness = max(1, int(current_dpi * line_target_mm / 25.4))
    
    config = RegistrationConfig(
        add_border=True,
        border_size=safe_border,
        mark_type='full',
        dpi=current_dpi,
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
            
            # Only re-threshold if mask has more than 2 unique values (not already binary)
            # This preserves any anti-aliasing or sub-pixel smoothing from prior stages
            unique_vals = np.unique(processed_mask)
            if len(unique_vals) > 2:
                _, processed_mask = cv2.threshold(processed_mask, 127, 255, cv2.THRESH_BINARY)
                logger.info(f"  Applied re-thresholding to non-binary mask {idx+1}")
            else:
                logger.info(f"  Mask {idx+1} already binary, skipping re-threshold to preserve edge smoothing")
        else:
            processed_mask = raw_mask.copy()

        # 2. المرحلة الثانية: إضافة العلامات والاسم الحاد (Marks & Branding)
        # Masks are kept in film polarity: 0 (black ink) on 255 (white paper).
        marked = generator.add_marks(
            image=processed_mask,
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

        # Add "Developed By MO2" branding — bottom-right corner, clearly visible
        h_brand, w_brand = marked.shape[:2]
        brand_text = "Developed By MO2"
        
        # Fixed scale and thickness for visibility
        brand_scale = 0.8
        thickness = 2
        (tw, th), baseline = cv2.getTextSize(brand_text, cv2.FONT_HERSHEY_SIMPLEX, brand_scale, thickness)
        
        # Position: bottom-right with safe margin
        brand_margin = max(60, int(w_brand * 0.05))
        x_pos = w_brand - tw - brand_margin
        y_pos = h_brand - brand_margin
        
        # Ensure coordinates are within image bounds
        x_pos = max(10, min(x_pos, w_brand - tw - 10))
        y_pos = max(th + 10, min(y_pos, h_brand - 10))
        
        # Draw white background rectangle for readability
        pad = 10
        bg_x1 = max(0, x_pos - pad)
        bg_y1 = max(0, y_pos - th - pad)
        bg_x2 = min(w_brand, x_pos + tw + pad)
        bg_y2 = min(h_brand, y_pos + baseline + pad)
        cv2.rectangle(marked, (bg_x1, bg_y1), (bg_x2, bg_y2), (255, 255, 255), -1)
        
        # Draw black text
        cv2.putText(
            marked, 
            brand_text, 
            (x_pos, y_pos),
            cv2.FONT_HERSHEY_SIMPLEX, 
            brand_scale, (0, 0, 0), thickness, cv2.LINE_AA
        )
        logger.info(f"  Branding: '{brand_text}' at ({x_pos},{y_pos}) size {tw}x{th} on {w_brand}x{h_brand}")

        result_masks.append(marked)
        _progress(((8-1) + (idx+1)/len(masks)) / TOTAL_STEPS, f"Marks {idx+1}/ {len(masks)}")
    
    return result_masks


def step9_export(
    cache: ProcessedFilmCache,
    separation_result: dict,
    output_dir: str,
    args: argparse.Namespace,
    analysis = None,
) -> list:
    _step(9, "Exporting films (PNG + PDF + SVG)")
    os.makedirs(output_dir, exist_ok=True)
    output_dir = os.path.normpath(output_dir)

    exported_paths = []
    pdf_paths = []

    try:
        # Extract masks from cache films
        masks = [film.final_mask for film in cache.films]
        total = max(1, len(masks))
        
        if HAS_CONTROLLER:
            from core.pipeline_controller import PipelineController
            controller = PipelineController()
            
        # PHASE 22: Smart Smoothing Hierarchy (Senior Standard)
        # Priority: (1) CLI Argument > (2) Smart Analysis Result > (3) Conservative Default (0.15)
        # This prevents "melted detail" by honoring the auto-detected smooth_factor from Step 0.
        cli_smooth = getattr(args, 'smoothing_factor', None)
        
        if cli_smooth is not None and cli_smooth > 0:
            eff_smooth = cli_smooth
        elif analysis is not None:
            eff_smooth = getattr(analysis, 'smoothing_factor', 0.15)
        else:
            # Last resort fallback: default to artwork level
            eff_smooth = 0.15
            
        logger.info(f"  [Export] Using effective smoothing factor: {eff_smooth}")
        
        logger.info(f"  [Export] Modules status: ReportLab={REPORTLAB_AVAILABLE}, SVGWrite={SVGWRITE_AVAILABLE}, VectorExporter={HAS_VECTOR_EXPORTER}")
        
        # We collect all valid masks for the combined PDF
        all_masks_for_pdf = []
        all_colors_for_pdf = []
        all_names_for_pdf = []
        
        # A4 margins for PDF layout (points)

        total = max(1, len(cache.films))

        for film in cache.films:
            i = film.film_index
            mask = film.final_mask
            
            # Skip masks with no design pixels (all black -> now all white 255 since we inverted)
            if len(mask.shape) == 3:
                is_empty = np.sum(cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY) < 128) == 0
            else:
                is_empty = np.sum(mask < 128) == 0
                
            if is_empty:
                logger.info(f"  Skipping empty mask {i+1}")
                continue

            # Use color info from film cache (already populated)
            color_entry = film.color_rgb
            name_entry = film.color_name
            
            # Use cached processing parameters
            eff_smooth = film.smooth_factor
            eff_corner = film.corner_threshold
            eff_no_blur = film.use_potrace_style
            
            # 1. Save PNG for UI preview (Pure Binary)
            png_filename = f"film_{i+1}.png"
            png_filepath = os.path.join(output_dir, png_filename)
            # Ensure consistent film polarity for previews: black artwork (ink) on white background (paper)
            # Internally, vector tracing uses design=255, but film output is 0-ink / 255-paper.
            # Save PNG in final film polarity to match PDFs.
            preview_mask = mask.copy()
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
                # FIXED: Enforce polarity first via PipelineController
                film_mask = mask

                
                if len(film_mask.shape) == 3:
                    ink_mask = cv2.bitwise_not(cv2.cvtColor(film_mask, cv2.COLOR_BGR2GRAY))
                else:
                    ink_mask = cv2.bitwise_not(film_mask)
                    
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
            
            # 3. Save individual PDF
            if REPORTLAB_AVAILABLE:
                pdf_filename = f"film_{i+1}.pdf"
                pdf_filepath = os.path.join(output_dir, pdf_filename)
                
                # FIXED: Ensure 1-channel grayscale
                mask_gray = mask if len(mask.shape) == 2 else cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
                film_gray = mask_gray

                
                # Add to combined list
                all_masks_for_pdf.append(film_gray)
                all_colors_for_pdf.append(color_entry)
                all_names_for_pdf.append(name_entry)
                
                # CHOICE: Raster (Image) for Halftone vs Vector (Bezier) for Solid
                is_halftone = film.is_halftone
                
                if is_halftone:
                    dot_count = int(np.sum(film_gray < 127))
                    dot_ratio = float(dot_count) / float(max(1, film_gray.size))
                    use_raster = (dot_count >= 50000) or (dot_ratio >= 0.03)

                    mode = "Raster" if use_raster else "Vector"
                    logger.info(f"  [Export] Rendering halftone {pdf_filename} as {mode} PDF (dots={dot_count}, ratio={dot_ratio:.2%})")
                    
                    c = rl_canvas.Canvas(pdf_filepath, pagesize=A4)

                    # CRITICAL FIX: Halftone must ALWAYS be raster (Industry Standard)
                    # Vector halftone causes crashes and quality issues
                    use_raster = True  # Force raster for all halftone
                    logger.info(f"  [Export] FORCED: Halftone {pdf_filename} as RASTER PDF (industry standard)")

                    if use_raster:
                        render_raster_halftone(c, film_gray, args.dpi, A4[0], A4[1])
                    else:
                        # This branch should never be reached - kept for compatibility only
                        render_vector_halftone(c, film_gray, color_entry, A4[1])
                    c.save()
                    exported_paths.append(pdf_filepath)
                else:
                    # TRUE HIGH-FIDELITY VECTOR for solids
                    # REVERT: vector_exporter expects ink=255 (design=white) for findContours
                    # film_gray has ink=0 (film polarity) → must invert
                    ink_mask_pdf = cv2.bitwise_not(film_gray)

                    export_vector_pdf(
                        masks=[ink_mask_pdf],
                        colors=[color_entry],
                        color_names=[name_entry],
                        output_path=Path(pdf_filepath),
                        dpi=args.dpi,
                        smooth_factor=eff_smooth,
                        corner_threshold=eff_corner,
                        no_vector_blur=eff_no_blur,
                        image_class=film.image_class
                    )
                    exported_paths.append(pdf_filepath)
                
                logger.info(f"  Exported {pdf_filename} (Smooth: {eff_smooth}, Corner: {eff_corner}, NoBlur: {eff_no_blur})")

            _progress(((9 - 1) + (i + 1) / total) / TOTAL_STEPS, f"Exported {i+1}/{total}")
        
        # 4. Save combined PDF
        if args.combine_pdf and REPORTLAB_AVAILABLE and all_masks_for_pdf:
            combined_pdf_path = os.path.join(output_dir, "all_films_combined.pdf")

            # REVERT: vector_exporter expects ink=255 - must invert masks
            ink_masks_combined = [cv2.bitwise_not(m) for m in all_masks_for_pdf]
            
            # Add audit assertion to ensure correct polarity (BUG-04 fix)
            for i, m in enumerate(all_masks_for_pdf):
                mean = np.mean(m)
                if mean <= 127:
                    logger.warning(f'  [Export] WARNING: all_masks_for_pdf[{i}] has mean={mean:.1f} — polarity may be wrong')
            
            # Use cached parameters from first film (consistent across all films)
            first_film = cache.films[0] if cache.films else None
            eff_corner = first_film.corner_threshold if first_film else 150.0
            eff_no_blur = first_film.use_potrace_style if first_film else False
                
            export_vector_pdf(
                masks=ink_masks_combined,  # Inverted masks for correct polarity
                colors=all_colors_for_pdf,
                color_names=all_names_for_pdf,
                output_path=Path(combined_pdf_path),
                dpi=args.dpi,
                smooth_factor=eff_smooth,
                corner_threshold=eff_corner,
                no_vector_blur=eff_no_blur,
                image_class=first_film.image_class if first_film else 'auto'
            )
            exported_paths.append(combined_pdf_path)
            logger.info(f"  Exported all_films_combined.pdf (Smooth: {eff_smooth})")
        
    except Exception as e:
        logger.error(f"  [Export] CRITICAL ERROR: {e}", exc_info=True)
        # Don't silence the exception - if export fails, we should know
        raise

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
    parser.add_argument("--dpi", type=int, default=300, help="Output DPI (industry standard for screen printing)")
    parser.add_argument("--halftone", action="store_true", help="Enable halftone mode")
    parser.add_argument("--lpi", type=int, default=65, help="Halftone LPI (lines per inch)")
    parser.add_argument("--dot-shape", choices=["round", "square", "ellipse"], default="round", help="Halftone dot shape")
    parser.add_argument("--detail-level", choices=["high", "medium", "low"], default="medium")
    parser.add_argument("--clean", action="store_true", help="Apply edge cleaning")
    parser.add_argument("--validate-strokes", action="store_true", help="Validate stroke widths")
    parser.add_argument("--min-stroke", type=float, default=0.0, help="Min stroke width in mm (disabled)")
    parser.add_argument("--edge-enhance", choices=["none", "light", "strong"], default="light")
    parser.add_argument(
        '--calibration', action='store_true',
        help='Generate calibration grid and test pattern for print validation'
    )
    parser.add_argument(
        '--validate-scale', action='store_true',
        help='Validate 1:1 scaling accuracy with measurement template'
    )
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
    parser.add_argument("--global-threshold", type=int, default=200, help="Global threshold for solid masks (0-255)")
    parser.add_argument("--smoothing-factor", type=float, default=0.3, help="Bezier smoothing factor (0-1.0)")
    parser.add_argument("--corner-threshold", type=float, default=45.0, help="Angle threshold to preserve sharp corners (degrees)")
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
    parser.add_argument(
        "--mesh-count", type=int, default=160,
        help="Screen mesh count (e.g. 86, 110, 160, 200, 305). Higher mesh = finer LPI."
    )

    parser.add_argument(
        "--auto-fix-lpi", action="store_true",
        help="Auto-adjust LPI to match industry mesh/LPI ratio (4-5) when out of range"
    )
    
    # Phase 2B: Dot Gain Compensation Controls (Production-grade defaults)
    parser.add_argument(
        "--dot-gain-radius", type=float, default=0.9,
        help="Dot gain compensation (0.85-1.1 typical for screen printing, 1.0=no gain)"
    )
    parser.add_argument(
        "--dot-gain-curve", choices=["linear", "exponential", "logarithmic", "sigmoid"], 
        default="sigmoid",
        help="Dot gain compensation curve type (sigmoid recommended for production)"
    )
    
    # Phase 2: Edge-aware Binarization Controls
    parser.add_argument(
        "--edge-aware-bin", action="store_true",
        help="Enable edge-aware binarization for superior ARTWORK processing"
    )
    parser.add_argument(
        "--binarization-method", choices=["sauvola", "niblack", "guided"], 
        default="sauvola",
        help="Edge-aware binarization method (sauvola recommended for artwork)"
    )
    parser.add_argument(
        "--edge-preserve", action="store_true", default=True,
        help="Preserve edges during binarization (recommended for sharp artwork)"
    )
    
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    start_time = time.time()
    _check_modules()

    # ═══ Auto-set parameters based on image type ═══
    # When image_type is simple/mixed/complex, override all related params unconditionally.
    # When image_type is auto, respect CLI-provided values or defaults.
    img_type = getattr(args, 'image_type', 'auto')

    if img_type == 'simple':
        args.smoothing_factor = 0.15
        args.corner_threshold = 45.0
        args.global_threshold = 160
        logger.info("[ImageType] Simple (text/logo): smooth=%.2f, corner=%.1f°, threshold=%d" % (args.smoothing_factor, args.corner_threshold, args.global_threshold))
    elif img_type == 'mixed':
        args.smoothing_factor = 0.20
        args.corner_threshold = 45.0
        args.global_threshold = 200
        logger.info("[ImageType] Mixed: smooth=%.2f, corner=%.1f°, threshold=%d" % (args.smoothing_factor, args.corner_threshold, args.global_threshold))
    elif img_type == 'complex':
        args.smoothing_factor = 0.25
        args.corner_threshold = 50.0
        args.global_threshold = 200
        logger.info("[ImageType] Complex: smooth=%.2f, corner=%.1f°, threshold=%d" % (args.smoothing_factor, args.corner_threshold, args.global_threshold))
    else:
        # Auto: keep CLI-provided values or defaults (smoothing_factor, corner_threshold, global_threshold)
        logger.info("[ImageType] Auto: using CLI/default parameters (smooth=%.2f, corner=%.1f°, threshold=%d)" % (args.smoothing_factor, args.corner_threshold, args.global_threshold))

    # Safety clamp: keep within UI semantics
    try:
        args.corner_threshold = float(args.corner_threshold)
    except Exception:
        args.corner_threshold = 45.0
    args.corner_threshold = max(0.0, min(90.0, args.corner_threshold))

    logger.info("=" * 50)
    logger.info("Virtual Design — Silk Screen Processing Pipeline")
    logger.info(f"Input:  {args.input}")
    logger.info(f"Output: {args.output}")
    logger.info(f"Colors: {args.colors} | DPI: {args.dpi} | Halftone: {args.halftone}")
    logger.info("=" * 50)

    # Handle calibration mode
    if args.calibration:
        process_calibration(args)
        return 0
    
    output_dir = args.output
    logger.info(f"Root Output Directory: {output_dir}")

    # TASK 3: Instantiate PrintJobConfig and clamp LPI
    job_config = PrintJobConfig(
        mesh_count=args.mesh_count,
        dpi=args.dpi,
    )
    args.lpi = job_config.validate_lpi(args.lpi, auto_fix=getattr(args, 'auto_fix_lpi', False))
    logger.info(f"[JobConfig] Mesh: {args.mesh_count} | Effective LPI: {args.lpi}")

    try:
        # Step 2 — Load
        # Step 1.1 — Load original for analysis (NO upscale to avoid artifacts)
        image_orig = load_image_safely(args.input)
        if len(image_orig.shape) > 2 and image_orig.shape[2] == 4:
            image_orig = image_orig[:, :, :3]

        # Step 0 — Smart Analysis (NEW)
        if HAS_SMART_ANALYZER and img_type == 'auto':
            _step(0, "Smart Image Analysis")
            analyzer = SmartAnalyzer()
            analysis = analyzer.analyze(image_orig, dpi=args.dpi)

            
            # Override args based on analysis (only if user didn't set manually)
            args.smoothing_factor = analysis.smoothing_factor
            args.corner_threshold = analysis.corner_threshold
            args.global_threshold = analysis.global_threshold
            # ❌ لا تـoverride الـ halftone — المستخدم هو اللي بيقرر solid أو halftone
            # args.halftone = analysis.use_halftone  
            args.lpi = analysis.lpi
            
            # Store image class for later use in pipeline steps
            args._image_class = analysis.image_class
            args._analysis_confidence = analysis.confidence
            
            # Auto-detect colors if not specified
            if args.colors == 0:
                args.colors = analysis.num_colors  # 0 = auto-detect
            
            logger.info(f"[SmartAnalyzer] Class: {analysis.image_class.value} | "
                       f"Confidence: {analysis.confidence:.0%} | "
                       f"Halftone: {args.halftone} | Smooth: {args.smoothing_factor}")
        else:
            # Fallback to existing logic for non-auto modes
            args._image_class = None
            args._analysis_confidence = 0.0
        
        # Now upscale for processing
        image = step1_load_image(args.input)
        
        # Handle scale validation mode
        if args.validate_scale:
            process_scale_validation(args, image)
            return 0

        
        # Step 2.5 — Auto Crop (Senior Optimization)
        if args.auto_crop:
            image = step0_auto_crop(image)

        # TASK 18: Specialized Pipeline Routing
        # Replaces steps 2.75 to 7.5 with classes-specific logic.
        from core.pipeline_router import PipelineRouter
        router = PipelineRouter(job_config)
        
        # Smart analysis needed for routing; analysis_obj is 'analysis' from Step 0
        analysis_obj = analysis if img_type == 'auto' and HAS_SMART_ANALYZER else None
        if not analysis_obj:
            # Create a mock analysis object if SmartAnalyzer was skipped
            from core.smart_analyzer import SmartResult, ImageClass
            analysis_obj = SmartResult(image_class=ImageClass.ARTWORK, num_colors=args.colors or 4, confidence=1.0)

        pipeline_result = router.route(image, analysis_obj, args)
        
        masks = pipeline_result.masks
        separation_result = pipeline_result.separation_result
        _route_class = pipeline_result.image_class
        skip_binarization = pipeline_result.skip_binarization

        # Step 3.5 — Automatic Underbase Creation (Artwork ONLY)
        if _route_class == 'artwork' and args.underbase_mode == 'automatic' and HAS_PANTONE:
            separation_result = step2_5_underbase_creation(separation_result, args)

        # Step 4.5 — Automatic Trapping (Artwork ONLY)
        if _route_class == 'artwork' and args.trapping_mode == 'automatic' and HAS_PANTONE:
            masks = step3_5_trapping(masks, separation_result, args)

        # Step 5 — Edge Cleaning (Artwork ONLY, skip for photos/halftone)
        if _route_class == 'artwork' and not args.halftone:
            masks = step4_clean_edges(masks, analysis_obj.image_class, dpi=args.dpi)

        # Step 7 — Final Binarization (Artwork ONLY, skip if router already binarized/halftoned)
        if not skip_binarization and _route_class == 'artwork':
            # Perform final production binarization only on vector-style artwork
            masks = step7_final_binarization(masks, args)
        
        # Step 7.5 — Stroke Validation (Logo/Artwork only)
        if _route_class in ['artwork', 'text_logo']:
            masks = step7_validate_strokes(masks, args)

        # Step 8 — Registration Marks (ALL)
        masks = step8_registration_marks(masks, output_dir, args)
        
        # Create ProcessedFilmCache — Lock Preview Output (BUG-01 fix)
        cache = ProcessedFilmCache()
        for i, mask in enumerate(masks):
            color_entry = separation_result['colors'][i] if i < len(separation_result['colors']) else (0,0,0)
            name_entry  = separation_result['color_names'][i] if i < len(separation_result['color_names']) else f'Film_{i+1}'
            
            # Determine effective smoothing factor (Senior Standard hierarchy)
            cli_smooth = getattr(args, 'smoothing_factor', None)
            
            # CRITICAL FIX: Use higher smoothing for TEXT_LOGO to eliminate aliasing
            # Zero smoothing = pure polygonal output (visible pixel staircases)
            # Industry standard: moderate Bezier smoothing even for sharp logos
            if _route_class == 'text_logo':
                eff_smooth = 0.35  # Increased from 0.15 to 0.35 for better anti-aliasing
                eff_corner = 120.0  # Moderate corner preservation
                eff_potrace = True  # Use potrace-style processing
                logger.info('[Cache] TEXT_LOGO pipeline: smoothing=0.35, corners=120.0, potrace=True')
            elif cli_smooth is not None and cli_smooth > 0:
                eff_smooth = cli_smooth
                eff_corner = getattr(analysis_obj, 'corner_threshold', 150.0)
                eff_potrace = getattr(analysis_obj, 'use_potrace_style', False)
            elif analysis_obj is not None:
                eff_smooth = getattr(analysis_obj, 'smoothing_factor', 0.15)
                eff_corner = getattr(analysis_obj, 'corner_threshold', 150.0)
                eff_potrace = getattr(analysis_obj, 'use_potrace_style', False)
            else:
                eff_smooth = 0.15
                eff_corner = 150.0
                eff_potrace = False
            
            cache.films.append(LockedFilm(
                final_mask=mask,
                color_rgb=color_entry,
                color_name=name_entry,
                film_index=i,
                image_class=_route_class,
                smooth_factor=eff_smooth,
                corner_threshold=eff_corner,
                use_potrace_style=eff_potrace,
                is_halftone=args.halftone or (analysis_obj is not None and getattr(analysis_obj, 'use_halftone', False)),
            ))
        cache.lock()  # Snapshot all masks — export is now deterministic
        
        # Debug output removed — was writing unconditional debug_mask_* files to output dir.
        # Re-enable with --debug flag if needed in future.

        # Step 9 — Exporting films (PNG + PDF + SVG)
        exported = step9_export(cache, separation_result, output_dir, args, analysis=analysis_obj)

        elapsed = round(time.time() - start_time, 1)
        logger.info(f"Pipeline complete in {elapsed}s. {len(exported)} films exported.")

        # Output validation: warn if no files were exported or files are 0 bytes
        valid_exports = [p for p in exported if os.path.exists(p) and os.path.getsize(p) > 0]
        
        # Professional Guard: If PDFs were requested but none made
        pdf_exports = [p for p in valid_exports if p.endswith('.pdf')]
        was_pdf_requested = getattr(args, 'combine_pdf', True)
        
        if was_pdf_requested and not pdf_exports:
            if not REPORTLAB_AVAILABLE:
                logger.error("[Export] PDF generation requested but failed (reportlab missing).")
                print("FATAL:PDF_NOT_EXPORTED:Dependency Missing", flush=True)
                return 4
            else:
                logger.error("[Export] PDF generation FAILED despite reportlab being available. Check logs above.")
                print("FATAL:PDF_NOT_EXPORTED:Generation Failed", flush=True)
                return 5

        if not valid_exports:
            logger.error("[Validation] No valid output files produced! All masks may have been empty.")
            # Still exit 0 so Flutter gets the OUTPUT_DIR signal, but user sees warning in logs
        else:
            logger.info(f"[Validation] {len(valid_exports)}/{len(exported)} files valid (non-empty).")
        zero_byte = [p for p in exported if os.path.exists(p) and os.path.getsize(p) == 0]
        if zero_byte:
            logger.warning(f"[Validation] {len(zero_byte)} zero-byte file(s): {zero_byte}")

        # 3. Final Content Audit: List every file written to output dir
        final_files = os.listdir(output_dir)
        logger.info(f"[FinalAudit] Files in {output_dir}: {final_files}")

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
