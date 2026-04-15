"""
ai_vision_bridge.py — Qwen3-VL Local Model Integration
Virtual Design Silk Screen Studio

FIX GROUP: Robust AI AutoFix System with:
- Model auto-discovery from common paths
- Environment variable configuration
- Graceful fallback when model unavailable
- Caching and performance optimization

Requirements:
    pip install llama-cpp-python

Model files (auto-discovered from common paths or set via environment):
    - Qwen3-VL-2B-Instruct-UD-Q4_K_XL.gguf  (~1.13 GB)
    - mmproj-F16.gguf                        (~819 MB)

Environment Variables:
    QWEN_MODEL_PATH  - Path to main model .gguf file
    QWEN_MMPROJ_PATH - Path to mmproj .gguf file
    AI_DISABLED      - Set to "1" to disable AI and use rule-based analysis only
"""

from __future__ import annotations
import base64
import contextlib
import json
import logging
import os
import time
import glob
from pathlib import Path
from typing import Optional, Dict, Tuple
from dataclasses import dataclass

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ─── AI Optimization Settings ────────────────────────────────────────────────
AI_MAX_DIM = 512  # Resize images to max 512px before AI analysis for speed

# ═══ MODEL CONFIGURATION WITH AUTO-DISCOVERY ═══

def _find_model_files() -> Tuple[str, str]:
    """
    Auto-discover model files from common locations.
    
    Searches in order:
    1. Environment variables (QWEN_MODEL_PATH, QWEN_MMPROJ_PATH)
    2. Current working directory
    3. Models subdirectory
    4. User home directory /models
    5. System-wide /opt/models or C:\ProgramData\Models
    
    Returns:
        (model_path, mmproj_path) - may be empty strings if not found
    """
    # 1. Environment variables (highest priority)
    env_model = os.environ.get("QWEN_MODEL_PATH", "").strip()
    env_mmproj = os.environ.get("QWEN_MMPROJ_PATH", "").strip()
    
    if env_model and env_mmproj:
        if os.path.exists(env_model) and os.path.exists(env_mmproj):
            logger.info(f"[AIBridge] Using environment paths: {env_model}")
            return env_model, env_mmproj
        else:
            logger.warning(f"[AIBridge] Environment paths set but files don't exist")
    
    # --- FIXED PROJECT PATH DISCOVERY ---
    # Find the 'virtual_design' root folder regardless of CWD
    try:
        current_file = Path(__file__).resolve()
        # Look for the root (has .git or python or models)
        root_dir = current_file.parents[2] # core -> python -> root
        if not (root_dir / "models").exists() and (current_file.parents[3] / "models").exists():
            root_dir = current_file.parents[3]
    except Exception:
        root_dir = Path.cwd()

    # Search paths (in order of preference)
    search_dirs = [
        root_dir / "models",
        root_dir / "Models",
        Path.cwd() / "models",
        Path.cwd(),
        Path.home() / "models",
        Path.home() / "Downloads",
    ]
    
    # ─── LOGGING SEARCH PLAN ───
    logger.info(f"[AIBridge] Project Root: {root_dir}")
    logger.info(f"[AIBridge] Searching for Qwen-VL models in {len(search_dirs)} locations...")

    # Extended patterns to handle specific manual filenames
    model_patterns = ["*Qwen3*VL*.gguf", "*Qwen-VL*.gguf", "*vision*.gguf", "*.gguf"]
    mmproj_patterns = ["*mmproj*.gguf", "*vision*proj*.gguf"]
    
    found_model = None
    found_mmproj = None
    
    # Track checked paths for logging if nothing found
    checked_paths = []

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
            
        checked_paths.append(str(search_dir))
        
        # Search for model file (main weights)
        if not found_model:
            for pattern in model_patterns:
                try:
                    matches = list(search_dir.glob(pattern))
                    # Filter: ignore mmproj, must be > 500MB
                    matches = [m for m in matches if 'mmproj' not in m.name.lower() and m.stat().st_size > 500*1024*1024]
                    if matches:
                        # Sort by size to get the high-quant model if multiple exist
                        matches.sort(key=lambda x: x.stat().st_size, reverse=True)
                        found_model = matches[0]
                        logger.info(f"[AIBridge] √ FOUND MODEL PATH: {found_model.absolute()}")
                        break
                except Exception: continue

        # Search for mmproj
        if not found_mmproj:
            for pattern in mmproj_patterns:
                try:
                    matches = list(search_dir.glob(pattern))
                    if matches:
                        found_mmproj = matches[0]
                        logger.info(f"[AIBridge] √ FOUND MMPROJ PATH: {found_mmproj.absolute()}")
                        break
                except Exception: continue

        if found_model and found_mmproj:
            break
    
    if not (found_model and found_mmproj):
        logger.warning(f"[AIBridge] Vision models NOT found in check list: {checked_paths}")
        logger.info("[AIBridge] Suggestion: Run 'ren models\\*2.gguf *' to clean filenames if they have suffixes")
    
    return str(found_model) if found_model else "", str(found_mmproj) if found_mmproj else ""

