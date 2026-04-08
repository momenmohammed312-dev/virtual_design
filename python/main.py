"""
main.py — Production Orchestrator for Silk Screen Pipeline
Virtual Design Silk Screen Studio

Architecture:
- AI Analyzer: core/ai_vision_bridge.py
- Pipeline Router: core/pipeline_router.py
- Processing Engine: Integrated within specialized router paths

Memory Optimization: < 2GB RAM
Implementation: Senior Computer Vision Engineer
"""

import argparse
import json
import logging
import os
import sys
import time
import gc
import io
from pathlib import Path
from typing import Dict, List, Optional

# إجبار المخرجات على استخدام UTF-8 لتجنب مشاكل التشفير في ويندوز
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import cv2
import numpy as np

# System path setup
sys.path.insert(0, str(Path(__file__).parent))

# Modular Imports
from core.image_loader import load_image_safely
from core.print_job_config import PrintJobConfig
from core.pipeline_router import PipelineRouter, PipelineResult
from core.pipeline_controller import PipelineController

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("SilkScreenPipeline")

# ─── Progress Signaling (Flutter Bridge) ──────────────────────────────────────

def _step(n: int, msg: str):
    print(f"\nStep {n}/10: {msg}\n", flush=True)

def _progress(pct: float, msg: str = ""):
    print(f"PROGRESS:{pct:.1f}:{msg}", flush=True)

def _output_dir_signal(path: str):
    print(f"OUTPUT_DIR:{os.path.abspath(path)}", flush=True)

# ─── Main Pipeline ────────────────────────────────────────────────────────────

