"""
main.py — Production Orchestrator for Silk Screen Pipeline
Virtual Design Silk Screen Studio
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
from typing import Dict, List, Optional, Any

# Force UTF-8 for Windows
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
from core.decision_engine import DecisionOracle
from core.physical_print_model import PhysicalPrintModel
from core import ai_vision_bridge

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("SilkScreenPipeline")

def _step(n: int, msg: str):
    print(f"\nStep {n}/10: {msg}\n", flush=True)

def _progress(pct: float, msg: str = ""):
    print(f"PROGRESS:{pct:.1f}:{msg}", flush=True)

def _output_dir_signal(path: str):
    print(f"OUTPUT_DIR:{os.path.abspath(path)}", flush=True)

def run_pipeline(args: argparse.Namespace) -> int:
    """Refactored orchestrator using the Unified Decision Engine."""
    start_time = time.time()
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True, parents=True)

    _step(1, "Unified Engine Initialization")
    
    # 1. Loading
    image, alpha_mask = load_image_safely(args.input)
    if image is None:
        logger.error(f"Failed to load image: {args.input}")
        return 2
    
    # 2. Decision Phase (The Oracle)
    _step(2, "Unified Decision Oracle — AI & Physics Analysis")
    ppm = PhysicalPrintModel(mesh_count=args.mesh_count)
    oracle = DecisionOracle()
    
    # Solve all parameters (AI + User + Rule + Physics)
    decision = oracle.solve(image, args, ai_vision_bridge, ppm)
    
    # Export Trace for transparency
    trace_path = output_dir / "decision_trace.json"
    with open(trace_path, "w", encoding="utf-8") as f:
        json.dump(oracle.get_summary_dict(), f, indent=2)
    
    logger.info(f"[Main] Decision exported to {trace_path}")
    logger.info(f"[Main] Resulting class: {decision.image_class.upper()}")
    _progress(0.4, f"Oracle: {decision.image_class.upper()}")

    # 3. Routing Phase
    _step(3, "Executing Pipeline Plan")
    job_config = PrintJobConfig(mesh_count=args.mesh_count, dpi=decision.parameters.get('dpi', 300))
    router = PipelineRouter(job_config, alpha_mask=alpha_mask)
    
    result: PipelineResult = router.route_deterministic(image, decision)
    
    # Cleanup memory
    del image
    gc.collect()

    # 4. Export Phase
    _step(9, "Exporting Films")
    try:
        output_pdf = output_dir / "final_films.pdf"
        masks = result.masks
        params = decision.parameters
        sep_res = result.separation_result

        if result.image_class in ('photo', 'artwork_halftone'):
            from reportlab.pdfgen import canvas as rl_canvas
            from reportlab.lib.pagesizes import A4, A3, letter
            from core.vector_exporter import render_raster_halftone
            from core.vector_marks import add_vector_marks_to_page

            page_sizes = {'A4': A4, 'A3': A3, 'LETTER': letter}
            page_name = params.get('page_size', 'A4').upper()
            
            # Check for Custom dimensions (converted from mm to points)
            custom_w = params.get('page_width', 0)
            custom_h = params.get('page_height', 0)
            
            if page_name == 'CUSTOM' and custom_w > 0 and custom_h > 0:
                # 1 mm = 2.83464567 points
                page_w, page_h = custom_w * 2.8346, custom_h * 2.8346
                logger.info(f"[Export] Using CUSTOM paper size: {custom_w}x{custom_h} mm")
            else:
                page_w, page_h = page_sizes.get(page_name, A4)
                
            margin_pt = params.get('margin_pt', 65.0)

            c = rl_canvas.Canvas(str(output_pdf), pagesize=(page_w, page_h))
            for i, (mask, color_rgb, color_name) in enumerate(zip(masks, sep_res['colors'], sep_res['color_names'])):
                if i > 0: c.showPage()
                c.setFillColorRGB(1, 1, 1)
                c.rect(0, 0, page_w, page_h, fill=1, stroke=0)
                
                render_raster_halftone(
                    c, mask, result.mask_dpi or params.get('dpi', 300),
                    page_w, page_h, margin_pt=margin_pt,
                    scale_mode=params.get('scale_mode', 'fit_to_page'),
                    custom_scale_percent=params.get('custom_scale_percent', 100.0),
                    custom_page_w=params.get('page_width', 0),
                    custom_page_h=params.get('page_height', 0),
                    fit_to_artwork=params.get('fit_artwork', False)
                )
                
                job_name = Path(args.input).stem
                add_vector_marks_to_page(c, page_w, page_h, margin_pt, color_rgb, color_name, {'job_name': job_name})
            c.save()
        else:
            from core.vector_exporter import export_vector_pdf
            # Determine page size string
            page_size_val = params.get('page_size', 'A4')
            if page_size_val.upper() == 'CUSTOM':
                # vector_exporter expects "WIDTHxHEIGHT" in mm if custom
                page_size_val = f"{params.get('page_width', 210)}x{params.get('page_height', 297)}"

            export_vector_pdf(
                masks=masks, colors=sep_res['colors'], color_names=sep_res['color_names'],
                output_path=output_pdf, dpi=params.get('dpi', 300), mask_dpi=result.mask_dpi,
                smooth_factor=params.get('smoothing_factor', 0.25),
                corner_threshold=params.get('corner_threshold', 120.0),
                min_contour_area=params.get('contour_min_area', 50),
                image_class=result.image_class, page_size=page_size_val,
                epsilon=params.get('simplification_epsilon', 1.2),
                job_name=Path(args.input).stem, is_halftone=params.get('halftone', False),
                args=args
            )

        # Previews
        for i, (mask, color_name) in enumerate(zip(masks, sep_res['color_names'])):
            preview_mask = cv2.bitwise_not(mask) if np.mean(mask) < 127 else mask.copy()
            cv2.imwrite(str(output_dir / f"film_{i+1}_{color_name.replace(' ', '_')}.png"), preview_mask)

        _progress(1.0, "Complete")
        if getattr(args, 'json_output', False):
            print(f"\nRESULTS_JSON:{json.dumps({'status': 'success', 'layers': len(masks)})}", flush=True)

    except Exception as e:
        logger.error(f"Export failed: {e}", exc_info=True)
        return 1

    _output_dir_signal(str(output_dir))
    return 0

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Silk Screen Image Processing System")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--mesh-count", type=int, default=160)
    parser.add_argument("--lpi", type=int, default=85)
    parser.add_argument("--colors", type=int, default=0)
    parser.add_argument("--image-type", choices=["text_logo", "artwork", "photo", "auto"], default="auto")
    parser.add_argument("--halftone", action="store_true")
    parser.add_argument("--skip-halftone", action="store_true")
    parser.add_argument("--smoothing-factor", type=float, default=0.25)
    parser.add_argument("--use-underbase", action="store_true")
    parser.add_argument("--choke-px", type=int, default=2)
    parser.add_argument("--trapping-px", type=int, default=1)
    parser.add_argument("--page-size", default="A4")
    parser.add_argument("--page-width", type=float, default=0)
    parser.add_argument("--page-height", type=float, default=0)
    parser.add_argument("--fit-artwork", action="store_true")
    parser.add_argument("--margin-pt", type=float, default=65.0)
    parser.add_argument("--json-output", action="store_true")
    parser.add_argument("--detail-level", choices=["low", "medium", "high"], default="medium")
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--validate-strokes", action="store_true")
    parser.add_argument("--min-stroke", type=float, default=0.5)
    parser.add_argument("--pantone-matching", choices=["disabled", "basic", "automatic"], default="automatic")
    parser.add_argument("--underbase-mode", choices=["disabled", "automatic", "forced"], default="disabled")
    parser.add_argument("--trapping-mode", choices=["disabled", "automatic"], default="automatic")
    parser.add_argument("--overprint-mode", choices=["disabled", "automatic"], default="automatic")
    parser.add_argument("--gradient-mesh-mode", choices=["disabled", "automatic"], default="automatic")
    parser.add_argument("--typography-mode", choices=["disabled", "automatic"], default="automatic")
    parser.add_argument("--mesh-preview-mode", choices=["disabled", "automatic"], default="automatic")
    parser.add_argument("--noise-removal", type=int, default=3)
    parser.add_argument("--adaptive-threshold", action="store_true")
    parser.add_argument("--corner-threshold", type=float, default=-1.0)
    parser.add_argument("--global-threshold", type=int, default=200)
    parser.add_argument("--auto-colors", action="store_true")
    parser.add_argument("--dot-shape", choices=["round", "ellipse", "line", "square"], default="ellipse")
    parser.add_argument("--upscale-factor", type=float, default=1.0)
    parser.add_argument("--denoise-strength", type=int, default=3)
    parser.add_argument("--contour-min-area", type=int, default=50)
    parser.add_argument("--simplification-epsilon", type=float, default=1.2)
    parser.add_argument("--ai-autofix", action="store_true")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    sys.exit(run_pipeline(args))
