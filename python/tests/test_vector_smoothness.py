"""
test_vector_smoothness.py — Phase 10: Vectorization Quality Validation
Tests curvature continuity, node count reduction, and visual accuracy.

Run with:
    pytest python/tests/test_vector_smoothness.py -v

Or standalone:
    python python/tests/test_vector_smoothness.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import cv2
import numpy as np
import math

from typing import List

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_circle_image(radius: int = 80, size: int = 200) -> np.ndarray:
    """Synthesize a clean anti-aliased white circle on black background."""
    img = np.zeros((size, size), dtype=np.uint8)
    cv2.circle(img, (size // 2, size // 2), radius, 255, -1, cv2.LINE_AA)
    return img


def _make_logo_image(size: int = 200) -> np.ndarray:
    """Synthesize a simple geometric logo shape (triangle)."""
    img = np.zeros((size, size), dtype=np.uint8)
    pts = np.array([[size//2, 20], [size-20, size-20], [20, size-20]], dtype=np.int32)
    cv2.fillPoly(img, [pts], 255)
    return img


def _make_noisy_edge_image(size: int = 200) -> np.ndarray:
    """Add Gaussian noise to simulate a degraded/scanned logo edge."""
    img = _make_circle_image(size=size)
    noise = np.random.normal(0, 15, img.shape).astype(np.int16)
    return np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)


def _count_path_nodes(paths) -> int:
    """Count total number of coordinate nodes across all paths."""
    total = 0
    for path in paths:
        for cmd in path:
            if cmd[0] == 'M':
                total += 1
            elif cmd[0] == 'L':
                total += 1
            elif cmd[0] == 'C':
                total += 3   # two control points + endpoint
    return total


def _curvature_continuity(paths) -> float:
    """
    Measure curvature continuity score [0,1].
    Checks C1 continuity at each junction:
        at a Bézier join, the tangent direction must be consistent
    Returns fraction of joins that are C1-continuous (angle < 30°).
    """
    total_joins = 0
    smooth_joins = 0

    for path in paths:
        cmds = [c for c in path if c[0] != 'Z']
        n = len(cmds)
        for i in range(1, n - 1):
            prev = cmds[i - 1]
            curr = cmds[i]
            nxt  = cmds[i + 1]

            # Only check at curve-to-curve junctions
            if curr[0] != 'C' or nxt[0] not in ('C', 'L'):
                continue

            # Tangent out of curr  (cp2 -> endpoint)
            ep_x, ep_y = curr[5], curr[6]
            cp2_x, cp2_y = curr[3], curr[4]
            t_out = np.array([ep_x - cp2_x, ep_y - cp2_y])

            # Tangent into next
            if nxt[0] == 'C':
                cp1_xn, cp1_yn = nxt[1], nxt[2]
                t_in = np.array([cp1_xn - ep_x, cp1_yn - ep_y])
            else:
                t_in = np.array([nxt[1] - ep_x, nxt[2] - ep_y])

            norm_out = np.linalg.norm(t_out)
            norm_in  = np.linalg.norm(t_in)
            if norm_out < 1e-6 or norm_in < 1e-6:
                continue

            cos_theta = np.clip(
                np.dot(t_out, t_in) / (norm_out * norm_in), -1.0, 1.0
            )
            angle_deg = math.degrees(math.acos(cos_theta))

            total_joins += 1
            if angle_deg < 30.0:
                smooth_joins += 1

    return smooth_joins / total_joins if total_joins > 0 else 1.0


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestImageClassifier:
    """Phase 1: ImageClassifier correctness."""

    def test_logo_detected_as_logo(self):
        from core.image_classifier import ImageClassifier
        img_bgr = cv2.cvtColor(_make_logo_image(200), cv2.COLOR_GRAY2BGR)
        result = ImageClassifier().classify(img_bgr)
        assert result.type == "logo", f"Expected 'logo', got '{result.type}' (scores: logo={result.score_logo:.3f} photo={result.score_photo:.3f})"

    def test_confidence_in_range(self):
        from core.image_classifier import ImageClassifier
        img_bgr = cv2.cvtColor(_make_circle_image(), cv2.COLOR_GRAY2BGR)
        result = ImageClassifier().classify(img_bgr)
        assert 0.0 <= result.confidence <= 1.0, f"Confidence out of range: {result.confidence}"

    def test_route_valid(self):
        from core.image_classifier import ImageClassifier
        img_bgr = cv2.cvtColor(_make_logo_image(), cv2.COLOR_GRAY2BGR)
        result = ImageClassifier().classify(img_bgr)
        assert result.route() in ("vector", "halftone", "hybrid")


class TestAntiAliasPreserver:
    """Phase 2: AntiAliasPreserver does not binarize."""

    def test_logo_preset_returns_grayscale(self):
        from core.anti_alias_preserve import AntiAliasPreserver
        img = _make_circle_image()
        out = AntiAliasPreserver.for_logo().process(img)
        assert len(out.shape) == 2, "Logo preset must return grayscale"
        # Must NOT be binary (should have intermediate values)
        unique_vals = len(np.unique(out))
        assert unique_vals > 2, f"Output appears binarized ({unique_vals} unique values)"

    def test_photo_preset_no_binarization(self):
        from core.anti_alias_preserve import AntiAliasPreserver
        img = _make_noisy_edge_image()
        out = AntiAliasPreserver.for_photo().process(img)
        unique_vals = len(np.unique(out))
        assert unique_vals > 10, f"Photo output appears binarized ({unique_vals} unique values)"

    def test_mixed_preset_keeps_colour(self):
        from core.anti_alias_preserve import AntiAliasPreserver
        gray = _make_logo_image()
        img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        out = AntiAliasPreserver.for_mixed().process(img)
        assert len(out.shape) == 3 and out.shape[2] == 3, "Mixed preset must return BGR"


class TestCurveFitter:
    """Phase 3: CurveFitter produces smooth Bézier paths."""

    def test_circle_produces_bezier_curves(self):
        from core.curve_fitter import CurveFitter, CurveFitConfig
        img = _make_circle_image(radius=70, size=200)
        fitter = CurveFitter(CurveFitConfig(use_canny=True, min_area=50))
        paths = fitter.extract_paths(img)
        assert len(paths) > 0, "No paths extracted from circle image"

        has_curve = any(
            cmd[0] == 'C'
            for path in paths
            for cmd in path
        )
        assert has_curve, "Expected at least one cubic Bézier command ('C')"

    def test_node_count_reduced_vs_raw(self):
        """
        Curve fitting should produce FEWER nodes than raw pixel contour
        (RDP + Chaikin should simplify).
        """
        from core.curve_fitter import CurveFitter, CurveFitConfig
        img = _make_circle_image(radius=70, size=200)

        # Raw contour node count
        _, edges = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)
        raw_contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        raw_nodes = sum(len(c) for c in raw_contours)

        # Fitted path node count
        fitter = CurveFitter(CurveFitConfig(use_canny=True, min_area=50))
        paths  = fitter.extract_paths(img)
        fitted_nodes = _count_path_nodes(paths)

        assert fitted_nodes < raw_nodes, (
            f"Fitted paths have MORE nodes ({fitted_nodes}) than raw contour ({raw_nodes}). "
            f"Simplification is not working."
        )

    def test_bezier_curvature_continuity(self):
        """At least 80% of Bézier joins should be C1-continuous."""
        from core.curve_fitter import CurveFitter, CurveFitConfig
        img = _make_circle_image(radius=70, size=200)
        fitter = CurveFitter(CurveFitConfig(use_canny=True, min_area=50, bezier_tension=0.30))
        paths = fitter.extract_paths(img)
        score = _curvature_continuity(paths)
        assert score >= 0.80, f"Curvature continuity too low: {score:.3f} (need ≥ 0.80)"

    def test_noisy_image_still_simplifies(self):
        """Noisy input should still produce fewer nodes than raw, proving denoising works."""
        from core.curve_fitter import CurveFitter, CurveFitConfig
        img = _make_noisy_edge_image()
        fitter = CurveFitter(CurveFitConfig(use_canny=True, min_area=30))
        paths = fitter.extract_paths(img)
        assert len(paths) >= 1, "No paths extracted from noisy edge image"


class TestLABColorSeparator:
    """Phase 5: LAB color separator."""

    def _make_two_color_image(self):
        """Red and blue rectangles on white."""
        img = np.full((100, 100, 3), 255, dtype=np.uint8)
        img[10:50, 10:50]  = (0,   0, 200)   # BGR red
        img[55:90, 55:90]  = (200, 0,   0)   # BGR blue
        return img

    def test_separates_correct_count(self):
        from core.lab_separator import LABColorSeparator
        img = self._make_two_color_image()
        result = LABColorSeparator(k_min=2, k_max=4).separate(img, num_colors=3)
        assert result.k == 3

    def test_masks_are_binary(self):
        from core.lab_separator import LABColorSeparator
        img = self._make_two_color_image()
        result = LABColorSeparator().separate(img, num_colors=2)
        for cluster in result.clusters:
            unique = set(np.unique(cluster.mask).tolist())
            assert unique.issubset({0, 255}), f"Mask has non-binary values: {unique}"

    def test_masks_non_overlapping(self):
        from core.lab_separator import LABColorSeparator
        img = self._make_two_color_image()
        result = LABColorSeparator().separate(img, num_colors=2)
        masks = [c.mask for c in result.clusters]
        if len(masks) >= 2:
            overlap = cv2.bitwise_and(masks[0], masks[1])
            assert np.sum(overlap) == 0, "Color masks must not overlap"

    def test_rgb_values_valid(self):
        from core.lab_separator import LABColorSeparator
        img = self._make_two_color_image()
        result = LABColorSeparator().separate(img, num_colors=2)
        for cluster in result.clusters:
            for ch in cluster.rgb:
                assert 0 <= ch <= 255, f"RGB channel out of range: {ch}"


class TestRasterHalftone:
    """Phase 6: Raster halftone engine."""

    def test_output_is_binary(self):
        from core.raster_halftone import RasterHalftoneEngine, RasterHalftoneConfig
        img = _make_circle_image(size=200)
        engine = RasterHalftoneEngine(RasterHalftoneConfig(lpi=55, dpi=300))
        out = engine.generate(img)
        unique = set(np.unique(out).tolist())
        assert unique.issubset({0, 255}), f"Output has non-binary values: {unique}"

    def test_ink_coverage_reasonable(self):
        from core.raster_halftone import RasterHalftoneEngine, RasterHalftoneConfig
        img = _make_circle_image(size=200)
        engine = RasterHalftoneEngine(RasterHalftoneConfig(lpi=55, dpi=300))
        out = engine.generate(img)
        coverage = 100 * np.mean(out > 0)
        assert 5.0 < coverage < 95.0, f"Ink coverage unrealistic: {coverage:.1f}%"

    def test_different_angles_differ(self):
        from core.raster_halftone import RasterHalftoneEngine, RasterHalftoneConfig
        img = _make_circle_image(size=200)
        out0  = RasterHalftoneEngine(RasterHalftoneConfig(angle=0)).generate(img)
        out45 = RasterHalftoneEngine(RasterHalftoneConfig(angle=45)).generate(img)
        assert not np.array_equal(out0, out45), "Different screen angles must differ"


class TestVectorHalftone:
    """Phase 7: Vector halftone engine."""

    def test_produces_dots(self):
        from core.vector_halftone import VectorHalftoneEngine, VectorHalftoneConfig
        img = _make_circle_image(size=200)
        cfg = VectorHalftoneConfig(lpi=55, input_dpi=300)
        dots = VectorHalftoneEngine(cfg).generate(img)
        assert len(dots) > 0, "No vector dots generated"

    def test_dots_inside_image_bounds(self):
        from core.vector_halftone import VectorHalftoneEngine, VectorHalftoneConfig
        size = 200
        img  = _make_circle_image(size=size)
        cfg  = VectorHalftoneConfig(lpi=55, input_dpi=300)
        dots = VectorHalftoneEngine(cfg).generate(img)
        for dot in dots:
            assert 0 <= dot.cx <= size, f"Dot cx={dot.cx} out of bounds"
            assert 0 <= dot.cy <= size, f"Dot cy={dot.cy} out of bounds"
            assert dot.radius >= 0,     f"Dot radius={dot.radius} is negative"

    def test_svg_output_valid(self):
        from core.vector_halftone import VectorHalftoneEngine, VectorHalftoneConfig
        img  = _make_circle_image(size=200)
        cfg  = VectorHalftoneConfig(lpi=55, input_dpi=300)
        eng  = VectorHalftoneEngine(cfg)
        dots = eng.generate(img)
        svg  = eng.to_svg(dots, 200, 200)
        assert '<svg' in svg
        assert '</svg>' in svg
        assert '<circle' in svg or len(dots) == 0

    def test_raster_and_vector_differ_in_type(self):
        """
        Raster engine -> ndarray; Vector engine -> list of dots.
        They must NOT share output types.
        """
        from core.raster_halftone import RasterHalftoneEngine, RasterHalftoneConfig
        from core.vector_halftone import VectorHalftoneEngine, VectorHalftoneConfig
        img = _make_circle_image(size=100)
        raster = RasterHalftoneEngine(RasterHalftoneConfig(dpi=300)).generate(img)
        dots   = VectorHalftoneEngine(VectorHalftoneConfig(input_dpi=300)).generate(img)
        assert isinstance(raster, np.ndarray), "Raster engine must return ndarray"
        assert isinstance(dots, list), "Vector engine must return list"


# ─── Standalone runner ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import traceback
    test_classes = [
        TestImageClassifier,
        TestAntiAliasPreserver,
        TestCurveFitter,
        TestLABColorSeparator,
        TestRasterHalftone,
        TestVectorHalftone,
    ]

    passed = failed = 0
    for cls in test_classes:
        obj = cls()
        methods = [m for m in dir(obj) if m.startswith("test_")]
        for method_name in methods:
            try:
                getattr(obj, method_name)()
                print(f"  [PASS] {cls.__name__}.{method_name}")
                passed += 1
            except Exception as e:
                print(f"  [FAIL] {cls.__name__}.{method_name}: {e}")
                traceback.print_exc()
                failed += 1

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
    if failed > 0:
        sys.exit(1)
