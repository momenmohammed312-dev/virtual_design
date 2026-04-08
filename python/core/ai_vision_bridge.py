"""
ai_vision_bridge.py — Qwen3-VL Local Model Integration
Virtual Design Silk Screen Studio

ربط الموديل المحلي Qwen3-VL-2B بالـ pipeline بدل SmartAnalyzer.
الموديل بيشوف الصورة مباشرة ويرجع parameters جاهزة للـ PipelineRouter.

Requirements:
    pip install llama-cpp-python

Model files (set paths in MODEL_PATH / MMPROJ_PATH below):
    - Qwen3-VL-2B-Instruct-UD-Q4_K_XL 2.gguf  (~1.13 GB)
    - mmproj-F16 2.gguf                          (~819 MB)
"""

from __future__ import annotations
import base64
import contextlib
import json
import logging
import os
import time
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ─── AI Optimization Settings ────────────────────────────────────────────────
AI_MAX_DIM = 512  # Resize images to max 512px before AI analysis for speed


def _resize_for_ai(image: np.ndarray, max_dim: int = AI_MAX_DIM) -> np.ndarray:
    """Resize image for AI analysis while preserving aspect ratio.
    
    Args:
        image: Input image (BGR or RGB)
        max_dim: Maximum dimension (width or height)
        
    Returns:
        Resized image
    """
    h, w = image.shape[:2]
    if max(h, w) <= max_dim:
        return image
    
    # Calculate new size preserving aspect ratio
    scale = max_dim / max(h, w)
    new_w = int(w * scale)
    new_h = int(h * scale)
    
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    logger.info(f"[AIBridge] Resized image for AI: {w}x{h} -> {new_w}x{new_h} (scale: {scale:.2f})")
    return resized


# ─── Model Paths (عدّل على حسب مكان الملفات عندك) ────────────────────────────
MODEL_PATH  = r"E:\ai models\Qwen3-VL-2B\Qwen3-VL-2B-Instruct-UD-Q4_K_XL 2.gguf"
MMPROJ_PATH = r"E:\ai models\Qwen3-VL-2B\mmproj-F16 2.gguf"

# ─── Singleton ────────────────────────────────────────────────────────────────
_llm = None

def _get_llm():
    """Load model once, reuse across all calls (Singleton pattern)."""
    global _llm
    if _llm is not None:
        return _llm

    try:
        from llama_cpp import Llama
    except ImportError:
        logger.error("[AIBridge] llama-cpp-python not installed. Run: pip install llama-cpp-python")
        return None

    if not os.path.exists(MODEL_PATH):
        logger.error(f"[AIBridge] Model not found: {MODEL_PATH}")
        return None

    if not os.path.exists(MMPROJ_PATH):
        logger.error(f"[AIBridge] mmproj not found: {MMPROJ_PATH}")
        return None

    logger.info("[AIBridge] Loading Qwen3-VL-2B model (first call only)...")
    t0 = time.time()

    # Suppress llama.cpp warnings on stderr (Flutter treats them as errors)
    with open(os.devnull, 'w') as devnull:
        with contextlib.redirect_stderr(devnull):
            _llm = Llama(
                model_path  = MODEL_PATH,
                mmproj      = MMPROJ_PATH,
                n_ctx       = 4096,      # زيادة للتحسين والاستقرار
                n_threads   = 4,         # HP ProBook — 4 threads كافية
                n_gpu_layers= 0,         # CPU only
                verbose     = False,     # إسكات الـ Logs عشان Flutter ما يتهوش
            )

    logger.info(f"[AIBridge] Model loaded in {time.time()-t0:.1f}s")
    return _llm


