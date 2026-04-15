#!/usr/bin/env python3
"""
auto_fix.py - AI Auto-Fix for Preview Flaws
Virtual Design Silk Screen Studio

Analyzes preview image vs original and suggests parameter adjustments.
Task 5.1 FIX: Added --prompt argument for user-guided AI adjustments.
"""

import argparse
import sys
import json
import base64
import cv2
import numpy as np
from pathlib import Path

# Add core to path
sys.path.insert(0, str(Path(__file__).parent))

from core.ai_vision_bridge import analyze_preview_flaws, analyze_with_prompt


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
        result = analyze_with_prompt(args.original, args.preview, args.prompt,
                                     iteration=args.iteration,
                                     previous_params=prev_params)
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