# Auto-discover or use environment paths
_MODEL_PATH, _MMPROJ_PATH = _find_model_files()

# Make available as module-level constants
MODEL_PATH = os.environ.get("QWEN_MODEL_PATH", _MODEL_PATH)
MMPROJ_PATH = os.environ.get("QWEN_MMPROJ_PATH", _MMPROJ_PATH)

# Check if AI is explicitly disabled
AI_DISABLED = os.environ.get("AI_DISABLED", "").lower() in ("1", "true", "yes", "on")

# ─── AI Status Tracking ─────────────────────────────────
_ai_status = {
    'initialized': False,
    'available': False,
    'last_error': None,
    'model_path': MODEL_PATH,
    'mmproj_path': MMPROJ_PATH,
}

# ─── Singleton ─────────────────────────────────────────────
_llm = None

def get_ai_status() -> Dict:
    """Get current AI system status for diagnostics."""
    return _ai_status.copy()

def _get_llm():
    """
    Load model once, reuse across all calls (Singleton pattern).
    
    FIX GROUP: Robust model loading with comprehensive error handling.
    """
    global _llm, _ai_status
    
    if _llm is not None:
        return _llm
    
    # Check if AI is disabled
    if AI_DISABLED:
        logger.info("[AIBridge] AI is disabled via AI_DISABLED environment variable")
        _ai_status['available'] = False
        _ai_status['last_error'] = "AI_DISABLED"
        return None
    
    # Check if model files are available
    if not MODEL_PATH or not os.path.exists(MODEL_PATH):
        logger.warning(f"[AIBridge] Main weights not found. (Current path: '{MODEL_PATH}')")
        _ai_status['available'] = False
        _ai_status['last_error'] = "MODEL_NOT_FOUND"
        return None
    
    if not MMPROJ_PATH or not os.path.exists(MMPROJ_PATH):
        logger.warning(f"[AIBridge] MMProjector not found. (Current path: '{MMPROJ_PATH}')")
        _ai_status['available'] = False
        _ai_status['last_error'] = "MMPROJ_NOT_FOUND"
        return None
    
    try:
        from llama_cpp import Llama
    except ImportError:
        logger.warning("[AIBridge] llama-cpp-python not installed. Run: pip install llama-cpp-python")
        logger.info("[AIBridge] Using rule-based fallback analysis")
        _ai_status['available'] = False
        _ai_status['last_error'] = "LLAMA_CPP_NOT_INSTALLED"
        return None
    
    # Attempt model loading with retry logic
    max_retries = 1
    for attempt in range(max_retries + 1):
        try:
            logger.info(f"[AIBridge] Loading model (attempt {attempt + 1}/{max_retries + 1})...")
            logger.info(f"[AIBridge] Model: {os.path.basename(MODEL_PATH)}")
            logger.info(f"[AIBridge] MMProj: {os.path.basename(MMPROJ_PATH)}")
            
            t0 = time.time()
            
            # Capture stderr for debugging
            import io
            stderr_buffer = io.StringIO()
            
            # Hardware optimization for speed
            cpu_count = os.cpu_count() or 4
            target_threads = max(4, min(cpu_count - 1, 12)) # Use more threads but leave some for UI
            
            # Auto-detect GPU potential (conservative)
            # 32 layers is usually enough to fit the entire 2B model in 4GB-6GB VRAM
            gpu_layers = 33 if os.environ.get("USE_GPU", "1") == "1" else 0
            
            with contextlib.redirect_stderr(stderr_buffer):
                _llm = Llama(
                    model_path   = MODEL_PATH,
                    mmproj       = MMPROJ_PATH,
                    n_ctx        = 2048, # Reduced context for speed (enough for 1 image)
                    n_threads    = target_threads,
                    n_gpu_layers = gpu_layers, 
                    verbose      = False,
                )
            
            # Check for warnings
            stderr_content = stderr_buffer.getvalue()
            if stderr_content:
                logger.debug(f"[AIBridge] Model load messages: {stderr_content[:500]}")
            
            load_time = time.time() - t0
            logger.info(f"[AIBridge] Model loaded successfully in {load_time:.1f}s")
            
            _ai_status['available'] = True
            _ai_status['initialized'] = True
            _ai_status['last_error'] = None
            
            return _llm
            
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"[AIBridge] Model load failed: {error_msg}")
            _ai_status['last_error'] = error_msg
            
            if attempt < max_retries:
                logger.info("[AIBridge] Retrying...")
                time.sleep(0.5)
            else:
                logger.error("[AIBridge] Model loading failed after all retries")
                logger.info("[AIBridge] Will use rule-based fallback analysis")
    
    _ai_status['available'] = False
    return None


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
   - Fine text/small details -> contour_min_area: 8-20, simplification_epsilon: 0.2-0.5
   - text_logo (any) -> simplification_epsilon: 0.2-0.5 (LOWER = more corners preserved; use values < 0.4 for text to preserve letter corners)
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
  "auto_adjustment_reason": "one line reason",
  "mode": "solid|halftone|color",
  "confidence": 0.0-1.0,
  "actions": [
    {"op": "bilateral_filter", "params": {"d": 9, "sigmaColor": 75, "sigmaSpace": 75}}
  ]
}

