"""
api_server.py — FastAPI wrapper around the existing silk-screen pipeline.

Start with:
    python api_server.py
or  uvicorn api_server:app --host 0.0.0.0 --port 8000 --workers 1

All heavy processing is delegated to main.run_pipeline() — nothing in
main.py is changed.
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from starlette.background import BackgroundTask

import uvicorn

# ── make the python/ directory importable ──────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("api_server")

app = FastAPI(
    title="Virtual Designer API",
    version="1.0.0",
    description="Silk-screen film generation API backed by the full Qwen + OpenCV pipeline.",
)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _check_qwen() -> bool:
    """Return True if the Qwen model file is present on disk."""
    try:
        from core.ai_vision_bridge import _MODEL_PATH  # type: ignore
        return bool(_MODEL_PATH and os.path.exists(_MODEL_PATH))
    except Exception:
        return False


def _delete_file(path: str) -> None:
    """Background cleanup callback."""
    try:
        os.unlink(path)
    except OSError:
        pass


def _build_args(
    img_path: str,
    output_dir: str,
    mask_path: str | None,
    **kw,
) -> argparse.Namespace:
    """Construct an argparse.Namespace that mirrors what parse_args() returns."""
    return argparse.Namespace(
        input=img_path,
        output=output_dir,
        colors=kw.get("colors", 0),
        dpi=kw.get("dpi", 300),
        halftone=kw.get("halftone", False),
        lpi=kw.get("lpi", 65),
        dot_shape=kw.get("dot_shape", "round"),
        dot_size=kw.get("dot_size", 1.0),
        dot_sizes=None,
        mesh_count=kw.get("mesh_count", 110),
        # main.py expects page sizes in mm via --page-width / --page-height
        page_width=kw.get("page_width", 0.0),
        page_height=kw.get("page_height", 0.0),
        detail_level=kw.get("detail_level", "medium"),
        image_class_hint=kw.get("image_class_hint", "auto"),
        ai_confidence=kw.get("ai_confidence", 0.0),
        pre_mask=mask_path,
        no_ai=kw.get("no_ai", False),
        reprocess_layer=kw.get("reprocess_layer", -1),
        smoothing_factor=-1.0,
        corner_threshold=-1.0,
        noise_removal=3,
        force_halftone=False,
        adaptive_threshold=False,
        film_label="",
        json_output=True,
        # Scaling / physical
        target_width_mm=kw.get("target_width_mm", 0.0),
        source_dpi=kw.get("source_dpi", 300),
        scale_mode=kw.get("scale_mode", "fit_to_page"),
        custom_scale_percent=kw.get("custom_scale_percent", 100.0),
        # Advanced (match parse_args defaults)
        image_type="auto",
        use_underbase=False,
        choke_px=2,
        trapping_px=1,
        page_size="A4",
        fit_artwork=False,
        margin_pt=28.35,
        clean=False,
        validate_strokes=False,
        min_stroke=0.5,
        pantone_matching="automatic",
        underbase_mode="disabled",
        trapping_mode="automatic",
        overprint_mode="automatic",
        gradient_mesh_mode="automatic",
        typography_mode="automatic",
        mesh_preview_mode="automatic",
        global_threshold=200,
        auto_colors=False,
        upscale_factor=1.0,
        denoise_strength=3,
        contour_min_area=50,
        simplification_epsilon=1.2,
        ai_autofix=False,
        smoothing_slider=-1,
    )


def _collect_results(output_dir: str, stem: str) -> str:
    """Pack PNG films + PDF + decision_trace into a ZIP and return its path."""
    zip_fd, zip_path = tempfile.mkstemp(suffix=".zip")
    os.close(zip_fd)

    out = Path(output_dir)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for pattern in ("*.png", "*.pdf"):
            for f in out.glob(pattern):
                zf.write(f, f.name)
        trace = out / "decision_trace.json"
        if trace.exists():
            zf.write(trace, "decision_trace.json")
        color_info = out / "color_info.json"
        if color_info.exists():
            zf.write(color_info, "color_info.json")

    return zip_path


# ──────────────────────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/health", summary="Server health & Qwen availability")
async def health():
    """
    Ping endpoint — the Flutter app polls this every 30 s to decide whether to
    route to the server or fall back to local AI.
    """
    return {"status": "ok", "qwen_available": _check_qwen()}


@app.post("/process", summary="Full pipeline: upload image → get ZIP of films")
async def process_image(
    file: UploadFile = File(...),
    colors: int = Form(0),
    dpi: int = Form(300),
    halftone: bool = Form(False),
    lpi: int = Form(65),
    dot_shape: str = Form("round"),
    dot_size: float = Form(1.0),
    mesh_count: int = Form(110),
    paper_width: float = Form(21.0),
    paper_height: float = Form(29.7),
    detail_level: str = Form("medium"),
    # Mobile-AI hints (optional) ─────────────────────────────────────────────
    image_class_hint: str = Form("auto"),
    ai_confidence: float = Form(0.0),
    no_ai: bool = Form(False),
    pre_mask_b64: str = Form(""),   # base64-encoded PNG from DeepLabV3
    # Scaling & physical sizing
    target_width_mm: float = Form(0.0),
    source_dpi: int = Form(300),
    scale_mode: str = Form("fit_to_page"),
    custom_scale_percent: float = Form(100.0),
):
    """
    Main processing endpoint.

    Accepts the image + optional TFLite hints from the phone, runs the full
    Qwen + OpenCV pipeline on the PC, and returns a ZIP containing all film
    PNGs, the combined PDF, and the decision_trace.json.
    """
    suffix = Path(file.filename or "input.png").suffix or ".png"

    with tempfile.TemporaryDirectory() as tmpdir:
        # ── save uploaded image ──────────────────────────────────────────────
        img_path = os.path.join(tmpdir, f"input{suffix}")
        with open(img_path, "wb") as fh:
            shutil.copyfileobj(file.file, fh)

        # ── save mask if provided ────────────────────────────────────────────
        mask_path: str | None = None
        if pre_mask_b64:
            try:
                mask_bytes = base64.b64decode(pre_mask_b64)
                mask_path = os.path.join(tmpdir, "pre_mask.png")
                with open(mask_path, "wb") as fh:
                    fh.write(mask_bytes)
            except Exception as exc:
                logger.warning("Could not decode pre_mask_b64: %s", exc)

        output_dir = os.path.join(tmpdir, "output")
        os.makedirs(output_dir, exist_ok=True)

        # ── build args & run pipeline ────────────────────────────────────────
        args = _build_args(
            img_path=img_path,
            output_dir=output_dir,
            mask_path=mask_path,
            colors=colors,
            dpi=dpi,
            halftone=halftone,
            lpi=lpi,
            dot_shape=dot_shape,
            dot_size=dot_size,
            mesh_count=mesh_count,
            page_width=float(paper_width) * 10.0 if paper_width else 0.0,
            page_height=float(paper_height) * 10.0 if paper_height else 0.0,
            detail_level=detail_level,
            image_class_hint=image_class_hint,
            ai_confidence=ai_confidence,
            no_ai=no_ai,
            target_width_mm=target_width_mm,
            source_dpi=source_dpi,
            scale_mode=scale_mode,
            custom_scale_percent=custom_scale_percent,
        )

        try:
            from main import run_pipeline  # type: ignore
            exit_code = run_pipeline(args)
        except Exception as exc:
            logger.error("Pipeline raised an exception: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=f"Pipeline error: {exc}")

        if exit_code != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Pipeline exited with code {exit_code}",
            )

        # ── collect output into ZIP (must happen before tmpdir cleanup) ──────
        stem = Path(file.filename or "result").stem
        zip_path = _collect_results(output_dir, stem)

    # tmpdir is gone now — zip_path is in a separate tempfile location
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename="films.zip",
        background=BackgroundTask(_delete_file, zip_path),
    )


@app.post("/reprocess_layer", summary="Re-run a single layer as halftone")
async def reprocess_layer(
    file: UploadFile = File(...),
    layer_index: int = Form(0),
    dpi: int = Form(300),
    lpi: int = Form(65),
    dot_shape: str = Form("round"),
    dot_size: float = Form(1.0),
    mesh_count: int = Form(110),
):
    """
    Re-process a single colour layer as halftone without touching the others.
    Mirrors the --reprocess-layer flag in main.py.
    """
    suffix = Path(file.filename or "input.png").suffix or ".png"

    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = os.path.join(tmpdir, f"input{suffix}")
        with open(img_path, "wb") as fh:
            shutil.copyfileobj(file.file, fh)

        output_dir = os.path.join(tmpdir, "output")
        os.makedirs(output_dir, exist_ok=True)

        args = _build_args(
            img_path=img_path,
            output_dir=output_dir,
            mask_path=None,
            dpi=dpi,
            halftone=True,
            lpi=lpi,
            dot_shape=dot_shape,
            dot_size=dot_size,
            mesh_count=mesh_count,
            colors=1,
            reprocess_layer=layer_index,
        )

        try:
            from main import run_pipeline  # type: ignore
            exit_code = run_pipeline(args)
        except Exception as exc:
            logger.error("Reprocess pipeline error: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=f"Pipeline error: {exc}")

        if exit_code != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Reprocess pipeline exited with code {exit_code}",
            )

        zip_path = _collect_results(output_dir, "layer")

    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=f"layer_{layer_index}.zip",
        background=BackgroundTask(_delete_file, zip_path),
    )


# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, workers=1)