# ─── Prompt ───────────────────────────────────────────────────────────────────
# Prompt template with OpenCV color context placeholder
_PROMPT_TEMPLATE = """/no_think
You are an autonomous Prepress Engineer for Silk Screen Printing.
Analyze the image and the provided OpenCV Color Data. Return STRICT JSON ONLY. No markdown, no explanation.

OPENCV COLOR DATA DETECTED:
{opencv_colors_context}

CLASSIFICATION RULES:
- text_logo: pure text or simple logo, flat colors, sharp edges, no gradients
- artwork: illustration with multiple flat colors, vector-like, limited gradients
- photo: photographic content, gradients, complex tones, continuous tone

COLOR SEPARATION RULES (HYBRID):
1. Review the OpenCV detected colors above.
2. Determine the TRUE number of printable ink colors needed (num_colors).
3. If two colors are very similar (brightness diff < 30), count them as 1 color (merge).
4. Ignore background colors (white/light with high brightness > 200).
5. Consider coverage % - colors under 2% may be noise.

PARAMETER RULES:
1. Edge quality:
   - Sharp clean edges -> smoothing_factor: 0.1-0.2, corner_threshold: 100-140
   - Jagged/pixelated -> smoothing_factor: 0.35-0.5, corner_threshold: 60-90
   - Moderate -> smoothing_factor: 0.2-0.35, corner_threshold: 80-110

2. Detail level (CRITICAL for text_logo - preserve sharp corners):
   - Fine text/small details -> contour_min_area: 8-20, simplification_epsilon: 0.3-0.6
   - text_logo (any) -> simplification_epsilon: 0.3-0.8 (LOW to preserve letter corners)
   - Normal artwork -> contour_min_area: 30-60, simplification_epsilon: 1.0-1.5
   - Bold/thick shapes -> contour_min_area: 60-150, simplification_epsilon: 1.5-2.5

3. Image resolution:
   - Low-res or small image -> upscale_factor: 2.0-4.0
   - Normal resolution -> upscale_factor: 1.0-1.5
   - High-res already -> upscale_factor: 1.0

4. Noise:
   - Clean image -> denoise_strength: 0
   - Slight noise -> denoise_strength: 3-5
   - Heavy noise/scan artifacts -> denoise_strength: 7-12

5. Halftone (photo only):
   - Fine detail photo -> lpi: 55-65, dot_shape: "round"
   - Normal photo -> lpi: 45-55, dot_shape: "round"
   - Textured/artistic -> lpi: 35-45, dot_shape: "ellipse"

HARD CONSTRAINTS:
- photo -> use_halftone: true, num_colors: 1
- text_logo -> num_colors <= 4 (can have multiple colors)
- artwork with gradients -> use_halftone: true
- artwork flat colors -> use_halftone: false

RESPONSE (JSON ONLY, nothing else):
{
  "image_class": "text_logo" | "artwork" | "photo",
  "num_colors": 1-8,
  "use_halftone": true | false,
  "smoothing_factor": 0.1-0.5,
  "corner_threshold": 30-140,
  "lpi": 35-85,
  "dot_shape": "round" | "ellipse" | "line" | "square",
  "upscale_factor": 1.0-4.0,
  "denoise_strength": 0-12,
  "contour_min_area": 8-150,
  "simplification_epsilon": 0.5-2.5,
  "color_merge_advice": "optional: which colors to merge",
  "auto_adjustment_reason": "one line reason"
}"""

# Default prompt without OpenCV data (fallback)
_PROMPT = _PROMPT_TEMPLATE.replace("{opencv_colors_context}", "No prior OpenCV data. Analyze visually.")


# ─── Caching ──────────────────────────────────────────────────────────────────
_analysis_cache = {}

def _get_image_hash(image: np.ndarray) -> str:
    """Generate a simple hash for the image to avoid redundant AI calls."""
    # Use a small downsampled version for hashing speed
    small = cv2.resize(image, (64, 64), interpolation=cv2.INTER_AREA)
    return str(hash(small.tobytes()))

# ─── Main API ─────────────────────────────────────────────────────────────────

