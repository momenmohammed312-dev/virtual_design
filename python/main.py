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

    # LOG: Input parameters
    logger.info("=" * 60)
    logger.info("[Main] 📥 INPUT PARAMETERS:")
    for arg_name, arg_value in vars(args).items():
        logger.info(f"  {arg_name}: {arg_value}")
    logger.info("=" * 60)
    print("=" * 60, flush=True)
    print("📥 [Main] INPUT PARAMETERS:", flush=True)
    for arg_name, arg_value in vars(args).items():
        print(f"  {arg_name}: {arg_value}", flush=True)
    print("=" * 60, flush=True)

    # 1. Loading
    image, alpha_mask = load_image_safely(args.input)
    if image is None:
        logger.error(f"Failed to load image: {args.input}")
        return 2
    
    # 2. Decision Phase (The Oracle)
    _step(2, "Unified Decision Oracle — AI & Physics Analysis")
    
    # DEBUG: Log mesh_count explicitly
    mesh_count = getattr(args, 'mesh_count', 160)
    print(f"📊 [Main] MESH COUNT: {mesh_count}", flush=True)
    logger.info(f"[Main] MESH COUNT: {mesh_count}")
    
    ppm = PhysicalPrintModel(mesh_count=mesh_count)
    max_safe_lpi = ppm.get_max_safe_lpi()
    calculated_lpi = int(mesh_count / 4.5)
    print(f"📊 [Main] Calculated LPI (mesh/4.5): {calculated_lpi}, Max Safe LPI: {max_safe_lpi}", flush=True)
    logger.info(f"[Main] Calculated LPI: {calculated_lpi}, Max Safe: {max_safe_lpi}")
    
    oracle = DecisionOracle()
    
    # Solve all parameters (AI + User + Rule + Physics)
    decision = oracle.solve(image, args, ai_vision_bridge, ppm)
    
    from core.mobile_hints import apply_mobile_hints
    decision, mobile_mask = apply_mobile_hints(args, decision, image)
    
    # REPROCESS SINGLE LAYER AS HALFTONE
    reprocess_layer = getattr(args, 'reprocess_layer', -1)
    if reprocess_layer >= 0:
        logger.info(f"[Main] Reprocessing single layer {reprocess_layer} as halftone")
        args.halftone = True
        args.colors = 1
        # Force halftone pipeline for this specific layer only
        args._single_layer_reprocess = reprocess_layer
    if mobile_mask is not None:
        alpha_mask = mobile_mask
    
    # Export Trace for transparency
    trace_path = output_dir / "decision_trace.json"
    with open(trace_path, "w", encoding="utf-8") as f:
        json.dump(oracle.get_summary_dict(), f, indent=2)
    
    logger.info(f"[Main] Decision exported to {trace_path}")
    logger.info(f"[Main] Resulting class: {decision.image_class.upper()}")
    
    # DEBUG: Log final decision parameters
    final_lpi = decision.parameters.get('lpi', 0)
    final_halftone = decision.parameters.get('halftone', False)
    final_dpi = decision.parameters.get('dpi', 300)
    print(f"📊 [Main] FINAL DECISION: class={decision.image_class}, LPI={final_lpi}, DPI={final_dpi}, halftone={final_halftone}", flush=True)
    logger.info(f"[Main] FINAL: LPI={final_lpi}, DPI={final_dpi}, halftone={final_halftone}")
    
    _progress(0.4, f"Ai Decisions: {decision.image_class.upper()}")

    # 3. Routing Phase
    _step(3, "Executing Pipeline Plan")
    job_config = PrintJobConfig(mesh_count=args.mesh_count, dpi=decision.parameters.get('dpi', 300))
    print(f"📊 [Main] JOB CONFIG: mesh={job_config.mesh_count}, dpi={job_config.dpi}", flush=True)
    logger.info(f"[Main] JOB CONFIG: mesh={job_config.mesh_count}, dpi={job_config.dpi}")
    router = PipelineRouter(job_config, alpha_mask=alpha_mask)
    
    # Inject decision metadata into args for downstream logic (Halftone skip bypass, etc.)
    setattr(args, 'overrides', decision.explicit_user_overrides)
    setattr(args, 'reasoning', decision.reasoning)
    
    result: PipelineResult = router.route_deterministic(image, decision)
    _progress(0.6, "Generating film layers...")

    
    # Cleanup memory
    del image
    gc.collect()

    # 4. Export Phase
    _step(4, "High-DPI Film Generation & PDF Export")
    output_pdf = output_dir / f"{Path(args.input).stem}_films.pdf"

    try:
        from core.router_utils import safe_float
        masks = result.masks
        params = decision.parameters
        sep_res = result.separation_result

        if result.image_class in ('photo', 'artwork_halftone'):
            from reportlab.pdfgen import canvas as rl_canvas
            from reportlab.lib.pagesizes import A4, A3, letter
            from core.vector_exporter import render_raster_halftone
            from core.vector_marks import add_vector_marks_to_page
            _progress(0.85, "Exporting PDF film...")

            page_sizes = {'A4': A4, 'A3': A3, 'LETTER': letter}
            page_name = params.get('page_size', 'A4').upper()
            p_width = safe_float(params.get('page_width', 0))
            p_height = safe_float(params.get('page_height', 0))
            
            if page_name == 'CUSTOM' and p_width > 0 and p_height > 0:
                if round(p_width) == 210 and round(p_height) == 297:
                    page_name = 'A4'
                    page_w, page_h = A4
                    logger.info(f"[Export] Standardized CUSTOM 210x297 mm to A4")
                else:
                    # 1 mm = 2.83464567 points
                    page_w, page_h = p_width * 2.8346, p_height * 2.8346
                    logger.info(f"[Export] Using CUSTOM paper size: {p_width}x{p_height} mm")
            else:
                page_w, page_h = page_sizes.get(page_name, A4)
                
            margin_pt = safe_float(params.get('margin_pt', 28.35))

            c = rl_canvas.Canvas(str(output_pdf), pagesize=(page_w, page_h))
            for i, (mask, color_rgb, color_name) in enumerate(zip(masks, sep_res['colors'], sep_res['color_names'])):
                if i > 0: c.showPage()
                c.setFillColorRGB(1, 1, 1)
                c.rect(0, 0, page_w, page_h, fill=1, stroke=0)
                
                render_raster_halftone(
                    c, mask, result.mask_dpi or params.get('dpi', 300),
                    page_w, page_h, margin_pt=margin_pt,
                    scale_mode=params.get('scale_mode', 'fit_to_page'),
                    custom_scale_percent=safe_float(params.get('custom_scale_percent', 100.0)),
                    custom_page_w=p_width,
                    custom_page_h=p_height,
                    fit_to_artwork=params.get('fit_artwork', False),
                    lpi=int(params.get('lpi', 45)),
                    mesh_count=int(mesh_count)
                )
                
                job_name = Path(args.input).stem
                add_vector_marks_to_page(c, page_w, page_h, margin_pt, color_rgb, color_name, {'job_name': job_name})
            c.save()
        else:
            from core.vector_exporter import export_vector_pdf
            # Determine page size string
            page_size_val = params.get('page_size', 'A4')
            if page_size_val.upper() == 'CUSTOM':
                page_size_val = f"{params.get('page_width', 210)}x{params.get('page_height', 297)}"

            if 'original_dimensions' in sep_res:
                setattr(args, 'original_dimensions', sep_res['original_dimensions'])
                logger.info(f"[Export] Original dimensions: {sep_res['original_dimensions']}")

            _progress(0.85, "Exporting PDF film...")

            export_vector_pdf(
                masks=masks, colors=sep_res['colors'], color_names=sep_res['color_names'],
                output_path=output_pdf, dpi=params.get('dpi', 300), mask_dpi=result.mask_dpi,
                smooth_factor=safe_float(params.get('smoothing_factor', 0.25)),
                corner_threshold=safe_float(params.get('corner_threshold', 120.0)),
                min_contour_area=params.get('contour_min_area', 50),
                image_class=result.image_class, page_size=page_size_val,
                epsilon=safe_float(params.get('simplification_epsilon', 1.2)),
                job_name=Path(args.input).stem, is_halftone=params.get('halftone', False),
                args=args,
                lpi=int(params.get('lpi', 45)),
                mesh_count=int(mesh_count),
                angle=45.0
            )

        # Previews - save mask directly (ink=0 black, background=255 white)
        for i, (mask, color_name) in enumerate(zip(masks, sep_res['color_names'])):
            display_idx = (reprocess_layer + 1) if reprocess_layer >= 0 else (i + 1)
            # CRITICAL FIX: If reprocessing, remove old file for this index to avoid name mismatch (e.g. Black vs Gold)
            if reprocess_layer >= 0:
                for existing_file in output_dir.glob(f"film_{display_idx}_*.png"):
                    try: os.remove(existing_file)
                    except: pass
            
            cv2.imwrite(str(output_dir / f"film_{display_idx}_{color_name.replace(' ', '_')}.png"), mask)

        # 5. Write metadata (ONLY for full runs, skip if reprocessing single layer)
        if reprocess_layer < 0:
            color_info_path = Path(args.output) / 'color_info.json'
            color_data = []
            for name, rgb in zip(sep_res['color_names'], sep_res['colors']):
                hex_str = f"#{int(rgb[0]):02x}{int(rgb[1]):02x}{int(rgb[2]):02x}"
                color_data.append({
                    'name': name,
                    'hex': hex_str,
                    'percentage': 0.0
                })
            with open(color_info_path, 'w', encoding='utf-8') as f:
                json.dump({'colors': color_data}, f)
        else:
            logger.info(f"[Main] Reprocess mode: Skipping color_info.json update to preserve other layers.")

        _progress(1.0, "Complete")
        if getattr(args, 'json_output', False):
            json_response = {
                'status': 'success', 
                'total_films': len(masks), 
                'film_names': sep_res['color_names']
            }
            print(f"\nRESULTS_JSON:{json.dumps(json_response)}", flush=True)

    except Exception as e:
        logger.error(f"Export failed: {e}", exc_info=True)
        return 1
    
    # 5. SINGLE LAYER REPROCESS CLEANUP
    # If we are only reprocessing one layer, we exit here to avoid overwriting color_info.json
    # or the global PDF, which would make other layers "disappear" from the UI.
    if reprocess_layer >= 0:
        logger.info(f"[Main] Single layer {reprocess_layer} reprocessed successfully. Skipping global metadata update.")
        _progress(1.0, "Layer reprocessed")
        _output_dir_signal(str(output_dir))
        return 0

    try:
        from core.mobile_hints import cleanup_mobile_mask
        cleanup_mobile_mask(getattr(args, 'pre_mask', None))
    except:
        pass

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
    parser.add_argument("--smoothing-factor", type=float, default=0.25)
    parser.add_argument("--use-underbase", action="store_true")
    parser.add_argument("--choke-px", type=int, default=2)
    parser.add_argument("--trapping-px", type=int, default=1)
    parser.add_argument("--page-size", default="A4")
    parser.add_argument("--page-width", type=float, default=0)
    parser.add_argument("--page-height", type=float, default=0)
    parser.add_argument("--fit-artwork", action="store_true")
    parser.add_argument("--margin-pt", type=float, default=28.35)  # ~10mm default
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
    parser.add_argument("--dot-sizes", type=str, default=None, help="Comma-separated dot size multipliers per layer")
    parser.add_argument("--dot-size", type=float, default=1.0, help="Global dot size multiplier")
    parser.add_argument("--image-class-hint", choices=["photo", "artwork", "text_logo", "mixed", "auto"], default="auto")
    parser.add_argument("--ai-confidence", type=float, default=0.0)
    parser.add_argument("--pre-mask", type=str, default=None)
    parser.add_argument("--no-ai", action="store_true")
    parser.add_argument("--upscale-factor", type=float, default=1.0)
    parser.add_argument("--denoise-strength", type=int, default=3)
    parser.add_argument("--contour-min-area", type=int, default=50)
    parser.add_argument("--simplification-epsilon", type=float, default=1.2)
    parser.add_argument("--ai-autofix", action="store_true")
    parser.add_argument("--reprocess-layer", type=int, default=-1, help="Index of a single layer to re-process")

    # Scaling & Physical Source Integrity (Phase 2 Upgrade)
    parser.add_argument("--target-width-mm", type=float, default=0.0, help="Explicit target width in mm")
    parser.add_argument("--source-dpi", type=int, default=-1, help="Original artwork DPI (overrides metadata)")
    parser.add_argument("--scale-mode", choices=["fit_to_page", "actual_size", "specific_width", "custom_scale"], default="fit_to_page")
    parser.add_argument("--custom-scale-percent", type=float, default=100.0)

    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    sys.exit(run_pipeline(args))
