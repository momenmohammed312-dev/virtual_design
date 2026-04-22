"""
ai_vision_bridge.py — Qwen3-VL Local Model Integration
Virtual Design Silk Screen Studio

FIX GROUP: Robust AI AutoFix System with:
- Model auto-discovery from common paths
- Environment variable configuration
- Graceful fallback when model unavailable
- Caching and performance optimization
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
AI_MAX_DIM = 448  # Optimized for Qwen-VL 2B input size (speeds up inference significantly)

# ═══ MODEL CONFIGURATION WITH AUTO-DISCOVERY ═══

def _find_model_files() -> Tuple[str, str]:
    env_model = os.environ.get("QWEN_MODEL_PATH", "").strip()
    env_mmproj = os.environ.get("QWEN_MMPROJ_PATH", "").strip()
    
    if env_model and env_mmproj:
        if os.path.exists(env_model) and os.path.exists(env_mmproj):
            return env_model, env_mmproj

    try:
        current_file = Path(__file__).resolve()
        root_dir = current_file.parents[2]
    except Exception:
        root_dir = Path.cwd()

    search_dirs = [
        root_dir / "models",
        root_dir / "Models",
        Path.cwd() / "models",
        Path.cwd(),
        Path.home() / "models",
        Path.home() / "Downloads",
    ]
    
    model_patterns = ["*Qwen3*VL*.gguf", "*Qwen-VL*.gguf", "*vision*.gguf", "*.gguf"]
    mmproj_patterns = ["*mmproj*.gguf", "*vision*proj*.gguf"]
    
    found_model = None
    found_mmproj = None

    for search_dir in search_dirs:
        if not search_dir.exists(): continue
            
        if not found_model:
            for pattern in model_patterns:
                try:
                    matches = list(search_dir.glob(pattern))
                    matches = [m for m in matches if 'mmproj' not in m.name.lower() and m.stat().st_size > 500*1024*1024]
                    if matches:
                        matches.sort(key=lambda x: x.stat().st_size, reverse=True)
                        found_model = matches[0]
                        break
                except Exception: continue

        if not found_mmproj:
            for pattern in mmproj_patterns:
                try:
                    matches = list(search_dir.glob(pattern))
                    if matches:
                        found_mmproj = matches[0]
                        break
                except Exception: continue

        if found_model and found_mmproj: break
    
    return str(found_model) if found_model else "", str(found_mmproj) if found_mmproj else ""

_MODEL_PATH, _MMPROJ_PATH = _find_model_files()
MODEL_PATH = os.environ.get("QWEN_MODEL_PATH", _MODEL_PATH)
MMPROJ_PATH = os.environ.get("QWEN_MMPROJ_PATH", _MMPROJ_PATH)
AI_DISABLED = os.environ.get("AI_DISABLED", "").lower() in ("1", "true", "yes", "on")

_ai_status = {
    'initialized': False,
    'available': False,
    'last_error': None,
    'model_path': MODEL_PATH,
    'mmproj_path': MMPROJ_PATH,
}

# Log AI status at module load - VERY VISIBLE
logger.info("🔵🔵🔵" * 20)
logger.info("[AIBridge] 🤖 AI VISION BRIDGE MODULE LOADED")
logger.info(f"[AIBridge] 📁 Model path: {MODEL_PATH if MODEL_PATH else 'NOT FOUND'}")
logger.info(f"[AIBridge] 📁 MMProj path: {MMPROJ_PATH if MMPROJ_PATH else 'NOT FOUND'}")
logger.info(f"[AIBridge] 🔧 AI Disabled: {AI_DISABLED}")
if MODEL_PATH and os.path.exists(MODEL_PATH):
    size_mb = os.path.getsize(MODEL_PATH) / (1024*1024)
    logger.info(f"[AIBridge] ✅ Model file exists ({size_mb:.1f} MB) - AI IS AVAILABLE")
else:
    logger.warning("[AIBridge] ❌ Model file NOT FOUND - AI will use FAST CLASSIFIER fallback")
logger.info("🔵🔵🔵" * 20)

_llm = None

def get_ai_status() -> Dict:
    return _ai_status.copy()

def _get_llm():
    global _llm, _ai_status
    if _llm is not None: return _llm
    if AI_DISABLED: return None
    if not MODEL_PATH or not os.path.exists(MODEL_PATH): return None
    if not MMPROJ_PATH or not os.path.exists(MMPROJ_PATH): return None
    
    try:
        from llama_cpp import Llama
    except ImportError: return None
    
    try:
        cpu_count = os.cpu_count() or 4
        target_threads = max(4, min(cpu_count - 1, 16))
        gpu_layers = 33 if os.environ.get("USE_GPU", "1") == "1" else 0
        
        _llm = Llama(
            model_path   = MODEL_PATH,
            mmproj       = MMPROJ_PATH,
            n_ctx        = 8192,
            n_threads    = target_threads,
            n_gpu_layers = gpu_layers, 
            verbose      = False,
        )
        _ai_status['available'] = True
        _ai_status['initialized'] = True
        return _llm
    except Exception: return None


# ─── API ─────────────────────────────────────────────────────────────────────

def _classify_without_ai(image: np.ndarray) -> Optional[str]:
    """Fast heuristic bypass — only for pure binary B&W images with no color."""
    logger.info("[AIBridge] 🔍 Fast Classifier Check - analyzing image characteristics...")
    if len(image.shape) == 3:
        # Check saturation: if image has significant color, never bypass
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        sat_mean = float(np.mean(hsv[:, :, 1])) / 255.0
        if sat_mean > 0.08:  # Has meaningful color → must use AI
            return None
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
    total = gray.size
    dark_ratio = hist[:20].sum() / total   # Strict: only pure black
    light_ratio = hist[235:].sum() / total  # Strict: only pure white
    # Only bypass if image is ≥ 96% pure black + white (truly binary)
    if dark_ratio + light_ratio > 0.96:
        return 'text_logo'
    return None

def analyze_image(image: np.ndarray, opencv_colors: list = None) -> Optional[dict]:
    """Analyze image with Fast-Classifier bypass for speed."""
    print("🤖 [AIBridge] ===== AI ANALYSIS STARTED =====", flush=True)
    logger.info("[AIBridge] ===== AI ANALYSIS STARTED =====")
    
    # 1. Check Cache
    img_hash = _get_image_hash(image)
    if img_hash in _ai_cache: 
        print("♻️ [AIBridge] Using cached result", flush=True)
        logger.info("[AIBridge] ♻️ Using cached result")
        return _ai_cache[img_hash]
    
    # 2. Skip AI for simple logos (Fix for analysis delay)
    fast_class = _classify_without_ai(image)
    if fast_class:
        print(f"⚡ [AIBridge] FAST CLASSIFIER BYPASS: {fast_class}", flush=True)
        logger.info(f"[AIBridge] ⚡ FAST CLASSIFIER BYPASS: {fast_class} (pure B&W logo)")
        res = _get_safe_fallback()
        res['image_class'] = fast_class
        res['confidence'] = 1.0
        return _validate_ai_params(res)
    
    print("🧠 [AIBridge] AI Model required (not a simple B&W logo)", flush=True)
    logger.info("[AIBridge] 🧠 AI Model required (not a simple B&W logo)")

    llm = _get_llm()
    if llm is None: 
        print("❌ [AIBridge] AI Model NOT AVAILABLE - using safe fallback", flush=True)
        logger.warning("[AIBridge] ❌ AI Model NOT AVAILABLE - using safe fallback")
        return _get_safe_fallback()
    
    print("✅ [AIBridge] AI Model loaded, analyzing image...", flush=True)
    logger.info("[AIBridge] ✅ AI Model loaded, analyzing image...")

    h, w = image.shape[:2]
    max_dim = 512
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        image = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    
    _, buf = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 85])
    img_b64 = base64.b64encode(buf).decode()

    prompt = _PROMPT
    if opencv_colors:
        color_lines = [f"  {i+1}. {c['hex']} - {c['coverage']:.1f}% coverage" for i, c in enumerate(opencv_colors[:8])]
        prompt = _PROMPT_TEMPLATE.replace("{opencv_colors_context}", "\n".join(color_lines))

    # LOG: Show the prompt being sent to AI
    logger.info("=" * 60)
    logger.info("[AIBridge] 📝 PROMPT SENT TO AI MODEL:")
    logger.info(f"{prompt}")
    logger.info("=" * 60)
    print("=" * 60, flush=True)
    print("📝 [AIBridge] PROMPT SENT TO AI MODEL:", flush=True)
    print(f"{prompt}", flush=True)
    print("=" * 60, flush=True)

    try:
        response = llm.create_chat_completion(
            messages=[{"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}, {"type": "text", "text": prompt}]}],
            temperature = 0.1, max_tokens = 250
        )
        raw = response["choices"][0]["message"]["content"]
        result = _parse_response(raw) or _get_safe_fallback()
        result = _adjust_for_resolution(result, h, w)
        _ai_cache[img_hash] = result
        
        # Log AI results
        print(f"✅ [AIBridge] AI ANALYSIS COMPLETE", flush=True)
        print(f"📊 [AIBridge] Class: {result.get('image_class', 'unknown')}", flush=True)
        print(f"📊 [AIBridge] Params: denoise={result.get('denoise_strength', '-')}, "
              f"upscale={result.get('upscale_factor', '-')}, "
              f"smooth={result.get('smoothing_factor', '-')}, "
              f"corner={result.get('corner_threshold', '-')}", flush=True)
        logger.info(f"[AIBridge] ✅ AI ANALYSIS COMPLETE")
        logger.info(f"[AIBridge] 📊 Class: {result.get('image_class', 'unknown')}")
        logger.info(f"[AIBridge] 📊 Params: denoise={result.get('denoise_strength', '-')}, "
                   f"upscale={result.get('upscale_factor', '-')}, "
                   f"smooth={result.get('smoothing_factor', '-')}, "
                   f"corner={result.get('corner_threshold', '-')}")
        return result
    except Exception as e:
        print(f"❌ [AIBridge] AI Analysis failed: {e}", flush=True)
        logger.error(f"[AIBridge] ❌ AI Analysis failed: {e}")
        return _get_safe_fallback()

def _get_safe_fallback() -> dict:
    return {
        "image_class":"artwork", "num_colors":3, "use_halftone":False,
        "smoothing_factor":0.25, "corner_threshold":95.0, "lpi":55,
        "dot_shape":"round", "upscale_factor":1.0, "denoise_strength":3,
        "contour_min_area":50, "simplification_epsilon":1.2
    }

def _adjust_for_resolution(result: dict, h: int, w: int) -> dict:
    max_dim = max(h, w)
    if max_dim < 500:
        result["smoothing_factor"] = max(result.get("smoothing_factor", 0.1), 0.3)
        result["simplification_epsilon"] = max(result.get("simplification_epsilon", 0.1), 1.5)
    return result

def _parse_response(raw: str) -> Optional[dict]:
    import re
    clean = raw.strip()
    if clean.startswith("```"):
        lines = clean.split("\n")
        clean = "\n".join(lines[1:-1])
    if "<think>" in clean:
        clean = re.sub(r"<think>.*?</think>", "", clean, flags=re.DOTALL).strip()
    
    try:
        res = json.loads(clean)
        return _validate_ai_params(res)
    except: return None

def _validate_ai_params(result: dict) -> dict:
    img_class = result.get("image_class", "artwork")
    
    # FIX A-15: Tightened constraints for Text Logos (Diagonal edges in M, A, etc.)
    if img_class == "text_logo":
        # REDUCED: Epsilon 0.05 ensures geometric perfection
        result["simplification_epsilon"] = 0.05
        # REDUCED: Smoothing 0.05 prevents vertices from jittering
        result["smoothing_factor"] = 0.05
        # STRICT: Corner threshold 35 preserves sharp serifs
        result["corner_threshold"] = 35.0
    
    # Global safety clamps
    result["smoothing_factor"] = max(0.01, min(0.6, float(result.get("smoothing_factor", 0.25))))
    result["corner_threshold"] = max(20.0, min(180.0, float(result.get("corner_threshold", 95.0))))
    result["simplification_epsilon"] = max(0.01, min(3.0, float(result.get("simplification_epsilon", 1.2))))
    
    return result

_PROMPT = """You are a professional silk screen printing expert and image analyst.
Analyze this image and respond ONLY with a valid JSON object. No markdown, no explanation.

