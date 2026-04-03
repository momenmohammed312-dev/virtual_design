"""
vector_halftone.py — Phase 7: Procedural Vector Halftone Engine
Generates scalable SVG <circle> elements instead of a raster bitmap.

Pipeline:
    1. Sample image on LPI-derived grid
    2. Compute local intensity per cell
    3. Map intensity → dot radius (r = r_max * √intensity)
    4. Apply screen-angle rotation transform
    5. Output: list of SVG-compatible dot records OR inline SVG string

Advantages over raster halftone:
    ✓ Infinite scalability (no DPI limit)
    ✓ RIP-independent (clean PostScript path per dot)
    ✓ Clean print edges at any zoom level
"""

from __future__ import annotations
import cv2
import numpy as np
import math
import logging
from dataclasses import dataclass, field
from typing import List, Literal, Optional

logger = logging.getLogger(__name__)

DotShape = Literal["circle", "ellipse", "square", "line"]


# ─── Data Types ──────────────────────────────────────────────────────────────

@dataclass
class VectorDot:
    """A single halftone dot in image-space coordinates."""
    cx:     float          # Centre X (pixels)
    cy:     float          # Centre Y (pixels)
    radius: float          # Radius or half-size (pixels)
    shape:  DotShape = "circle"


@dataclass
class VectorHalftoneConfig:
    lpi:         int       = 55          # Lines Per Inch
    input_dpi:   int       = 300         # We need this to convert lpi→pixels
    angle:       float     = 45.0        # Screen angle (degrees)
    dot_shape:   DotShape  = "circle"
    gamma:       float     = 1.6         # Dot gain compensation
    shadow_gap:  float     = 0.90        # Max radius as fraction of half-cell
    min_radius:  float     = 0.8         # Minimum visible dot radius (px)
    invert:      bool      = True        # True: dark pixel → large dot


# ─── Engine ──────────────────────────────────────────────────────────────────

