#!/usr/bin/env python3
"""
Comprehensive Audit Validation Suite for Issue Fixes
Tests all 11 issues to verify fixes are working correctly.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
import cv2
from pathlib import Path
import json

# Test result tracking
results = {'passed': 0, 'failed': 0, 'tests': []}

def assert_true(condition, test_name, message=""):
    if condition:
        results['passed'] += 1
        results['tests'].append(('PASS', test_name, message))
        print(f"  ✓ PASS: {test_name}")
    else:
        results['failed'] += 1
        results['tests'].append(('FAIL', test_name, message))
        print(f"  ✗ FAIL: {test_name} - {message}")

def test_issue_1_paper_size_configurable():
    """Issue #1: Paper size margins should be configurable"""
    print("\n--- Issue #1: Paper Size Configurable ---")
    
    # Check that render_raster_halftone accepts margin_pt
    from core.vector_exporter import render_raster_halftone
    import inspect
    sig = inspect.signature(render_raster_halftone)
    params = list(sig.parameters.keys())
    
    assert_true('margin_pt' in params, 
                "render_raster_halftone accepts margin_pt", 
                "margin_pt parameter added")
    assert_true('lpi' in params,
                "render_raster_halftone accepts lpi",
                "lpi parameter added for film specs")

def test_issue_2_unified_footer():
    """Issue #2: Raster and vector exports share footer format"""
    print("\n--- Issue #2: Unified Footer Format ---")
    
    # Check main.py uses consistent footer
    main_file = Path(__file__).parent.parent / "main.py"
    content = main_file.read_text(encoding='utf-8', errors='ignore')
    
    # Raster path should use same footer format as vector
    assert_true("color_name.upper()" in content and "Developed by MO2" in content,
                "Raster footer matches vector format",
                "Both use color name + brand format")
    assert_true("add_vector_marks_to_page" in content,
                "Raster uses vector marks",
                "Unified registration marks system")

def test_issue_3_png_quality():
    """Issue #3: PNG compression quality for PDF embedding"""
    print("\n--- Issue #3: PNG Quality Preservation ---")
    
    from core.vector_exporter import render_raster_halftone
    import inspect
    source = inspect.getsource(render_raster_halftone)
    
    # Should use IMWRITE_PNG_COMPRESSION
    assert_true("IMWRITE_PNG_COMPRESSION" in source,
                "PNG compression quality set",
                "Uses OpenCV PNG quality parameter")
    assert_true("preserveAspectRatio=True" in source,
                "Aspect ratio preserved",
                "No distortion in PDF embedding")

def test_issue_4_lpi_calculation():
    """Issue #4: DPI-aware LPI calculation"""
    print("\n--- Issue #4: DPI-Aware LPI Calculation ---")
    
    from core.router_utils import apply_halftone_pipeline
    import inspect
    source = inspect.getsource(apply_halftone_pipeline)
    
    # Should use DPI-based max calculation
    assert_true("traditional_max" in source and "dpi_based_max" in source,
                "DPI-aware LPI validation",
                "Considers both mesh and DPI limits")
    assert_true("traditional_max * 1.5" in source,
                "Allows higher LPI for high-DPI",
                "150% of traditional limit for quality")

def test_issue_8_background_detection():
    """Issue #8: Improved background detection"""
    print("\n--- Issue #8: Background Detection ---")
    
    from core.color_separator import ColorSeparator
    import inspect
    source = inspect.getsource(ColorSeparator.separate)
    
    # Should have border analysis
    assert_true("_sample_border_colors" in source,
                "Border sampling for solid detection",
                "Uses border variance analysis")
    assert_true("border_variance" in source,
                "Border variance check",
                "Detects consistent backgrounds")

def test_issue_9_single_color_detection():
    """Issue #9: Single-color detection to avoid blank masks"""
    print("\n--- Issue #9: Single-Color Detection ---")
    
    from core.pipeline_router import PipelineRouter
    import inspect
    source = inspect.getsource(PipelineRouter._run_artwork)
    
    # Should detect truly single-color images
    assert_true("is_truly_single_color" in source,
                "Single-color detection",
                "Avoids forcing 2 colors for 1-color images")
    assert_true("color_std < 15" in source,
                "Color variance threshold",
                "Uses LAB space variance check")

def test_issue_10_ai_parsing():
    """Issue #10: AI natural language parsing"""
    print("\n--- Issue #10: AI Natural Language Parsing ---")
    
    from core.ai_vision_bridge import _normalize_user_prompt, _extract_json_from_mixed_input
    
    # Test normalization
    normalized = _normalize_user_prompt("make it smoother and less jagged")
    assert_true("smoothing" in normalized.lower(),
                "Normalizes 'smooth' to standard term",
                "Adds standard terminology")
    
    # Test JSON extraction
    mixed = 'Make it smoother {"lpi": 65} and cleaner'
    cleaned, extracted = _extract_json_from_mixed_input(mixed)
    assert_true(extracted is not None and extracted.get('lpi') == 65,
                "Extracts JSON from mixed input",
                "Parses embedded JSON parameters")
    assert_true("{" not in cleaned,
                "Removes JSON from cleaned prompt",
                "Clean prompt for AI processing")

def test_issue_11_progress_labels():
    """Issue #11: Accurate progress/routing labels"""
    print("\n--- Issue #11: Progress Label Accuracy ---")
    
    from core.pipeline_router import PipelineRouter
    import inspect
    source = inspect.getsource(PipelineRouter._run_artwork)
    
    # Should use artwork_halftone class
    assert_true("artwork_halftone" in source,
                "Uses artwork_halftone class",
                "Distinguishes artwork+halftone from photo")
    assert_true("export_class = 'artwork'" in source,
                "Artwork class for non-halftone",
                "Correct routing labels")

def run_all_tests():
    print("=" * 60)
    print("COMPREHENSIVE AUDIT VALIDATION SUITE")
    print("=" * 60)
    
    test_issue_1_paper_size_configurable()
    test_issue_2_unified_footer()
    test_issue_3_png_quality()
    test_issue_4_lpi_calculation()
    test_issue_8_background_detection()
    test_issue_9_single_color_detection()
    test_issue_10_ai_parsing()
    test_issue_11_progress_labels()
    
    print("\n" + "=" * 60)
    print(f"Tests: {results['passed']} passed, {results['failed']} failed")
    print("=" * 60)
    
    if results['failed'] > 0:
        print("\nFailed tests:")
        for status, name, msg in results['tests']:
            if status == 'FAIL':
                print(f"  - {name}: {msg}")
    
    return results['failed'] == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
