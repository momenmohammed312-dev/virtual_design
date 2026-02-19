"""
main.py — Silk Screen Processing Pipeline (CLI Entry Point)
Virtual Design Silk Screen Studio

FIXES applied:
  - FATAL #3: Print OUTPUT_DIR: at the end so Dart can read it
  - FATAL #4: Print Step X/9 for each step so Dart can stream progress
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np

# Local imports
sys.path.insert(0, str(Path(__file__).parent))

from core.color_separator import ColorSeparator
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
    from core.registration_marks import RegistrationMarks
    HAS_REG_MARKS = True
except ImportError:
    HAS_REG_MARKS = False

try:
    from core.exporter import Exporter
    HAS_EXPORTER = True
except ImportError:
    HAS_EXPORTER = False

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

# ─── Pipeline Steps ──────────────────────────────────────────────────────────

def step1_load_image(input_path: str) -> np.ndarray:
    _step(1, "Loading image")
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Image not found: {input_path}")
    image = cv2.imread(input_path)
    if image is None:
        raise ValueError(f"Cannot read image: {input_path}")
    logger.info(f"Loaded image: {image.shape} from {input_path}")
    return image


def step2_separate_colors(image: np.ndarray, num_colors: int) -> dict:
    _step(2, f"Separating {num_colors} colors")
    separator = ColorSeparator()
    # If separator supports internal progress, it could emit callbacks.
    # Fallback: emit coarse progress markers before/after operation.
    _progress((2 - 1) / TOTAL_STEPS + 0.15, 'K-means starting')
    result = separator.separate(image, num_colors=num_colors)
    _progress((2 - 1) / TOTAL_STEPS + 0.9, 'K-means complete')
    logger.info(f"Colors: {[result['colors'][i] for i in range(num_colors)]}")
    return result


def step3_generate_masks(image: np.ndarray, separation_result: dict) -> list:
    _step(3, "Generating color masks")
    generator = MaskGenerator()
    masks = generator.generate_masks(image, separation_result)
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
    _step(5, "Halftone generation" if args.halftone else "Halftone (skipped)")
    if not args.halftone or not HAS_HALFTONE:
        return masks
    generator = HalftoneGenerator()
    result = []
    total = max(1, len(masks))
    for i, mask in enumerate(masks):
        ht = generator.generate(mask, lpi=args.lpi, dpi=args.dpi)
        result.append(ht)
        overall = ((5 - 1) + (i + 1) / total) / TOTAL_STEPS
        _progress(overall, f"Halftone {i+1}/{total}")
    return result


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
    _step(7, "Validating stroke widths")
    if not args.validate_strokes or not HAS_STROKE_VALIDATOR:
        return masks
    validator = StrokeValidator()
    total = max(1, len(masks))
    for i, mask in enumerate(masks):
        warnings = validator.validate(mask, min_stroke_mm=args.min_stroke, dpi=args.dpi)
        if warnings:
            for w in warnings:
                logger.warning(f"  Film {i+1}: {w}")
        else:
            logger.info(f"  Film {i+1}: stroke validation passed")
        _progress(((7 - 1) + (i + 1) / total) / TOTAL_STEPS, f"Validated {i+1}/{total}")
    return masks


def step8_registration_marks(masks: list, output_dir: str, args: argparse.Namespace) -> list:
    _step(8, "Adding registration marks")
    if not HAS_REG_MARKS:
        return masks
    reg = RegistrationMarks()
    result = []
    for mask in masks:
        marked = reg.add_marks(mask, dpi=args.dpi)
        result.append(marked)
    return result


def step9_export(
    masks: list,
    separation_result: dict,
    output_dir: str,
    args: argparse.Namespace,
) -> list:
    _step(9, "Exporting films")
    os.makedirs(output_dir, exist_ok=True)

    exported_paths = []

    if HAS_EXPORTER:
        exporter = Exporter(output_dir=Path(output_dir), dpi=args.dpi)
        paths = exporter.export_all_films(
            masks=masks,
            colors=separation_result["colors"],
            color_names=separation_result["color_names"],
        )
        exported_paths = [str(p) for p in paths]
    else:
        # Fallback: save as PNG
        generator = MaskGenerator()
        total = max(1, len(masks))
        for i, mask in enumerate(masks):
            film = generator.generate_film_image(mask)
            name = separation_result["color_names"][i]
            path = os.path.join(output_dir, f"{name}.png")
            cv2.imwrite(path, film)
            exported_paths.append(path)
            logger.info(f"  Saved: {path}")
            _progress(((9 - 1) + (i + 1) / total) / TOTAL_STEPS, f"Exported {i+1}/{total}")

        # حفظ preview مجمّع
        preview = generator.generate_combined_preview(
            masks, separation_result["colors"]
        )
        preview_path = os.path.join(output_dir, "preview_combined.png")
        cv2.imwrite(preview_path, preview)
        logger.info(f"  Saved preview: {preview_path}")

    # حفظ color info JSON
    _save_color_info(separation_result, output_dir)

    # Emit final progress 100% before returning
    _progress(1.0, 'Finished')

    return exported_paths


def _save_color_info(separation_result: dict, output_dir: str) -> None:
    """حفظ معلومات الألوان كـ JSON — يقرأها الـ PreviewController."""
    import json
    from core.color_separator import ColorSeparator

    separator = ColorSeparator()
    color_info = separator.get_color_info(separation_result)

    info_path = os.path.join(output_dir, "color_info.json")
    with open(info_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "num_colors": separation_result["num_colors"],
                "colors": color_info,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    logger.info(f"  Saved color info: {info_path}")


# ─── Main ────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Silk Screen Film Generator — Virtual Design Studio"
    )
    parser.add_argument("--input", required=True, help="Path to input image")
    parser.add_argument("--output", required=True, help="Output directory path")
    parser.add_argument("--colors", type=int, default=2, help="Number of colors (1-10)")
    parser.add_argument("--dpi", type=int, default=300, help="Output DPI")
    parser.add_argument("--halftone", action="store_true", help="Enable halftone mode")
    parser.add_argument("--lpi", type=int, default=65, help="Halftone LPI (lines per inch)")
    parser.add_argument("--detail-level", choices=["high", "medium", "low"], default="medium")
    parser.add_argument("--clean", action="store_true", help="Apply edge cleaning")
    parser.add_argument("--validate-strokes", action="store_true", help="Validate stroke widths")
    parser.add_argument("--min-stroke", type=float, default=0.3, help="Min stroke width in mm")
    parser.add_argument("--edge-enhance", choices=["none", "light", "strong"], default="light")
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
    os.makedirs(output_dir, exist_ok=True)

    try:
        # Step 1 — Load
        image = step1_load_image(args.input)

        # Step 2 — Color Separation
        separation_result = step2_separate_colors(image, args.colors)

        # Step 3 — Mask Generation
        masks = step3_generate_masks(image, separation_result)

        # Step 4 — Edge Cleaning
        if args.clean:
            masks = step4_clean_edges(masks)
        else:
            _step(4, "Edge cleaning (skipped)")

        # Step 5 — Halftone
        masks = step5_halftone(masks, args)

        # Step 6 — Binarize
        masks = step6_binarize(masks, args)

        # Step 7 — Stroke Validation
        masks = step7_validate_strokes(masks, args)

        # Step 8 — Registration Marks
        masks = step8_registration_marks(masks, output_dir, args)

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