class VectorHalftoneEngine:
    """
    Procedural vector halftone: produces a list of VectorDot objects.

    Each dot maps to a scalable SVG primitive (circle / rect).
    The coordinate system is image-space pixels; callers scale to page units.
    """

    def __init__(self, config: Optional[VectorHalftoneConfig] = None):
        self.cfg = config or VectorHalftoneConfig()

    # ─── Public API ────────────────────────────────────────────────────────────

    def generate(self, grayscale: np.ndarray) -> List[VectorDot]:
        """
        Generate vector halftone dots for a grayscale channel.

        Args:
            grayscale: uint8 grayscale image (H×W) — NOT binary

        Returns:
            Ordered list of VectorDot objects
        """
        cfg = self.cfg

        if len(grayscale.shape) == 3:
            gray = cv2.cvtColor(grayscale, cv2.COLOR_BGR2GRAY)
        else:
            gray = grayscale.astype(np.uint8)

        h, w = gray.shape
        dot_spacing = cfg.input_dpi / cfg.lpi      # pixels per cell
        r_max       = dot_spacing * 0.5 * cfg.shadow_gap   # max dot radius

        angle_rad = math.radians(cfg.angle)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        cx0, cy0 = w / 2.0, h / 2.0

        # Number of grid cells to cover the image diagonal
        diag = math.sqrt(w * w + h * h)
        n    = int(math.ceil(diag / dot_spacing)) + 2

        # Build rotated grid
        cols = np.arange(-n, n + 1)
        rows = np.arange(-n, n + 1)
        mg_cols, mg_rows = np.meshgrid(cols, rows)
        gx = mg_cols.flatten() * dot_spacing
        gy = mg_rows.flatten() * dot_spacing

        # Rotate back to image space
        px = cx0 + gx * cos_a - gy * sin_a
        py = cy0 + gx * sin_a + gy * cos_a

        # Keep only dots inside the image bounds
        inside = (px >= 0) & (px < w) & (py >= 0) & (py < h)
        px, py = px[inside], py[inside]

        if len(px) == 0:
            return []

        # Sample pixel intensity at each grid point (nearest-neighbour)
        ix = np.clip(np.round(px).astype(int), 0, w - 1)
        iy = np.clip(np.round(py).astype(int), 0, h - 1)
        pixel_vals = gray[iy, ix].astype(np.float32) / 255.0

        # Ink fraction: dark pixel (low val) → large dot when invert=True
        if cfg.invert:
            ink = 1.0 - pixel_vals
        else:
            ink = pixel_vals

        # Dot gain compensation (gamma)
        if cfg.gamma != 1.0:
            ink = np.power(ink, 1.0 / cfg.gamma)

        # Dot radius: r = r_max * √(ink)  [industry formula]
        radii = r_max * np.sqrt(np.clip(ink, 0, 1))

        # Build dot list (filter sub-minimum dots)
        dots: List[VectorDot] = [
            VectorDot(
                cx=float(px[i]),
                cy=float(py[i]),
                radius=float(radii[i]),
                shape=cfg.dot_shape,
            )
            for i in range(len(px))
            if radii[i] >= cfg.min_radius
        ]

        logger.info(
            f"[VectorHalftone] lpi={cfg.lpi} angle={cfg.angle}° "
            f"dots={len(dots)} r_max={r_max:.1f}px"
        )
        return dots

    # ─── SVG Export ───────────────────────────────────────────────────────────

    def to_svg(
        self,
        dots: List[VectorDot],
        width_px: int,
        height_px: int,
        fill_color: str = "#000000",
        scale: float = 1.0,
    ) -> str:
        """
        Render dot list as an inline SVG string.

        Args:
            dots:       List of VectorDot from generate()
            width_px:   Image width in pixels (becomes SVG viewBox width)
            height_px:  Image height in pixels
            fill_color: Dot fill colour (hex)
            scale:      px-to-unit scale (1.0 = keep pixel units)

        Returns:
            SVG string (without XML declaration)
        """
        W = width_px  * scale
        H = height_px * scale
        lines = [
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{W:.2f}" height="{H:.2f}" '
            f'viewBox="0 0 {W:.2f} {H:.2f}">',
        ]

        for dot in dots:
            cx = dot.cx * scale
            cy = dot.cy * scale
            r  = dot.radius * scale

            if dot.shape == "circle":
                lines.append(
                    f'<circle cx="{cx:.3f}" cy="{cy:.3f}" r="{r:.3f}" '
                    f'fill="{fill_color}"/>'
                )
            elif dot.shape == "ellipse":
                rx = r * 0.8
                ry = r * 1.2
                lines.append(
                    f'<ellipse cx="{cx:.3f}" cy="{cy:.3f}" '
                    f'rx="{rx:.3f}" ry="{ry:.3f}" fill="{fill_color}"/>'
                )
            elif dot.shape == "square":
                x = cx - r
                y = cy - r
                s = r * 2
                lines.append(
                    f'<rect x="{x:.3f}" y="{y:.3f}" '
                    f'width="{s:.3f}" height="{s:.3f}" fill="{fill_color}"/>'
                )
            elif dot.shape == "line":
                lines.append(
                    f'<line x1="{cx-r:.3f}" y1="{cy:.3f}" '
                    f'x2="{cx+r:.3f}" y2="{cy:.3f}" '
                    f'stroke="{fill_color}" stroke-width="{r*0.6:.3f}"/>'
                )

        lines.append("</svg>")
        return "\n".join(lines)

    # ─── Rasterize for Preview ────────────────────────────────────────────────

    def rasterize(
        self,
        dots: List[VectorDot],
        width_px: int,
        height_px: int,
    ) -> np.ndarray:
        """Blit dots onto a uint8 canvas for preview / raster fallback."""
        canvas = np.zeros((height_px, width_px), dtype=np.uint8)
        for dot in dots:
            cx = int(round(dot.cx))
            cy = int(round(dot.cy))
            r  = max(1, int(round(dot.radius)))
            if dot.shape == "circle":
                cv2.circle(canvas, (cx, cy), r, 255, -1, cv2.LINE_AA)
            elif dot.shape == "ellipse":
                cv2.ellipse(canvas, (cx, cy), (max(1, int(r*0.8)), max(1, int(r*1.2))),
                            0, 0, 360, 255, -1)
            elif dot.shape == "square":
                x1 = max(0,          cx - r)
                y1 = max(0,          cy - r)
                x2 = min(width_px-1, cx + r)
                y2 = min(height_px-1,cy + r)
                canvas[y1:y2+1, x1:x2+1] = 255
            elif dot.shape == "line":
                cv2.line(canvas, (cx - r, cy), (cx + r, cy), 255,
                         max(1, int(r * 0.6)))
        return canvas


# ─── Convenience ─────────────────────────────────────────────────────────────

def generate_vector_halftone(
    grayscale: np.ndarray,
    lpi: int = 55,
    input_dpi: int = 300,
    angle: float = 45.0,
    dot_shape: DotShape = "circle",
    gamma: float = 1.6,
) -> List[VectorDot]:
    """
    Quick helper: grayscale image → list of VectorDot objects.

    Note: This module is SEPARATE from raster_halftone.py.
    They share only: grayscale input channel + LPI/angle config.
    """
    cfg = VectorHalftoneConfig(
        lpi=lpi,
        input_dpi=input_dpi,
        angle=angle,
        dot_shape=dot_shape,
        gamma=gamma,
    )
    return VectorHalftoneEngine(cfg).generate(grayscale)