def analyze_image(image: np.ndarray, opencv_colors: list = None) -> Optional[dict]:
    """
    Analyze a BGR numpy image using Qwen3-VL local model with caching.
    
    Args:
        image: BGR numpy array
        opencv_colors: Optional list of dicts from ColorSeparator.extract_dominant_colors_for_ai()
                      Each dict has: hex, rgb, coverage, brightness
    """
    img_hash = _get_image_hash(image)
    cache_key = (img_hash, tuple(c['hex'] for c in opencv_colors) if opencv_colors else "no_colors")
    if cache_key in _analysis_cache:
        logger.info("[AIBridge] Using cached analysis result")
        return _analysis_cache[cache_key]

    llm = _get_llm()
    if llm is None:
        # FALLBACK: Robust default parameters if model fails to load
        return _get_safe_fallback()

    # 🔥 CRITICAL FIX: Resize for AI speed optimization (67s → 5-15s)
    h, w = image.shape[:2]
    logger.info(f"[AIBridge] AI Input Shape BEFORE resize: {w}x{h}")
    
    max_dim = 512  # Increased from 448 for better quality/speed balance
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        new_w, new_h = int(w * scale), int(h * scale)
        image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        logger.info(f"[AIBridge] ✓ Resized for AI: {w}x{h} → {new_w}x{new_h} (scale: {scale:.3f})")
    else:
        logger.info(f"[AIBridge] No resize needed (already {max(h,w)} ≤ {max_dim})")
    
    # 🔥 Verify final shape
    final_h, final_w = image.shape[:2]
    logger.info(f"[AIBridge] AI Input Shape AFTER resize: {final_w}x{final_h}")

    # Encode to JPEG base64
    _, buf = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 85])
    img_b64 = base64.b64encode(buf).decode()
    logger.info(f"[AIBridge] Base64 encoded size: {len(img_b64)} chars")

    # Build prompt with OpenCV color context
    if opencv_colors:
        color_lines = []
        for i, c in enumerate(opencv_colors[:8]):
            color_lines.append(
                f"  {i+1}. {c['hex']} (RGB:{c['rgb']}) - {c['coverage']:.1f}% coverage, brightness={c['brightness']:.0f}"
            )
        opencv_context = "OpenCV K-Means detected these dominant colors:\n" + "\n".join(color_lines)
        prompt = _PROMPT_TEMPLATE.replace("{opencv_colors_context}", opencv_context)
        logger.info(f"[AIBridge] Using hybrid mode with {len(opencv_colors)} OpenCV colors")
    else:
        prompt = _PROMPT
        logger.info("[AIBridge] Using visual-only mode (no OpenCV data)")

    logger.info("[AIBridge] Sending image to Qwen3-VL...")
    t0 = time.time()

    try:
        response = llm.create_chat_completion(
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                    {"type": "text", "text": prompt}
                ]
            }],
            temperature = 0.1,
            max_tokens  = 250,
        )
    except Exception as e:
        logger.error(f"[AIBridge] Inference failed: {e}")
        return _get_safe_fallback()

    elapsed = time.time() - t0
    raw = response["choices"][0]["message"]["content"]
    logger.info(f"[AIBridge] Response in {elapsed:.1f}s")

    result = _parse_response(raw) or _get_safe_fallback()
    
    # Adjust parameters based on original image resolution
    if result:
        result = _adjust_for_resolution(result, h, w)
    
    _analysis_cache[cache_key] = result
    return result

def _get_safe_fallback() -> dict:
    """Safe default parameters if AI fails."""
    logger.warning("[AIBridge] Using safe fallback parameters")
    return {
        "image_class":            "artwork",
        "num_colors":             3,
        "use_halftone":           False,
        "smoothing_factor":       0.25,
        "corner_threshold":       95.0,
        "lpi":                    55,
        "dot_shape":              "round",
        "upscale_factor":         1.0,
        "denoise_strength":       3,
        "contour_min_area":       50,
        "simplification_epsilon": 1.2,
    }


def _adjust_for_resolution(result: dict, h: int, w: int) -> dict:
    """Correct AI params when image is low-res (will be upscaled heavily)."""
    max_dim = max(h, w)
    
    # Low-res images need more aggressive cleaning
    if max_dim < 500:
        # More smoothing to hide upscale artifacts
        result["smoothing_factor"] = max(result["smoothing_factor"], 0.3)
        # Bigger min area to filter noise
        result["contour_min_area"] = max(result.get("contour_min_area", 50), 80)
        # Bigger epsilon to simplify jagged edges
        result["simplification_epsilon"] = max(
            result.get("simplification_epsilon", 1.2), 1.5
        )
        logger.info(
            f"[AIBridge] Low-res image ({max_dim}px) — "
            f"boosted: smooth={result['smoothing_factor']:.2f} "
            f"min_area={result['contour_min_area']} "
            f"epsilon={result['simplification_epsilon']:.1f}"
        )
    elif max_dim < 1000:
        result["smoothing_factor"] = max(result["smoothing_factor"], 0.2)
        result["contour_min_area"] = max(result.get("contour_min_area", 50), 40)
        result["simplification_epsilon"] = max(
            result.get("simplification_epsilon", 1.2), 1.0
        )
    
    return result