def run_pipeline(args: argparse.Namespace) -> int:
    """Main execution orchestrator."""
    start_time = time.time()
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True, parents=True)

    _step(1, "Loading and Normalizing Engine")
    
    # 1. Configuration
    job_config = PrintJobConfig(
        mesh_count=args.mesh_count,
        dpi=args.dpi,
    )
    # Clamp LPI to mesh constraints
    args.lpi = job_config.validate_lpi(args.lpi, auto_fix=getattr(args, 'auto_fix_lpi', False))
    
    # 2. Loading (Memory-Safe)
    # 🔥 FIXED: Now receives alpha_mask from transparent PNGs
    image, alpha_mask = load_image_safely(args.input)
    if image is None:
        logger.error(f"Failed to load image: {args.input}")
        return 2
    
    # ⚡ No-copy float conversion if possible
    if len(image.shape) > 2 and image.shape[2] == 4:
        image = image[:, :, :3]
    
    h, w = image.shape[:2]
    
    # 🔥 Log alpha channel info for debugging
    if alpha_mask is not None:
        alpha_ratio = np.sum(alpha_mask) / alpha_mask.size
        logger.info(f"[Pipeline] Alpha mask loaded: {alpha_ratio:.1%} visible artwork, "
                   f"{1-alpha_ratio:.1%} transparent/background")
    
    # Score original image quality
    # 🔥 Pass alpha_mask to PipelineRouter for transparent PNG handling
    router = PipelineRouter(job_config, alpha_mask=alpha_mask)
    qual_score = router.halftone_gen.evaluate_quality(image)
    logger.info(f"Image loaded: {w}x{h} | Quality Score: {qual_score:.1f}")
    _progress(0.1, "Image Loaded")

    # 3. Decision Logic (AI Analyzer + Pipeline Router)
    _step(2, "AI Image Analysis & Routing")
    
    # --- AI Autopilot: Hybrid OpenCV + Qwen3-VL ---
    # Task 3.4 FIX: Only run auto-colors when user hasn't explicitly set color count
    # Check if colors is 0 (auto) and auto-colors flag is enabled
    user_color_count = getattr(args, 'colors', 0)
    if getattr(args, 'auto_colors', False) and user_color_count == 0 and args.image_type == 'auto':
        try:
            from core.ai_vision_bridge import analyze_image, apply_to_args
            from core.color_separator import ColorSeparator
            
            logger.info("[Main] AI Autopilot enabled. Running hybrid color analysis...")
            
            # STEP 1: OpenCV K-Means extracts dominant colors
            separator = ColorSeparator()
            opencv_colors = separator.extract_dominant_colors_for_ai(image, max_colors=8)
            logger.info(f"[Main] OpenCV found {len(opencv_colors)} dominant colors")
            
            # STEP 2: AI decides which colors to merge/ignore
            ai_results = analyze_image(image, opencv_colors=opencv_colors)
            
            # STEP 3: Apply AI decisions to pipeline args
            apply_to_args(ai_results, args)
            
            _progress(0.3, "AI Analysis Complete")
        except Exception as e:
            logger.error(f"[Main] AI Bridge failed: {e}")
    elif user_color_count > 0:
        logger.info(f"[Main] Using user-specified color count: {user_color_count}")
    # ------------------------------------------
    
    # SmartAnalyzer Fallback for standard metadata
    try:
        from core.smart_analyzer import SmartAnalyzer
        analyzer = SmartAnalyzer()
        analysis_obj = analyzer.analyze(image, dpi=args.dpi)
    except ImportError:
        analysis_obj = None

    # Routing: Decides engine paths and extracts parameters
    result: PipelineResult = router.route(image, analysis_obj, args)
    
    _progress(0.4, f"Routed to {result.image_class.upper()}")
    
    # 🔗 ULTRA-CLEANUP: Free source image before heavy separation/export
    del image
    gc.collect()

    # 5. Specialized Processing (Post-Routing steps if needed)
    _step(3, "Final Edge Cleaning & Validation")
    
    controller = PipelineController()
    masks = result.masks
    
    # Step 4: Registration marks — VECTOR ONLY via export_vector_pdf
    # Raster RegistrationMarksGenerator is disabled to prevent double marks.
    _step(4, "Registration marks handled as vector in PDF export stage")

    # 6. Export Stage (Split by Image Class)
    _step(9, "Exporting Films")
    try:
        output_pdf = output_dir / "final_films.pdf"
        sep_res = result.separation_result

        if result.image_class == 'photo':
            # ── RASTER PATH: halftone mask → high-res raster PDF ──
            from reportlab.pdfgen import canvas as rl_canvas
            from reportlab.lib.pagesizes import A4, A3, letter
            from core.vector_exporter import render_raster_halftone
            from core.vector_marks import add_vector_marks_to_page

            page_sizes = {'A4': A4, 'A3': A3, 'LETTER': letter}
            page_w, page_h = page_sizes.get(
                getattr(args, 'page_size', 'A4').upper(), A4
            )

            c = rl_canvas.Canvas(str(output_pdf), pagesize=(page_w, page_h))

            for i, (mask, color_rgb, color_name) in enumerate(
                zip(masks, sep_res['colors'], sep_res['color_names'])
            ):
                if i > 0:
                    c.showPage()

                # White background
                c.setFillColorRGB(1, 1, 1)
                c.rect(0, 0, page_w, page_h, fill=1, stroke=0)

                # Raster halftone embed
                render_raster_halftone(c, mask, args.dpi, page_w, page_h)

                # Vector registration marks
                film_info = {'job_name': output_pdf.stem}
                add_vector_marks_to_page(
                    c, page_w, page_h, 65, color_rgb, color_name, film_info
                )

                # Task 4.1 FIX: Clean professional footer matching vector exporter format
                c.setFont("Helvetica", 9)
                c.setFillColorRGB(0, 0, 0)
                # Left footer: Film info with LPI
                c.drawString(
                    65, 50,
                    f"FILM {i+1}: {color_name}  |  DPI:{args.dpi}  |  LPI:{args.lpi}"
                )
                # Right footer: Brand and page number
                brand_text = f"Virtual Design Studio | {film_info.get('job_name', 'Untitled')} | Page {i+1}/{len(masks)}"
                c.drawRightString(page_w - 65, 50, brand_text)

            c.save()
            logger.info(
                f"[RasterExport] Saved: {output_pdf} ({len(masks)} films)"
            )

        else:
            # ── VECTOR PATH: solid/artwork/text → Bezier vector PDF ──
            from core.vector_exporter import export_vector_pdf
            # Use input image filename as job name for branding
            job_name = Path(args.input).stem if hasattr(args, 'input') and args.input else None
            # Determine if halftone was applied
            is_halftone = getattr(args, 'halftone', False) or result.image_class == 'photo'
            export_vector_pdf(
                masks=masks,
                colors=sep_res['colors'],
                color_names=sep_res['color_names'],
                output_path=output_pdf,
                dpi=args.dpi,
                smooth_factor=result.effective_smoothing or args.smoothing_factor,
                corner_threshold=getattr(args, 'corner_threshold', 120.0),
                min_contour_area=getattr(args, 'contour_min_area', 50),
                image_class=result.image_class,
                page_size=getattr(args, 'page_size', 'A4'),
                epsilon=getattr(args, 'simplification_epsilon', None),
                job_name=job_name,
                is_halftone=is_halftone,
            )

        # ── Generate PNG Previews for Flutter ──
        logger.info("[Preview] Generating PNG previews...")
        for i, (mask, color_name) in enumerate(zip(masks, sep_res['color_names'])):
            # Ensure mask is uint8
            if mask.dtype != np.uint8:
                mask = mask.astype(np.uint8)
            
            # Task 3.2 FIX: Correct preview inversion for silk-screen polarity
            # Silk-screen: ink=0 (black), background=255 (white/transparent)
            # Preview should show: black ink on white background (what you see when printing)
            mask_mean = np.mean(mask)
            if mask_mean < 127:
                # Mask is mostly black (ink-heavy), background is dark
                # Invert so preview shows black ink on white background
                preview_mask = cv2.bitwise_not(mask)
            else:
                # Mask is already mostly white (background), ink is visible as black
                # Use as-is for preview
                preview_mask = mask.copy()
            
            # Save as PNG
            preview_path = output_dir / f"film_{i+1}_{color_name.replace(' ', '_')}.png"
            cv2.imwrite(str(preview_path), preview_mask)
            logger.info(f"[Preview] Saved: {preview_path.name}")

        _progress(1.0, "Complete")

        # 🎯 Flutter JSON Bridge
        if getattr(args, 'json_output', False):
            res_json = {
                "status": "success",
                "pdf": str(output_pdf.absolute()),
                "layers": len(masks),
                "colors": sep_res['color_names'],
                "class": result.image_class,
                "elapsed": round(time.time() - start_time, 1)
            }
            print(f"\nRESULTS_JSON:{json.dumps(res_json)}", flush=True)

    except Exception as e:
        logger.error(f"Export failed: {e}", exc_info=True)
        return 1

    # Signal output directory to Flutter
    _output_dir_signal(str(output_dir))
    return 0