Determine the best processing parameters for silk screen printing:

- image_class: one of "text_logo" (sharp edges, 1-3 flat colors, text/icons), "artwork" (illustrations, limited colors, medium detail), "photo" (photographs, gradients, many tones)
- num_colors: integer 1-8, exact number of ink colors needed for printing
- use_halftone: true if gradients or photographic tones are present, false for flat/solid areas
- lpi: integer 35-150, recommended lines-per-inch for halftone screen (lower for coarse mesh, higher for fine mesh)
- smoothing_factor: float 0.01-0.5, how much to smooth vector paths (low for text/logos, higher for photos)
- corner_threshold: float 20-180, angle in degrees for corner detection (low=sharp corners, high=smooth curves)
- simplification_epsilon: float 0.01-3.0, path simplification tolerance
- dot_shape: one of "round", "ellipse", "square", "line"
- upscale_factor: float 1.0-4.0, how much to upscale if image is low resolution
- denoise_strength: integer 0-10, noise removal strength

Respond with ONLY this JSON structure:
{"image_class": "artwork", "num_colors": 3, "use_halftone": false, "lpi": 65, "smoothing_factor": 0.25, "corner_threshold": 95.0, "simplification_epsilon": 1.2, "dot_shape": "round", "upscale_factor": 1.0, "denoise_strength": 3}"""

_PROMPT_TEMPLATE = _PROMPT
_ai_cache = {}

def _get_image_hash(image: np.ndarray) -> str:
    import hashlib
    small = cv2.resize(image, (64, 64), interpolation=cv2.INTER_AREA)
    return hashlib.md5(small.tobytes()).hexdigest()

def apply_to_args(ai_result: dict, args) -> None:
    if not ai_result: return
    # Final clamping for text path
    if ai_result.get('image_class') == 'text_logo':
         args.smoothing = 0.05
         args.simplification = 0.05
    if getattr(args, 'colors', 0) == 0:
        args.colors = ai_result.get("num_colors", 1)


# ─── Auto-Fix Functions (used by auto_fix.py) ────────────────────────────────

def analyze_preview_flaws(
    original_path: str,
    preview_path: str,
    prev_params: Optional[dict] = None,
    iteration: int = 1,
) -> Optional[dict]:
    """
    Compare original vs preview image and suggest parameter adjustments.
    Uses heuristic analysis (histogram + edge density) with AI enhancement
    when available.
    """
    original = cv2.imread(original_path)
    preview = cv2.imread(preview_path)

    if original is None or preview is None:
        logger.error(f"[AutoFix] Failed to load images: orig={original_path}, prev={preview_path}")
        return None

    # Convert to grayscale for analysis
    orig_gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY) if len(original.shape) == 3 else original
    prev_gray = cv2.cvtColor(preview, cv2.COLOR_BGR2GRAY) if len(preview.shape) == 3 else preview

    # Resize preview to match original if needed
    if orig_gray.shape != prev_gray.shape:
        prev_gray = cv2.resize(prev_gray, (orig_gray.shape[1], orig_gray.shape[0]),
                               interpolation=cv2.INTER_AREA)

    # --- Heuristic Analysis ---
    # 1. Histogram comparison (detail preservation)
    hist_orig = cv2.calcHist([orig_gray], [0], None, [256], [0, 256]).flatten()
    hist_prev = cv2.calcHist([prev_gray], [0], None, [256], [0, 256]).flatten()
    hist_orig = hist_orig / hist_orig.sum()
    hist_prev = hist_prev / hist_prev.sum()
    hist_correlation = float(cv2.compareHist(
        hist_orig.astype(np.float32), hist_prev.astype(np.float32), cv2.HISTCMP_CORREL
    ))

    # 2. Edge density comparison (sharpness preservation)
    edges_orig = cv2.Canny(orig_gray, 50, 150)
    edges_prev = cv2.Canny(prev_gray, 50, 150)
    edge_density_orig = np.sum(edges_orig > 0) / edges_orig.size
    edge_density_prev = np.sum(edges_prev > 0) / edges_prev.size
    edge_ratio = edge_density_prev / max(edge_density_orig, 1e-6)

    # 3. Build suggestions
    suggestions = {}

    # If preview lost too many edges → reduce smoothing
    if edge_ratio < 0.6:
        suggestions['smoothing_factor'] = max(0.05, (prev_params or {}).get('smoothing_factor', 0.25) * 0.7)
        suggestions['reason_smoothing'] = f'Edge loss detected (ratio={edge_ratio:.2f}), reducing smoothing'

    # If preview has too many edges → increase smoothing
    if edge_ratio > 1.5:
        suggestions['smoothing_factor'] = min(0.5, (prev_params or {}).get('smoothing_factor', 0.25) * 1.3)
        suggestions['reason_smoothing'] = f'Edge noise detected (ratio={edge_ratio:.2f}), increasing smoothing'

    # If histogram diverges significantly → adjust corner threshold
    if hist_correlation < 0.85:
        suggestions['corner_threshold'] = min(150.0, (prev_params or {}).get('corner_threshold', 95.0) * 1.1)
        suggestions['reason_histogram'] = f'Histogram divergence (corr={hist_correlation:.3f})'

    # Build result
    result = {
        'iteration': iteration,
        'analysis': {
            'hist_correlation': hist_correlation,
            'edge_ratio': edge_ratio,
            'edge_density_original': float(edge_density_orig),
            'edge_density_preview': float(edge_density_prev),
        },
        'suggestions': suggestions,
        'adjusted_params': {**(prev_params or {}), **suggestions},
    }

    logger.info(f"[AutoFix] Iteration {iteration}: hist_corr={hist_correlation:.3f}, "
                f"edge_ratio={edge_ratio:.2f}, suggestions={list(suggestions.keys())}")
    return result


def analyze_with_prompt(
    original_path: str,
    preview_path: str,
    user_prompt: str,
    iteration: int = 1,
    previous_params: Optional[dict] = None,
) -> Optional[dict]:
    """
    AI-guided analysis using a user-provided natural language prompt.
    Falls back to heuristic analysis when AI model is unavailable.
    """
    # First, run heuristic analysis as baseline
    base_result = analyze_preview_flaws(
        original_path, preview_path,
        prev_params=previous_params,
        iteration=iteration,
    )
    if base_result is None:
        return None

    base_result['user_prompt'] = user_prompt

    # Attempt AI-enhanced analysis if model is available
    llm = _get_llm()
    if llm is None:
        logger.info("[AutoFix] AI model not available, using heuristic-only analysis")
        base_result['ai_enhanced'] = False
        return base_result

    # Load and encode images for AI
    try:
        original = cv2.imread(original_path)
        preview = cv2.imread(preview_path)
        if original is None or preview is None:
            base_result['ai_enhanced'] = False
            return base_result

        # Resize for AI input
        for img_ref in [original, preview]:
            h, w = img_ref.shape[:2]
            if max(h, w) > AI_MAX_DIM:
                scale = AI_MAX_DIM / max(h, w)
                img_ref = cv2.resize(img_ref, (int(w * scale), int(h * scale)),
                                     interpolation=cv2.INTER_AREA)

        _, buf_orig = cv2.imencode('.jpg', original, [cv2.IMWRITE_JPEG_QUALITY, 80])
        _, buf_prev = cv2.imencode('.jpg', preview, [cv2.IMWRITE_JPEG_QUALITY, 80])
        b64_orig = base64.b64encode(buf_orig).decode()
        b64_prev = base64.b64encode(buf_prev).decode()

        ai_prompt = (
            f"You are a silk screen printing expert. Analyze the user's request carefully.\n\n"
            f"USER'S REQUEST (IMPORTANT): \"{user_prompt}\"\n\n"
            f"Current parameters: {json.dumps(previous_params or {})}\n\n"
            f"Instructions:\n"
            f"1. Focus on what the user is specifically asking for in their request.\n"
            f"2. Adjust parameters to match the user's needs exactly.\n"
            f"3. If user asks for 'halftone' or 'dots', set use_halftone=true and adjust lpi.\n"
            f"4. If user asks for 'smoother', increase smoothing_factor.\n"
            f"5. If user asks for 'sharper edges', increase corner_threshold.\n\n"
            f"Respond ONLY with a JSON object containing adjusted parameters:\n"
            f'{{"smoothing_factor": 0.0-0.5, "corner_threshold": 20-180, '
            f'"simplification_epsilon": 0.01-3.0, "use_halftone": true/false, '
            f'"lpi": 45-150, "dot_sizes": [1.0, 0.8, 1.2], '
            f'"reason": "brief explanation based on user request"}}'
        )

        response = llm.create_chat_completion(
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_orig}"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_prev}"}},
                    {"type": "text", "text": ai_prompt},
                ]
            }],
            temperature=0.7,  # Increased for more varied responses
            max_tokens=300,
        )

        raw = response["choices"][0]["message"]["content"]
        ai_params = _parse_response(raw)
        if ai_params:
            base_result['ai_enhanced'] = True
            base_result['ai_suggestions'] = ai_params
            # Merge AI suggestions into adjusted params
            base_result['adjusted_params'].update(ai_params)
        else:
            base_result['ai_enhanced'] = False

    except Exception as e:
        logger.warning(f"[AutoFix] AI-enhanced analysis failed: {e}")
        base_result['ai_enhanced'] = False

    return base_result