def _sanitize_numeric_ranges(json_str: str) -> str:
    """Convert numeric ranges like '0.35-0.5' to single values before JSON parsing."""
    import re
    # Pattern to match numeric ranges: number-number (with optional decimals)
    # Examples: 0.35-0.5, 10-20, 0.1-0.3
    range_pattern = r'"(\d+\.?\d*)-(\d+\.?\d*)"'
    
    def replace_range(match):
        val1, val2 = float(match.group(1)), float(match.group(2))
        # Use midpoint of range
        midpoint = (val1 + val2) / 2
        # Preserve original decimal precision
        if '.' in match.group(1) or '.' in match.group(2):
            return f'"{midpoint:.2f}"'
        else:
            return f'"{int(midpoint)}"'
    
    sanitized = re.sub(range_pattern, replace_range, json_str)
    return sanitized


def _parse_response(raw: str) -> Optional[dict]:
    """Parse and validate JSON response from model."""
    # Strip markdown code blocks if model added them
    clean = raw.strip()
    if clean.startswith("```"):
        lines = clean.split("\n")
        clean = "\n".join(lines[1:-1]) if len(lines) > 2 else clean

    # Strip <think>...</think> if thinking mode leaked
    if "<think>" in clean:
        import re
        clean = re.sub(r"<think>.*?</think>", "", clean, flags=re.DOTALL).strip()

    # 🔥 FIX: Sanitize numeric ranges before JSON parsing
    clean = _sanitize_numeric_ranges(clean)

    try:
        result = json.loads(clean)
    except json.JSONDecodeError as e:
        logger.warning(f"[AIBridge] JSON parse failed: {e} | raw: {raw[:200]}")
        return None

    # 🔥 FIX: Apply defaults for missing keys instead of failing
    defaults = {
        "image_class": "artwork",
        "num_colors": 3,
        "use_halftone": False,
        "smoothing_factor": 0.25,
        "corner_threshold": 95.0,
        "lpi": 55,
        "dot_shape": "round",
        "upscale_factor": 1.0,
    }
    for key, default_val in defaults.items():
        if key not in result:
            logger.warning(f"[AIBridge] Missing key: {key}, using default: {default_val}")
            result[key] = default_val
        else:
            # Coerce type if possible
            try:
                if isinstance(default_val, bool):
                    result[key] = bool(result[key])
                elif isinstance(default_val, int):
                    result[key] = int(float(result[key]))
                elif isinstance(default_val, float):
                    result[key] = float(result[key])
                elif isinstance(default_val, str):
                    result[key] = str(result[key])
            except (ValueError, TypeError):
                logger.warning(f"[AIBridge] Invalid type for {key}: {result[key]}, using default: {default_val}")
                result[key] = default_val

    # Validate image_class
    valid_classes = {"text_logo", "artwork", "photo"}
    if result["image_class"] not in valid_classes:
        logger.warning(f"[AIBridge] Unknown image_class: {result['image_class']}, defaulting to artwork")
        result["image_class"] = "artwork"

    # Clamp numeric values to safe ranges
    result["num_colors"]      = max(1, min(8, result["num_colors"]))
    result["smoothing_factor"]= max(0.1, min(0.5, result["smoothing_factor"]))
    result["corner_threshold"]= float(max(30, min(140, result.get("corner_threshold", 95.0))))
    result["lpi"]             = int(max(45, min(85, result.get("lpi", 55))))

    # Enforce constraints
    if result["image_class"] == "photo":
        result["use_halftone"] = True
        result["num_colors"]   = 1
    elif result["image_class"] == "text_logo":
        # Suggest non-halftone for text logos, but don't force it
        # (user's UI selection takes precedence - enforced in apply_to_args)
        result["num_colors"] = min(result["num_colors"], 4)
        # Only set use_halftone=False if AI didn't already analyze it
        if "use_halftone" not in result:
            result["use_halftone"] = False
        # CRITICAL: Lower epsilon for text logos to preserve sharp letter corners
        result["simplification_epsilon"] = min(
            result.get("simplification_epsilon", 0.8), 0.8
        )
        result["smoothing_factor"] = min(
            result.get("smoothing_factor", 0.2), 0.25
        )

    logger.info(f"[AIBridge] Parsed: {result}")
    return result


# ─── Pipeline Router Integration ──────────────────────────────────────────────