# ─── Arg Parsing ──────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Silk Screen Image Processing System")
    parser.add_argument("--input", required=True, help="Path to input image")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--dpi", type=int, default=300, help="Output resolution (DPI)")
    parser.add_argument("--mesh-count", type=int, default=160, help="Screen mesh count")
    parser.add_argument("--lpi", type=int, default=55, help="Halftone LPI limit")
    parser.add_argument("--colors", type=int, default=0, help="Number of colors (0=auto)")
    parser.add_argument("--image-type", choices=["text_logo", "artwork", "photo", "auto"], default="auto")
    parser.add_argument("--halftone", action="store_true", help="Force halftone mode")
    parser.add_argument("--combine-pdf", action="store_true", default=True)
    parser.add_argument("--smoothing-factor", type=float, default=0.25)
    parser.add_argument("--auto-fix-lpi", action="store_true", default=True)
    parser.add_argument("--use-underbase", action="store_true", help="Generate Underbase")
    parser.add_argument("--choke-px", type=int, default=2)
    parser.add_argument("--trapping-px", type=int, default=1)
    parser.add_argument("--page-size", choices=["A4", "A3", "LETTER"], default="A4")
    parser.add_argument("--json-output", action="store_true")

    # Advanced Professional Parameters
    parser.add_argument("--detail-level", choices=["low", "medium", "high"], default="medium")
    parser.add_argument("--clean", action="store_true", help="Perform deep edge cleaning")
    parser.add_argument("--validate-strokes", action="store_true", help="Ensure minimum stroke width")
    parser.add_argument("--min-stroke", type=float, default=0.5, help="Min stroke width in mm")
    parser.add_argument("--skip-halftone", action="store_true", help="Force skip halftone generation")
    parser.add_argument("--pantone-matching", choices=["disabled", "basic", "automatic"], default="automatic")
    parser.add_argument("--underbase-mode", choices=["disabled", "automatic", "forced"], default="disabled")
    parser.add_argument("--trapping-mode", choices=["disabled", "automatic"], default="automatic")
    parser.add_argument("--overprint-mode", choices=["disabled", "automatic"], default="automatic")
    parser.add_argument("--gradient-mesh-mode", choices=["disabled", "automatic"], default="automatic")
    parser.add_argument("--typography-mode", choices=["disabled", "automatic"], default="automatic")
    parser.add_argument("--mesh-preview-mode", choices=["disabled", "automatic"], default="automatic")
    parser.add_argument("--noise-removal", type=int, default=3, help="Noise removal strength (1-10)")
    parser.add_argument("--adaptive-threshold", action="store_true", help="Use adaptive binary thresholding")
    
    # Existing / Legacy
    parser.add_argument("--corner-threshold", type=float, default=-1.0)
    parser.add_argument("--global-threshold", type=int, default=200)
    parser.add_argument("--auto-crop", action="store_true")
    
    # AI Autopilot
    parser.add_argument("--auto-colors", action="store_true", help="Enable AI-based automatic parameters optimization")
    
    # AI Vision Extended Parameters
    parser.add_argument("--dot-shape", choices=["round", "ellipse", "line", "square"], default="round")
    parser.add_argument("--upscale-factor", type=float, default=1.0)
    parser.add_argument("--denoise-strength", type=int, default=3)
    parser.add_argument("--contour-min-area", type=int, default=50)
    parser.add_argument("--simplification-epsilon", type=float, default=1.2)
    parser.add_argument("--ai-autofix", action="store_true", help="Re-analyze and auto-correct pipeline params")
    
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    sys.exit(run_pipeline(args))