ALLOWED OPERATIONS FOR 'actions':
denoise, bilateral_filter, gaussian_blur, sharpen, threshold, adaptive_threshold, otsu_threshold, morph_open, morph_close, erode, dilate, contour_smooth, background_remove, color_reduce, kmeans, lpi_adjust, dot_shape, vector_fix
"""

# Default prompt without OpenCV data (fallback)
_PROMPT = _PROMPT_TEMPLATE.replace("{opencv_colors_context}", "No prior OpenCV data. Analyze visually.")


# ─── Caching ──────────────────────────────────────────────────────────────────
_analysis_cache: dict = {}  # {image_hash: result}
import hashlib

def _get_image_hash(image: np.ndarray) -> str:
    """
    FIX GROUP 7.3: Generate MD5 hash for the image to avoid redundant AI calls.
    Uses 64x64 downsample for speed while maintaining uniqueness.
    """
    small = cv2.resize(image, (64, 64), interpolation=cv2.INTER_AREA)
    return hashlib.md5(small.tobytes()).hexdigest()

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
    """Convert numeric ranges like 0.35-0.5 or '0.35-0.5' to single values before JSON parsing."""
    import re
    
    # 🔥 FIX: Handle both quoted and unquoted numeric ranges
    # Pattern 1: Unquoted ranges (like 0.35-0.5 in value position)
    unquoted_pattern = r'(:\s*)(\d+\.?\d*)-(\d+\.?\d*)(\s*[,}\n])'
    
    def replace_unquoted(match):
        prefix, val1, val2, suffix = match.group(1), float(match.group(2)), float(match.group(3)), match.group(4)
        midpoint = (val1 + val2) / 2
        if '.' in match.group(2) or '.' in match.group(3):
            return f'{prefix}{midpoint:.2f}{suffix}'
        else:
            return f'{prefix}{int(midpoint)}{suffix}'
    
    json_str = re.sub(unquoted_pattern, replace_unquoted, json_str)
    
    # Pattern 2: Quoted ranges (like "0.35-0.5")
    quoted_pattern = r'"(\d+\.?\d*)-(\d+\.?\d*)"'
    
    def replace_quoted(match):
        val1, val2 = float(match.group(1)), float(match.group(2))
        midpoint = (val1 + val2) / 2
        if '.' in match.group(1) or '.' in match.group(2):
            return f'"{midpoint:.2f}"'
        else:
            return f'"{int(midpoint)}"'
    
    sanitized = re.sub(quoted_pattern, replace_quoted, json_str)
    logger.info(f"[AIBridge] Sanitized numeric ranges in JSON")
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
    has_ranges = '-' in clean and any(c.isdigit() for c in clean.split('-')[0][-5:])
    if has_ranges:
        logger.info(f"[AIBridge] Detected numeric ranges in response, sanitizing...")
        logger.debug(f"[AIBridge] Before sanitize: {clean[:200]}")
    clean = _sanitize_numeric_ranges(clean)
    if has_ranges:
        logger.debug(f"[AIBridge] After sanitize: {clean[:200]}")

    try:
        result = json.loads(clean)
    except json.JSONDecodeError as e:
        logger.warning(f"[AIBridge] JSON parse failed: {e}")
        logger.warning(f"[AIBridge] Sanitized content: {clean[:300]}")
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
        "confidence": 1.0,
        "actions": [],
        "mode": "solid"
    }
    
    # 0. Intelligent Parameter Aliasing (AI variability handling)
    aliases = {
        'smoothness': 'smoothing_factor',
        'smooth': 'smoothing_factor',
        'corners': 'corner_threshold',
        'corner_sharpness': 'corner_threshold',
        'thickness': 'global_threshold',
        'line_thickness': 'global_threshold',
        'threshold': 'global_threshold',
        'dots': 'lpi',
        'frequency': 'lpi'
    }
    for alias, target in aliases.items():
        if alias in result and target not in result:
            result[target] = result[alias]

    # 1. Parameter Normalization -> Don't reject if missing, just use defaults
    # Required only for NEW image routing, optional for auto-fix adjustments
    for key, default_val in defaults.items():
        if key not in result:
            result[key] = default_val
        else:
            # Coerce type if possible
            try:
                if isinstance(default_val, bool) and not isinstance(result[key], bool):
                    result[key] = str(result[key]).lower() in ('true', '1', 'yes')
                elif isinstance(default_val, int):
                    result[key] = int(float(result[key]))
                elif isinstance(default_val, float):
                    result[key] = float(result[key])
            except (ValueError, TypeError):
                result[key] = default_val

    # 2. Enforce confidence threshold (only if provided)
    if "confidence" in result:
        try:
            conf = float(result["confidence"])
            if conf < 0.4: # Lowered threshold for custom prompts
                logger.warning(f"[AIBridge] Low confidence ({conf}). Using partial results anyway.")
        except (ValueError, TypeError):
            pass

    # 3. Enforce Strict Allowed Operations for Actions
    allowed_ops = {
        "denoise", "bilateral_filter", "gaussian_blur", "sharpen", "threshold",
        "adaptive_threshold", "otsu_threshold", "morph_open", "morph_close",
        "erode", "dilate", "contour_smooth", "background_remove", "color_reduce",
        "kmeans", "lpi_adjust", "dot_shape", "vector_fix"
    }
    
    actions = result.get("actions", [])
    if not isinstance(actions, list):
        logger.error("[AIBridge] Invalid logic: 'actions' must be an array. Rejecting.")
        return _get_safe_fallback()
        
    safe_actions = []
    for action in actions:
        if not isinstance(action, dict) or "op" not in action:
            logger.error("[AIBridge] Action missing 'op'. Rejecting.")
            continue
        if action["op"] not in allowed_ops:
            logger.error(f"[AIBridge] UNSAFE/UNKNOWN operation detected: '{action['op']}'. Dropping action.")
            continue
        safe_actions.append(action)
    result["actions"] = safe_actions

    for key, default_val in defaults.items():
        if key not in result:
            logger.warning(f"[AIBridge] Missing optional: {key}, using default: {default_val}")
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
    result["lpi"]             = int(max(65, min(150, result.get("lpi", 85))))

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
        # Auto-calculate LPI based on DPI if not explicitly set
        dpi = getattr(args, 'dpi', 300)
        default_lpi = min(150, max(65, dpi // 5))
        args.lpi = ai_result.get("lpi", default_lpi)

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


def _resize_for_ai(img: np.ndarray, max_dim: int = 768) -> np.ndarray:
    """Resize image for AI processing while maintaining aspect ratio."""
    h, w = img.shape[:2]
    if max(h, w) <= max_dim:
        return img
    
    scale = max_dim / max(h, w)
    new_w = int(w * scale)
    new_h = int(h * scale)
    return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)


def _normalize_user_prompt(user_prompt: str) -> str:
    """
    FIX Issue #10: Normalize natural language prompt to standard terminology.
    
    Converts common user terms to standard prepress terminology for better AI parsing.
    """
    import re
    
    prompt_lower = user_prompt.lower()
    
    # Synonym mappings: user terms -> standard terms
    synonyms = {
        # Smoothing terms (English & Arabic)
        r'\bsmooth\b|\bsofter\b|\bround\b|\brounded\b|\banti[- ]?alias\b|\bblur\b|أنعم|نعومة|نعمه': 'higher smoothing_factor',
        r'\bjagged\b|\bpixelated\b|\brough\b|\bsharp edges\b|\bhard edges\b|مشرشر|مبكسل|خشن': 'reduce smoothing_factor',
        
        # Corner/sharpness terms
        r'\bsharp\b|\bcrisp\b|\bclean\b|\bprecise\b|\bfine detail\b|حاد|واضح|دقيق': 'lower corner_threshold',
        r'\bround corners\b|\bsoft corners\b|\bfuzzy\b|\bblunt\b|زوايا ناعمة|دوران': 'increase corner_threshold',
        
        # Line thickness
        r'\bthicker\b|\bbold\b|\bheavy\b|\bdark\b|اتقل|سميك|تخين|تقل': 'thicker lines (increase global_threshold)',
        r'\bthinner\b|\blight\b|\bthin\b|\bdelicate\b|اخف|رفيع|خف': 'thinner lines (decrease global_threshold)',
        
        # Halftone terms
        r'\bfiner dots\b|\bsmaller dots\b|\bhigher resolution\b|\bmore detail\b|نقط أصغر|تفاصيل أكتر|دقة عالية': 'increase lpi',
        r'\blarger dots\b|\bbigger dots\b|\bcoarser\b|\blower resolution\b|نقط كبيرة|خشنة': 'decrease lpi',
        
        # Output versioning
        r'\bnew version\b|\banother one\b|\bcopy\b|نسخة تانية|نسخة جديدة': 'create new version',
    }
    
    normalized = user_prompt
    for pattern, standard_term in synonyms.items():
        if re.search(pattern, prompt_lower):
            # Append standard term for clarity (don't replace, just augment)
            normalized += f". [System Intelligence]: This implies {standard_term}."
    
    return normalized


def _extract_json_from_mixed_input(user_prompt: str) -> tuple:
    """
    FIX Issue #10: Extract JSON parameters from mixed natural language + JSON input.
    
    Returns: (cleaned_prompt, extracted_params dict or None)
    """
    import json
    import re
    
    # Look for JSON block in the prompt
    json_pattern = r'\{[^}]*(?:"[^"]*"[^}]*)*\}'
    json_matches = re.findall(json_pattern, user_prompt, re.DOTALL)
    
    extracted = {}
    cleaned_prompt = user_prompt
    
    for json_str in json_matches:
        try:
            parsed = json.loads(json_str)
            extracted.update(parsed)
            # Remove this JSON from the cleaned prompt
            cleaned_prompt = cleaned_prompt.replace(json_str, '')
        except json.JSONDecodeError:
            continue
    
    cleaned_prompt = cleaned_prompt.strip()
    
    return cleaned_prompt, extracted if extracted else None


def analyze_with_prompt(original_path: str, preview_path: str, user_prompt: str, 
                         iteration: int = 1, preserve_original: bool = True) -> Optional[dict]:
    """
    FIX Issue #10: Enhanced AI analysis with natural language normalization and iterative workflow.
    
    Features:
    - Accepts natural language, JSON, or mixed instructions
    - Normalizes user terminology to standard prepress terms
    - Saves AI-fixed output as NEW version (preserves original)
    - Supports iterative AI correction workflow
    
    Args:
        original_path: Path to original input image (for reference)
        preview_path: Path to current preview image (what user sees)
        user_prompt: User's description of desired adjustments (natural language, JSON, or mixed)
        iteration: Iteration number for multi-step correction workflow
        preserve_original: If True, mark result as new version rather than replacement
        
    Returns:
        Dict with parameter adjustments or None if failed
        Format: {
            'smoothing_factor': float,
            'corner_threshold': float,
            'global_threshold': int,
            'lpi': int,
            'adjustment_reason': str,
            'iteration': int,
            'is_new_version': bool,
            'original_preserved': bool
        }
    """
    llm = _get_llm()
    if llm is None:
        logger.warning("[AIBridge] LLM not available for prompt-based analysis")
        return None
    
    # FIX Issue #10: Parse mixed input (natural language + JSON)
    cleaned_prompt, extracted_params = _extract_json_from_mixed_input(user_prompt)
    
    # FIX Issue #10: Normalize terminology
    normalized_prompt = _normalize_user_prompt(cleaned_prompt)
    
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
    
    # Build enhanced prompt with normalization context
    prompt = f"""/no_think
