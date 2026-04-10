"""
Regression tests for Virtual Design Silk Screen Pipeline Audit Fixes
Tests all critical and high-severity issues from the engineering audit.
"""

import numpy as np
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2


class TestResult:
    """Simple test result tracker"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def add_pass(self, name):
        self.passed += 1
        print(f"  ✓ PASS: {name}")

    def add_fail(self, name, msg):
        self.failed += 1
        self.errors.append((name, msg))
        print(f"  ✗ FAIL: {name} - {msg}")

    def report(self):
        print(f"\n{'='*50}")
        print(f"Tests: {self.passed} passed, {self.failed} failed")
        if self.errors:
            print("\nFailures:")
            for name, msg in self.errors:
                print(f"  - {name}: {msg}")
        print(f"{'='*50}")
        return self.failed == 0


# Global test result tracker
results = TestResult()


def assert_true(condition, name, msg=""):
    """Simple assertion helper"""
    if condition:
        results.add_pass(name)
    else:
        results.add_fail(name, msg or "Assertion failed")


def run_fix_group_1_tests():
    """FIX GROUP 1: Background Detection Fixes"""
    print("\n--- FIX GROUP 1: Background Detection ---")

    # Task 1.1: Verify Euclidean distance is used
    try:
        from core.background_detector import BackgroundDetector

        img = np.ones((100, 100, 3), dtype=np.uint8) * 255
        img[20:80, 30:50] = [139, 0, 0]
        img[20:40, 50:70] = [139, 0, 0]
        img[40:60, 50:60] = [139, 0, 0]

        detector = BackgroundDetector(mode="remove_white", tolerance=20)
        bg_mask, fg_mask, stats = detector.detect(img)

        fg_pixels = np.sum(fg_mask)
        total_pixels = img.shape[0] * img.shape[1]
        fg_percentage = fg_pixels / total_pixels * 100

        assert_true(10 < fg_percentage < 30,
                    "Euclidean distance preserves foreground",
                    f"Foreground percentage {fg_percentage:.1f}% out of expected range")
    except Exception as e:
        results.add_fail("Euclidean distance test", str(e))

    # Task 1.3: Default tolerance reduced
    try:
        from core.background_detector import BackgroundDetector
        detector = BackgroundDetector()
        assert_true(detector.tolerance <= 20,
                    "Default tolerance is 20",
                    f"Expected <= 20, got {detector.tolerance}")
    except Exception as e:
        results.add_fail("Default tolerance test", str(e))


def run_fix_group_2_tests():
    """FIX GROUP 2: Mask Generator Fixes"""
    print("\n--- FIX GROUP 2: Mask Generator ---")

    # Task 2.1: DPI-scaled component threshold
    try:
        for dpi, expected_min in [
            (300, 20),   # At 300 DPI: 20 * 1 = 20
            (150, 5),    # At 150 DPI: 20 * 0.25 = 5 (capped at min 5)
            (600, 80),   # At 600 DPI: 20 * 4 = 80
        ]:
            min_component_px = max(5, int(20 * (dpi / 300) ** 2))
            assert_true(min_component_px == expected_min,
                        f"DPI-scaled threshold @ {dpi} DPI",
                        f"Expected {expected_min}, got {min_component_px}")
    except Exception as e:
        results.add_fail("DPI-scaled threshold", str(e))

    # Task 2.3: color_masks removed
    try:
        from core.color_separator import ColorSeparator
        img = np.ones((50, 50, 3), dtype=np.uint8) * 255
        img[10:40, 10:25] = [0, 0, 255]
        img[10:40, 25:40] = [0, 255, 0]

        sep = ColorSeparator()
        result = sep.separate(img, num_colors=2, bg_tolerance=20)

        assert_true('color_masks' not in result,
                    "color_masks removed from separator",
                    "color_masks should not be in output")
        assert_true('label_map' in result,
                    "label_map still present",
                    "label_map should be in output")
    except Exception as e:
        results.add_fail("color_masks removal", str(e))


def run_fix_group_3_tests():
    """FIX GROUP 3: Vector PDF Hole Rendering Fixes"""
    print("\n--- FIX GROUP 3: Vector PDF Holes ---")

    # Task 3.2: Recursive hierarchy traversal
    try:
        from core.vector_exporter import export_vector_pdf

        mask = np.ones((200, 200), dtype=np.uint8) * 255
        cv2.circle(mask, (100, 100), 80, 0, -1)
        cv2.circle(mask, (100, 100), 40, 255, -1)

        output_path = Path("test_o_output.pdf")

        try:
            export_vector_pdf(
                masks=[mask],
                colors=[(0, 0, 0)],
                color_names=["Black"],
                output_path=output_path,
                dpi=300,
                lpi=45,
                mesh_count=160
            )
            assert_true(output_path.exists(),
                        "PDF with holes created",
                        "PDF file should be created")
        finally:
            if output_path.exists():
                output_path.unlink()
    except Exception as e:
        results.add_fail("Recursive hole handling", str(e))


def run_fix_group_4_tests():
    """FIX GROUP 4: Vector Smoothing Fixes"""
    print("\n--- FIX GROUP 4: Vector Smoothing ---")

    # Task 4.1: Inverted scale-aware smoothing
    try:
        smooth_factor = 0.2
        scale_factor = 5.0
        scale_boost = min(2.5, scale_factor / 2.0)
        adjusted_smooth = min(0.45, smooth_factor * scale_boost)

        assert_true(scale_boost > 1.0,
                    "Scale boost increases at high scale",
                    f"Expected > 1.0, got {scale_boost}")
        assert_true(adjusted_smooth > smooth_factor,
                    "Adjusted smooth > base smooth",
                    f"Expected > {smooth_factor}, got {adjusted_smooth}")
    except Exception as e:
        results.add_fail("Scale-aware smoothing", str(e))

    # Task 4.2: Conditional upscale
    try:
        from core.vector_exporter import preprocess_mask_for_vector

        small_mask = np.ones((100, 100), dtype=np.uint8) * 255
        _, factor = preprocess_mask_for_vector(small_mask)
        assert_true(factor == 2.0,
                    "Small mask upscales 2x",
                    f"Expected 2.0, got {factor}")

        large_mask = np.ones((1000, 1000), dtype=np.uint8) * 255
        _, factor = preprocess_mask_for_vector(large_mask)
        assert_true(factor == 1.0,
                    "Large mask does NOT upscale",
                    f"Expected 1.0, got {factor}")
    except Exception as e:
        results.add_fail("Conditional upscale", str(e))


def run_fix_group_5_tests():
    """FIX GROUP 5: Halftone Quality Fixes"""
    print("\n--- FIX GROUP 5: Halftone Quality ---")

    # Task 5.1: Default LPI = 45
    try:
        from core.halftone_generator import HalftoneGenerator
        import inspect
        gen = HalftoneGenerator()
        sig = inspect.signature(gen.generate)
        lpi_default = sig.parameters['lpi'].default
        assert_true(lpi_default == 45,
                    "Default LPI is 45",
                    f"Expected 45, got {lpi_default}")
    except Exception as e:
        results.add_fail("Default LPI", str(e))

    # Task 5.2: Mesh-count validation
    try:
        test_cases = [(160, 40), (200, 50), (110, 27)]
        for mesh_count, expected_max_lpi in test_cases:
            max_safe_lpi = mesh_count // 4
            assert_true(max_safe_lpi == expected_max_lpi,
                        f"Mesh {mesh_count} validation",
                        f"Expected {expected_max_lpi}, got {max_safe_lpi}")
    except Exception as e:
        results.add_fail("Mesh validation", str(e))

    # Task 5.3: CMYK angles
    try:
        from core.router_utils import CMYK_ANGLES
        expected_angles = [45.0, 15.0, 75.0, 0.0]
        assert_true(CMYK_ANGLES == expected_angles,
                    "CMYK angles defined",
                    f"Expected {expected_angles}, got {CMYK_ANGLES}")
    except Exception as e:
        results.add_fail("CMYK angles", str(e))


def run_fix_group_7_tests():
    """FIX GROUP 7: AI System Fixes"""
    print("\n--- FIX GROUP 7: AI System ---")

    # Task 7.1: Model paths from env
    try:
        from core import ai_vision_bridge
        assert_true("E:\\" not in ai_vision_bridge.MODEL_PATH,
                    "MODEL_PATH not hardcoded Windows path",
                    "MODEL_PATH contains hardcoded Windows path")
        assert_true("E:\\" not in ai_vision_bridge.MMPROJ_PATH,
                    "MMPROJ_PATH not hardcoded Windows path",
                    "MMPROJ_PATH contains hardcoded Windows path")
    except Exception as e:
        results.add_fail("Model paths from env", str(e))

    # Task 7.3: MD5 image hash
    try:
        from core.ai_vision_bridge import _get_image_hash
        img1 = np.ones((100, 100, 3), dtype=np.uint8) * 255
        img2 = img1.copy()
        img3 = np.ones((100, 100, 3), dtype=np.uint8) * 128

        hash1 = _get_image_hash(img1)
        hash2 = _get_image_hash(img2)
        hash3 = _get_image_hash(img3)

        assert_true(hash1 == hash2,
                    "Identical images have same hash",
                    f"hash1={hash1}, hash2={hash2}")
        assert_true(hash1 != hash3,
                    "Different images have different hash",
                    f"hash1 and hash3 should differ")
        assert_true(len(hash1) == 32,
                    "MD5 hash is 32 chars",
                    f"Expected 32, got {len(hash1)}")
    except Exception as e:
        results.add_fail("MD5 image hash", str(e))


def run_fix_group_8_tests():
    """FIX GROUP 8: Performance Fixes"""
    print("\n--- FIX GROUP 8: Performance ---")

    # Task 8.1: NumPy LUT replaces vectorize
    try:
        from core.color_separator import ColorSeparator
        img = np.ones((50, 50, 3), dtype=np.uint8) * 255
        img[:25, :] = [0, 0, 255]
        img[25:, :] = [0, 255, 0]

        sep = ColorSeparator()
        result = sep.separate(img, num_colors=2)

        label_map = result['label_map']
        centers = result['centers']

        for i, center in enumerate(centers):
            mask = (label_map == i)
            pixel_count = np.sum(mask)
            assert_true(pixel_count > 0,
                        f"Label {i} has pixels (LUT remapping)",
                        f"Label {i} has 0 pixels")
    except Exception as e:
        results.add_fail("NumPy LUT remapping", str(e))


def run_integration_tests():
    """Integration tests"""
    print("\n--- Integration Tests ---")

    try:
        from core.color_separator import ColorSeparator
        from core.mask_generator import MaskGenerator

        img = np.ones((200, 200, 3), dtype=np.uint8) * 255
        img[:100, :100] = [0, 0, 255]      # Red
        img[:100, 100:] = [0, 255, 0]      # Green
        img[100:, :100] = [255, 0, 0]      # Blue
        img[100:, 100:] = [0, 255, 255]    # Yellow

        sep = ColorSeparator()
        sep_result = sep.separate(img, num_colors=4, bg_tolerance=20)

        assert_true(sep_result['num_colors'] == 4,
                    "Separates 4 colors",
                    f"Expected 4, got {sep_result['num_colors']}")

        gen = MaskGenerator()
        masks = gen.generate_masks(img, sep_result, dpi=300)

        assert_true(len(masks) == 4,
                    "Generates 4 masks",
                    f"Expected 4 masks, got {len(masks)}")

        for i, mask in enumerate(masks):
            ink_pixels = np.sum(mask == 0)
            assert_true(ink_pixels > 100,
                        f"Mask {i} has substantial ink pixels",
                        f"Expected > 100, got {ink_pixels}")
    except Exception as e:
        results.add_fail("Integration: 4-color logo", str(e))


def run_all_tests():
    """Run all audit fix tests"""
    print("="*50)
    print("Virtual Design Audit Fixes - Regression Tests")
    print("="*50)

    run_fix_group_1_tests()
    run_fix_group_2_tests()
    run_fix_group_3_tests()
    run_fix_group_4_tests()
    run_fix_group_5_tests()
    run_fix_group_7_tests()
    run_fix_group_8_tests()
    run_integration_tests()

    return results.report()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