def apply_to_args(ai_result: dict, args) -> None:
    """
    Apply AI analysis results to pipeline args in-place.
    الموديل هنا هو اللي بيحدد الأرقام والـ Pipeline بينفذ فوراً

    Args:
        ai_result: dict from analyze_image()
        args: argparse.Namespace from pipeline
    """
    if ai_result is None:
        return

    # Core parameters
    # Only override color count in auto mode (user selected 0 = auto-detect)
    if getattr(args, 'colors', 0) == 0:
        args.colors = ai_result["num_colors"]
    # else: user chose a specific color count -> keep their selection
    # Respect user's explicit halftone choice - AI can only suggest, not override
    user_requested_halftone = getattr(args, 'halftone', False)
    if not user_requested_halftone:
        # User didn't explicitly request halftone -> follow AI suggestion
        args.halftone = ai_result["use_halftone"]
    # else: user chose halftone explicitly -> keep args.halftone = True
    args.smoothing_factor = ai_result["smoothing_factor"]
    args.image_type       = ai_result["image_class"]

    # Standard optional params
    if hasattr(args, 'corner_threshold'):
        args.corner_threshold = ai_result.get("corner_threshold", 95.0)
    if hasattr(args, 'lpi'):
        args.lpi = ai_result.get("lpi", 55)

    # Extended AI Vision params
    if hasattr(args, 'dot_shape'):
        args.dot_shape = ai_result.get("dot_shape", "round")
    if hasattr(args, 'upscale_factor'):
        args.upscale_factor = float(ai_result.get("upscale_factor", 1.0))
    if hasattr(args, 'denoise_strength'):
        args.denoise_strength = int(ai_result.get("denoise_strength", 3))
    if hasattr(args, 'contour_min_area'):
        args.contour_min_area = int(ai_result.get("contour_min_area", 50))
    if hasattr(args, 'simplification_epsilon'):
        args.simplification_epsilon = float(ai_result.get("simplification_epsilon", 1.2))

    # Log the reason for the decision
    reason = ai_result.get("auto_adjustment_reason", "No reason provided")
    logger.info(f"[AI-Autopilot] {reason}")
    logger.info(
        f"[AIBridge] Applied: class={args.image_type} colors={args.colors} "
        f"halftone={args.halftone} smooth={args.smoothing_factor:.2f} "
        f"dot={getattr(args,'dot_shape','?')} upscale={getattr(args,'upscale_factor',1.0):.1f} "
        f"denoise={getattr(args,'denoise_strength',3)} "
        f"min_area={getattr(args,'contour_min_area',50)} "
        f"epsilon={getattr(args,'simplification_epsilon',1.2):.1f}"
    )


def analyze_preview_flaws(original_img_path: str, preview_img_path: str) -> Optional[dict]:
    """
    Analyze preview flaws and suggest parameter adjustments.
    
    Compares original image with generated preview to identify:
    - Jagged edges (need more smoothing)
    - Lost details (need lower epsilon)
    - Poor halftone density (need LPI adjustment)
    
    Returns adjusted parameters or None if analysis fails.
    """
    llm = _get_llm()
    if llm is None:
        logger.warning("[AIBridge] Auto-Fix: Model not available")
        return None

    # 🔥 FIX: Resize images before AI analysis for speed (67s -> 5-15s)
    try:
        orig_img = cv2.imread(original_img_path)
        prev_img = cv2.imread(preview_img_path)
        
        if orig_img is None or prev_img is None:
            logger.error("[AIBridge] Auto-Fix: Failed to load images")
            return None
        
        # Resize for AI speed optimization
        orig_resized = _resize_for_ai(orig_img, max_dim=768)
        prev_resized = _resize_for_ai(prev_img, max_dim=768)
        
        # Encode resized images
        _, orig_buf = cv2.imencode('.png', orig_resized)
        _, prev_buf = cv2.imencode('.png', prev_resized)
        
        orig_b64 = base64.b64encode(orig_buf).decode()
        prev_b64 = base64.b64encode(prev_buf).decode()
        
        logger.info(f"[AIBridge] Auto-Fix: Images resized and encoded for AI")
    except Exception as e:
        logger.error(f"[AIBridge] Auto-Fix: Failed to process images: {e}")
        return None

    fix_prompt = """/no_think
Compare the ORIGINAL image with the generated PRINT PREVIEW.
Identify flaws in the preview:
- Jagged/staircase edges (need higher smoothing_factor)
- Lost fine details (need lower simplification_epsilon)
- Blurred text/corners (need lower smoothing_factor)
- Poor halftone dot quality (need different LPI)

Return STRICT JSON with corrected values:
{
  "smoothing_factor": 0.1-0.5,
  "corner_threshold": 30-140,
  "simplification_epsilon": 0.3-2.5,
  "lpi": 35-85,
  "adjustment_reason": "Brief description of what was fixed"
}

If preview looks good, return minimal adjustments.
"""

    logger.info("[AIBridge] Auto-Fix: Analyzing preview vs original...")

    try:
        response = llm.create_chat_completion(
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "ORIGINAL IMAGE:"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{orig_b64}"}},
                    {"type": "text", "text": "CURRENT PREVIEW (Result):"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{prev_b64}"}},
                    {"type": "text", "text": fix_prompt}
                ]
            }],
            temperature=0.1,
            max_tokens=200,
        )

        raw = response["choices"][0]["message"]["content"]
        result = _parse_response(raw)

        if result:
            logger.info(f"[AIBridge] Auto-Fix: {result.get('adjustment_reason', 'No reason')}")
            # Remove non-parameter keys
            return {
                'smoothing_factor': result.get('smoothing_factor', 0.25),
                'corner_threshold': result.get('corner_threshold', 95.0),
                'simplification_epsilon': result.get('simplification_epsilon', 1.2),
                'lpi': result.get('lpi', 55),
                'adjustment_reason': result.get('adjustment_reason', ''),
            }
        return None

    except Exception as e:
        logger.error(f"[AIBridge] Auto-Fix failed: {e}")
        return None