You are a Prepress Engineer for Silk Screen Printing. 

Iteration {iteration} of AI-assisted film correction.

The user wants to adjust their film based on this description:
"{normalized_prompt}"

{'Previously extracted parameters: ' + json.dumps(extracted_params) if extracted_params else ''}

Analyze the current preview image and suggest specific parameter adjustments.
Return STRICT JSON ONLY with these fields:
- smoothing_factor: float (0.1-0.5) - higher = smoother edges, lower = sharper
- corner_threshold: float (30-140) - lower = sharper corners, higher = softer
- global_threshold: int (0-255) - higher = thicker lines, lower = thinner
- lpi: int (45-85) - lines per inch: higher = finer dots, lower = coarser
- dot_shape: string ("round", "ellipse", "line") - round for photos, ellipse for artwork
- adjustment_reason: string - brief explanation of changes in user's language

Example: {{"smoothing_factor": 0.35, "corner_threshold": 95, "global_threshold": 180, "lpi": 55, "dot_shape": "round", "adjustment_reason": "Increased smoothing to reduce jagged edges"}}
"""
    
    logger.info(f"[AIBridge] Iteration {iteration}: Analyzing prompt: {user_prompt[:60]}...")
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
            temperature=0.2 + (iteration * 0.05),  # Slightly more creative on later iterations
            max_tokens=300,
        )
        
        elapsed = time.time() - t0
        raw = response["choices"][0]["message"]["content"]
        logger.info(f"[AIBridge] Prompt response in {elapsed:.1f}s (iteration {iteration})")
        
        result = _parse_response(raw)
        
        if result:
            # FIX Issue #10: Merge with extracted JSON params (extracted params take precedence)
            if extracted_params:
                for key in ['smoothing_factor', 'corner_threshold', 'global_threshold', 'lpi', 'dot_shape']:
                    if key in extracted_params:
                        result[key] = extracted_params[key]
                logger.info(f"[AIBridge] Merged extracted params: {extracted_params}")
            
            # FIX Issue #10: Add versioning metadata
            adjustment_reason = result.get('adjustment_reason', 'Custom adjustments applied')
            if iteration > 1:
                adjustment_reason = f"[Rev {iteration}] {adjustment_reason}"
            
            logger.info(f"[AIBridge] Adjustments applied: {adjustment_reason}")
            
            return {
                'smoothing_factor': float(result.get('smoothing_factor', 0.25)),
                'corner_threshold': float(result.get('corner_threshold', 95.0)),
                'global_threshold': int(result.get('global_threshold', 180)),
                'lpi': int(result.get('lpi', 55)),
                'dot_shape': str(result.get('dot_shape', 'round')),
                'adjustment_reason': adjustment_reason,
                'iteration': iteration,
                'is_new_version': preserve_original,
                'original_preserved': preserve_original,
                'prompt_normalized': normalized_prompt != user_prompt
            }
        return None
        
    except Exception as e:
        logger.error(f"[AIBridge] Prompt analysis failed: {e}")
        return None


# ─── Health Check ─────────────────────────────────────────────────────────────

def is_available() -> bool:
    """
    Check if AI system is available and ready.
    
    Returns True if:
    - llama-cpp is installed
    - Model files exist and are readable
    - Model has been successfully loaded or can be loaded
    
    Also updates _ai_status for diagnostics.
    """
    global _ai_status
    
    # Check if explicitly disabled
    if AI_DISABLED:
        _ai_status['available'] = False
        _ai_status['last_error'] = "AI_DISABLED"
        return False
    
    # Check llama-cpp installation
    try:
        import llama_cpp  # noqa: F401
    except ImportError:
        _ai_status['available'] = False
        _ai_status['last_error'] = "LLAMA_CPP_NOT_INSTALLED"
        return False
    
    # Check model files
    has_model = MODEL_PATH and os.path.exists(MODEL_PATH)
    has_mmproj = MMPROJ_PATH and os.path.exists(MMPROJ_PATH)
    
    _ai_status['model_path'] = MODEL_PATH
    _ai_status['mmproj_path'] = MMPROJ_PATH
    
    if not has_model:
        _ai_status['available'] = False
        msg = f"Vision weights not found at: '{MODEL_PATH or 'None'}'. " \
              f"Please place Qwen .gguf files in: G:\\Designs\\design app\\virtual_design\\models"
        _ai_status['last_error'] = "MODEL_NOT_FOUND"
        logger.error(f"[AIBridge] {msg}")
        return False
    
    if not has_mmproj:
        _ai_status['available'] = False
        msg = f"Vision projector (mmproj) not found at: '{MMPROJ_PATH or 'None'}'. " \
              f"Ensure mmproj-F16.gguf is in the models folder."
        _ai_status['last_error'] = "MMPROJ_NOT_FOUND"
        logger.error(f"[AIBridge] {msg}")
        return False
    
    # If model is already loaded, we're good
    if _llm is not None:
        _ai_status['available'] = True
        _ai_status['last_error'] = None
        return True
    
    # Model files exist but not loaded yet - return True to allow lazy loading
    _ai_status['available'] = True  # Potentially available
    _ai_status['last_error'] = None
    return True


def get_fallback_analysis() -> Dict:
    """
    Rule-based fallback analysis when AI is unavailable.
    
    Provides reasonable defaults based on simple image metrics.
    """
    logger.info("[AIBridge] Using rule-based fallback analysis")
    
    return {
        "image_class": "artwork",
        "num_colors": 3,
        "use_halftone": False,
        "smoothing_factor": 0.25,
        "corner_threshold": 95.0,
        "lpi": 55,
        "dot_shape": "round",
        "upscale_factor": 1.0,
        "denoise_strength": 3,
        "contour_min_area": 50,
        "simplification_epsilon": 1.2,
        "color_merge_advice": "",
        "auto_adjustment_reason": "Rule-based fallback (AI unavailable)",
        "_fallback": True  # Marker that this is fallback
    }
