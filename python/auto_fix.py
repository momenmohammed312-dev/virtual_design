#!/usr/bin/env python3
"""
auto_fix.py - AI Auto-Fix for Preview Flaws
Virtual Design Silk Screen Studio

Analyzes preview image vs original and suggests parameter adjustments.
Task 5.1 FIX: Added --prompt argument for user-guided AI adjustments.
"""

import argparse
import os
import cv2
import re
import json
import sys
try:
    import google.generativeai as genai
    import PIL.Image as PilImage
    _GEMINI_AVAILABLE = True
except ImportError:
    _GEMINI_AVAILABLE = False
from core.ai_vision_bridge import analyze_preview_flaws, analyze_with_prompt


def _analyze_with_gemini(original_path: str, preview_path: str, user_prompt: str):
    """Use Google Gemini 1.5 Flash for AI auto-fix analysis."""
    if not _GEMINI_AVAILABLE:
        return None
    
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        api_key = "AIzaSyB5gcq64Zym2xlPylXDfD4hb2X-8UdkAfg"
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        img_orig = PilImage.open(original_path).convert("RGB")
        img_prev = PilImage.open(preview_path).convert("RGB")
        
        prompt = f"""You are a professional silk screen printing expert.
Compare the original image and the processed film preview.
User request: "{user_prompt}"

Respond ONLY with a valid JSON object. No markdown, no explanation, no extra text.

Return exactly this structure:
{{"smoothing_factor": 0.25, "corner_threshold": 95.0, "use_halftone": false, "lpi": 65, "denoise_strength": 3, "simplification_epsilon": 1.2, "adjustment_reason": "one line explanation"}}

Rules:
- smoothing_factor: 0.01 to 0.65
- corner_threshold: 20 to 180
- lpi: 35 to 150
- denoise_strength: 0 to 10
- simplification_epsilon: 0.01 to 3.0
- use_halftone: true or false
"""
        response = model.generate_content([prompt, img_orig, img_prev])
        text = response.text.strip()
        
        # Strip markdown if present
        text = re.sub(r'```json|```', '', text).strip()
        
        json_match = re.search(r'\{.*?\}', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        return None
    except Exception as e:
        print(json.dumps({"error": f"Gemini API failed: {e}"}), file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(description='AI Auto-Fix Preview Flaws')
    parser.add_argument('--original', required=True, help='Path to original image')
    parser.add_argument('--preview', required=True, help='Path to preview image')
    parser.add_argument('--prompt', type=str, default=None,
                        help='User description of desired adjustments (enables custom AI analysis)')
    parser.add_argument('--iteration', type=int, default=1, help='Iteration number for autofix')
    parser.add_argument('--prev-params', type=str, default=None, help='JSON string of previous params')
    args = parser.parse_args()

    # Load images
    original = cv2.imread(args.original)
    preview = cv2.imread(args.preview)

    if original is None:
        print(json.dumps({'error': f'Cannot load original: {args.original}'}))
        sys.exit(1)
    if preview is None:
        print(json.dumps({'error': f'Cannot load preview: {args.preview}'}))
        sys.exit(1)

    # Load previous params if existing
    prev_params = json.loads(args.prev_params) if args.prev_params else None

    # Task 5.1 FIX: Use prompt-based analysis if user provided a prompt
    if args.prompt:
        # Try Gemini first (fast, free, no local model needed)
        result = _analyze_with_gemini(args.original, args.preview, args.prompt)
        
        # Fallback to local model only if Gemini failed
        if not result:
            try:
                result = analyze_with_prompt(
                    args.original, args.preview, args.prompt,
                    iteration=args.iteration,
                    previous_params=prev_params
                )
            except Exception as e:
                print(json.dumps({"error": f"Local model failed: {e}"}), file=sys.stderr)
                result = None
        
        # Last resort: return size-aware safe defaults so Flutter doesn't show error
        if not result:
            orig = cv2.imread(args.original)
            h, w = orig.shape[:2] if orig is not None else (1000, 1000)
            max_dim = max(h, w)
            if max_dim < 400:
                smooth, corner, eps = 0.35, 60.0, 1.8
            elif max_dim < 800:
                smooth, corner, eps = 0.30, 65.0, 1.6
            elif max_dim < 1500:
                smooth, corner, eps = 0.25, 80.0, 1.3
            elif max_dim < 2500:
                smooth, corner, eps = 0.20, 100.0, 1.0
            else:
                smooth, corner, eps = 0.15, 120.0, 0.8
            result = {
                "smoothing_factor": smooth,
                "corner_threshold": corner,
                "denoise_strength": 3,
                "simplification_epsilon": eps,
                "adjustment_reason": f"Could not analyze image. Returning size-aware defaults (max_dim={max_dim}px). Prompt was: {args.prompt}"
            }
    else:
        # Standard auto-fix analysis
        result = analyze_preview_flaws(args.original, args.preview,
                                       prev_params=prev_params,
                                       iteration=args.iteration)

    if result:
        # Output JSON for Flutter to parse
        print(json.dumps(result))
        sys.exit(0)
    else:
        print(json.dumps({'error': 'AI analysis failed'}))
        sys.exit(1)


if __name__ == '__main__':
    main()