def analyze_with_prompt(original_path: str, preview_path: str, user_prompt: str) -> Optional[dict]:
    """
    Task 5.2 FIX: Analyze preview with user-provided prompt for custom adjustments.
    
    This function allows users to describe what they want to adjust in the film,
    and the AI will suggest parameter changes based on that description.
    
    Args:
        original_path: Path to original input image
        preview_path: Path to current preview image (what user sees)
        user_prompt: User's description of desired adjustments
        
    Returns:
        Dict with parameter adjustments or None if failed
    """
    llm = _get_llm()
    if llm is None:
        logger.warning("[AIBridge] LLM not available for prompt-based analysis")
        return None
    
    # 🔥 FIX: Resize image before AI analysis for speed
    img = cv2.imread(preview_path)
    if img is None:
        logger.error(f"[AIBridge] Cannot load preview: {preview_path}")
        return None
    
    # Resize for AI speed optimization
    img_resized = _resize_for_ai(img, max_dim=768)
    
    # Encode resized image
    _, buf = cv2.imencode(".jpg", img_resized)
    img_b64 = base64.b64encode(buf).decode("utf-8")
    
    # Build prompt with user instructions
    prompt = f"""/no_think
You are a Prepress Engineer for Silk Screen Printing. 
The user wants to adjust their film based on this description:
"{user_prompt}"

Analyze the current preview image and suggest specific parameter adjustments.
Return STRICT JSON ONLY with these fields:
- smoothing_factor: float (0.1-0.5) - higher = smoother edges
- corner_threshold: float (30-140) - lower = sharper corners
- global_threshold: int (0-255) - adjust line thickness
- lpi: int (45-85) - lines per inch for halftone
- adjustment_reason: string - brief explanation of changes

Example: {{"smoothing_factor": 0.35, "corner_threshold": 95, "global_threshold": 180, "lpi": 55, "adjustment_reason": "Increased smoothing to reduce jagged edges"}}
"""
    
    logger.info(f"[AIBridge] Analyzing with user prompt: {user_prompt[:50]}...")
    t0 = time.time()
    
    try:
        response = llm.create_chat_completion(
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                    {"type": "text", "text": prompt}
                ]
            }],
            temperature=0.2,
            max_tokens=250,
        )
        
        elapsed = time.time() - t0
        raw = response["choices"][0]["message"]["content"]
        logger.info(f"[AIBridge] Prompt response in {elapsed:.1f}s")
        
        result = _parse_response(raw)
        
        if result:
            logger.info(f"[AIBridge] Prompt-based adjustments applied: {result.get('adjustment_reason', '')}")
            return {
                'smoothing_factor': result.get('smoothing_factor', 0.25),
                'corner_threshold': result.get('corner_threshold', 95.0),
                'global_threshold': result.get('global_threshold', 180),
                'lpi': result.get('lpi', 55),
                'adjustment_reason': result.get('adjustment_reason', 'Custom adjustments applied'),
            }
        return None
        
    except Exception as e:
        logger.error(f"[AIBridge] Prompt analysis failed: {e}")
        return None


# ─── Health Check ─────────────────────────────────────────────────────────────

def is_available() -> bool:
    """Check if model files exist and llama-cpp is installed."""
    try:
        import llama_cpp  # noqa: F401
    except ImportError:
        return False
    return os.path.exists(MODEL_PATH) and os.path.exists(MMPROJ_PATH)
