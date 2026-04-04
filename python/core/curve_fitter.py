"""
curve_fitter.py — Phase 3: True Curve Reconstruction
Feature-first vectorization:  grayscale -> edge detect -> contour -> Bézier

Pipeline:
    A) Gaussian pre-blur (subpixel edge stabilization)
    B) Canny edge detection on GRAYSCALE (not binary!)
    C) cv2.findContours on edge map
    D) Ramer-Douglas-Peucker simplification (adaptive ε)
    E) Chaikin corner-cutting (2 iterations)
    F) Cubic Bézier fitting (Potrace-style)

The result is a list of SVG-style path commands (M/L/C/Z) that can be
fed directly into vector_exporter.py or saved as SVG elements.
"""

from __future__ import annotations
import cv2
import numpy as np
import math
import logging
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


# ─── Types ───────────────────────────────────────────────────────────────────

PathCommand = Tuple  # ('M', x, y) | ('L', x, y) | ('C', cx1,cy1,cx2,cy2,x,y) | ('Z',)
ContourPath = List[PathCommand]


# ─── Config ──────────────────────────────────────────────────────────────────

@dataclass
class CurveFitConfig:
    # Canny thresholds (used on the grayscale image)
    canny_low:  int   = 50
    canny_high: int   = 150

    # Adaptive RDP epsilon multipliers (scaled by perimeter)
    rdp_factor_small:  float = 0.012   # area < 200 px²
    rdp_factor_medium: float = 0.018   # area 200–1000 px²
    rdp_factor_large:  float = 0.022   # area > 1000 px²

    # Minimum epsilon floor (px)
    rdp_min_epsilon: float = 1.5

    # Chaikin iterations (0 = disabled)
    chaikin_iterations: int = 2

    # Corner detection threshold (degrees)
    corner_threshold: float = 110.0

    # Bézier control-point tension (Catmull-Rom smooth factor)
    bezier_tension: float = 0.30

    # Minimum contour area to keep (filters noise)
    min_area: int = 30

    # If True, work on Canny edges; if False, work on existing binary mask
    use_canny: bool = True


# ─── Main fitter ─────────────────────────────────────────────────────────────

class CurveFitter:
    """
    Converts a grayscale image (or binary mask) into smooth Bézier paths.

    This replaces the old binary-contour-to-polyline approach with a true
    curve-reconstruction pipeline.
    """

    def __init__(self, config: Optional[CurveFitConfig] = None):
        self.cfg = config or CurveFitConfig()

    # ─── Public API ────────────────────────────────────────────────────────────

    def extract_paths(self, image: np.ndarray) -> List[ContourPath]:
        """
        Full pipeline: image -> smooth Bézier paths.

        Args:
            image: uint8 grayscale or BGR image

        Returns:
            List of path command lists (M/L/C/Z tuples)
        """
        cfg = self.cfg

        # A) Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.astype(np.uint8)

        # B) Edge map (Canny on grayscale — NOT on binary)
        if cfg.use_canny:
            blurred = cv2.GaussianBlur(gray, (3, 3), 0.8)
            edge_map = cv2.Canny(blurred, cfg.canny_low, cfg.canny_high)
        else:
            # Already binary mask -> invert so ink=255, background=0
            _, edge_map = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)

        # C) Find contours on edge map
        contours, _ = cv2.findContours(
            edge_map, cv2.RETR_TREE, cv2.CHAIN_APPROX_TC89_L1
        )

        paths: List[ContourPath] = []
        for contour in contours:
            area = abs(cv2.contourArea(contour))
            if area < cfg.min_area:
                continue

            path = self._contour_to_bezier(contour)
            if path:
                paths.append(path)

        logger.debug(
            f"[CurveFitter] {len(contours)} contours -> "
            f"{len(paths)} valid paths (min_area={cfg.min_area})"
        )
        return paths

    # ─── Pipeline Stages ──────────────────────────────────────────────────────

    def _contour_to_bezier(self, contour: np.ndarray) -> ContourPath:
        """
        Convert one OpenCV contour to a Bézier path.
        Stages: RDP -> Chaikin -> Bézier fitting
        """
        pts = contour.reshape(-1, 2).astype(float)
        if len(pts) < 3:
            return []

        # D) Ramer-Douglas-Peucker simplification
        pts = self._rdp_simplify(contour, pts)
        if len(pts) < 3:
            return []

        # E) Chaikin corner-cutting
        for _ in range(self.cfg.chaikin_iterations):
            pts = self._chaikin(pts, closed=True)
        if len(pts) < 3:
            return []

        # F) Bézier fitting
        return self._pts_to_bezier(pts)

    # ─── D) Adaptive RDP ────────────────────────────────────────────────────────

    def _rdp_simplify(self, contour: np.ndarray, pts: np.ndarray) -> np.ndarray:
        """Apply adaptive Ramer-Douglas-Peucker simplification."""
        cfg = self.cfg
        perimeter = cv2.arcLength(contour, True)
        area = abs(cv2.contourArea(contour))

        if area < 200:
            factor = cfg.rdp_factor_small
        elif area < 1000:
            factor = cfg.rdp_factor_medium
        else:
            factor = cfg.rdp_factor_large

        epsilon = max(cfg.rdp_min_epsilon, perimeter * factor)
        simplified = cv2.approxPolyDP(contour, epsilon, True)
        return simplified.reshape(-1, 2).astype(float)

    # ─── E) Chaikin Corner-Cutting ───────────────────────────────────────────────

    @staticmethod
    def _chaikin(pts: np.ndarray, closed: bool = True) -> np.ndarray:
        """
        One pass of Chaikin's algorithm:
            new points at 1/4 and 3/4 of each edge.

        This creates a smooth B-spline approximation of the input polygon
        without any corner overshoot.
        """
        n = len(pts)
        if n < 3:
            return pts

        out = []
        for i in range(n):
            p0 = pts[i]
            p1 = pts[(i + 1) % n]
            q = 0.75 * p0 + 0.25 * p1
            r = 0.25 * p0 + 0.75 * p1
            out.append(q)
            out.append(r)

        return np.array(out)

    # ─── F) Cubic Bézier Fitting ─────────────────────────────────────────────────

    def _pts_to_bezier(self, pts: np.ndarray) -> ContourPath:
        """
        Convert a smooth polygon to cubic Bézier curves.

        Uses Catmull-Rom -> Cubic Bézier conversion:
            CP1 = P1 + (P2 - P0) * tension
            CP2 = P2 - (P3 - P1) * tension

        Corner detection is used to break the spline at sharp turns
        (these are emitted as line segments instead).
        """
        cfg = self.cfg
        n = len(pts)
        tension = cfg.bezier_tension

        # Detect corners via signed curvature
        corners = set()
        for i in range(n):
            a = self._signed_angle(
                pts[(i - 1) % n],
                pts[i],
                pts[(i + 1) % n]
            )
            if abs(a) > (180.0 - cfg.corner_threshold):
                corners.add(i)

        commands: ContourPath = [('M', float(pts[0][0]), float(pts[0][1]))]

        for i in range(n):
            p0 = pts[(i - 1) % n]
            p1 = pts[i]
            p2 = pts[(i + 1) % n]
            p3 = pts[(i + 2) % n]

            is_corner = (i in corners) or ((i + 1) % n in corners)
            sf = 0.0 if is_corner else tension

            if sf == 0.0:
                commands.append(('L', float(p2[0]), float(p2[1])))
            else:
                # Catmull-Rom control points
                cp1x = p1[0] + (p2[0] - p0[0]) * sf
                cp1y = p1[1] + (p2[1] - p0[1]) * sf
                cp2x = p2[0] - (p3[0] - p1[0]) * sf
                cp2y = p2[1] - (p3[1] - p1[1]) * sf
                commands.append((
                    'C',
                    float(cp1x), float(cp1y),
                    float(cp2x), float(cp2y),
                    float(p2[0]), float(p2[1])
                ))

        commands.append(('Z',))
        return commands

    # ─── Helpers ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _signed_angle(p0: np.ndarray, p1: np.ndarray, p2: np.ndarray) -> float:
        """Signed turning angle at p1 (degrees). Negative = left turn."""
        v1 = p1 - p0
        v2 = p2 - p1
        cross = float(v1[0] * v2[1] - v1[1] * v2[0])
        dot   = float(v1[0] * v2[0] + v1[1] * v2[1])
        return math.degrees(math.atan2(cross, dot))


# ─── Convenience function ────────────────────────────────────────────────────

def fit_curves(
    image: np.ndarray,
    use_canny: bool = True,
    tension: float = 0.30,
    min_area: int = 30,
) -> List[ContourPath]:
    """
    Quick path extraction with sane defaults.

    Args:
        image:     Grayscale or BGR image
        use_canny: True = run Canny on grayscale input (feature-first)
                   False = treat image as binary mask
        tension:   Bézier curve smoothness (0=no curve, 0.5=maximum)
        min_area:  Minimum contour area to keep (px²)

    Returns:
        List of path command lists
    """
    cfg = CurveFitConfig(
        use_canny=use_canny,
        bezier_tension=tension,
        min_area=min_area,
    )
    return CurveFitter(cfg).extract_paths(image)
