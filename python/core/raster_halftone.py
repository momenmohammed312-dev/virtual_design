"""
raster_halftone.py — Phase 6: AM Raster Halftone Engine
Amplitude Modulation screening at 600–2400 DPI output.

Pipeline:
    1. Grayscale input
    2. Rotate image plane by screen angle θ
    3. Apply periodic sinusoidal/clustered-dot threshold matrix
    4. Dot gain compensation (gamma)
    5. Output: high-DPI 1-bit bitmap (uint8 0/255)

Key Parameters:
    lpi   : Lines Per Inch  (typical: 45–85 for screen printing)
    dpi   : Device resolution (600, 1200, 2400)
    angle : Screen angle in degrees (0°, 15°, 45°, 75°)
    dot_fn: Dot shape function ('round', 'ellipse', 'euclidean', 'line')
"""

from __future__ import annotations
import cv2
import numpy as np
import math
import logging
from dataclasses import dataclass
from typing import Literal, Optional

logger = logging.getLogger(__name__)

DotFunction = Literal["round", "ellipse", "euclidean", "line"]


# ─── Config ──────────────────────────────────────────────────────────────────

@dataclass
class RasterHalftoneConfig:
    lpi:       int   = 55          # Lines Per Inch
    dpi:       int   = 1200        # Output device resolution
    angle:     float = 45.0        # Screen angle (degrees)
    dot_fn:    DotFunction = "round"
    gamma:     float = 1.6         # Dot gain compensation
    threshold: float = 0.5         # Hard threshold for final 1-bit output
    oversample: int  = 2           # Super-sampling factor (1=none, 2=2×)


# ─── Engine ──────────────────────────────────────────────────────────────────

class RasterHalftoneEngine:
    """
    AM Screening halftone engine for screen printing films.

    Produces a high-DPI binary bitmap where dot size ∝ local ink density.
    Output is strictly 0 (paper) / 255 (ink) for RIP compatibility.
    """

    def __init__(self, config: Optional[RasterHalftoneConfig] = None):
        self.cfg = config or RasterHalftoneConfig()

    def generate(self, grayscale: np.ndarray) -> np.ndarray:
        """
        Generate AM halftone bitmap.

        Args:
            grayscale: uint8 grayscale image (H×W) — NOT binary

        Returns:
            uint8 1-bit bitmap at cfg.dpi resolution (0=paper, 255=ink)
        """
        cfg = self.cfg

        if len(grayscale.shape) == 3:
            gray = cv2.cvtColor(grayscale, cv2.COLOR_BGR2GRAY)
        else:
            gray = grayscale.astype(np.uint8)

        # Up-sample to output DPI if input is low-res
        input_dpi_estimate = max(gray.shape)   # rough estimate
        if input_dpi_estimate < 300:
            scale = cfg.dpi / 96.0             # assume 96 dpi input
            if scale > 1.0:
                new_w = max(1, int(gray.shape[1] * scale))
                new_h = max(1, int(gray.shape[0] * scale))
                gray  = cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

        # Build threshold matrix
        screen_matrix = self._build_screen_matrix(gray.shape, cfg.dpi, cfg.lpi,
                                                   cfg.angle, cfg.dot_fn)

        # Apply gamma compensation to input (controls dot growth curve)
        if cfg.gamma != 1.0:
            lut = self._gamma_lut(cfg.gamma)
            gray_g = lut[gray]
        else:
            gray_g = gray

        # Threshold: ink where pixel < screen matrix threshold
        # (dark pixels -> big dots -> more ink)
        ink_float = 1.0 - (gray_g.astype(np.float32) / 255.0)
        screen_f  = screen_matrix.astype(np.float32) / 255.0
        bitmap    = (ink_float >= screen_f).astype(np.uint8) * 255

        logger.info(
            f"[RasterHalftone] lpi={cfg.lpi} dpi={cfg.dpi} "
            f"angle={cfg.angle}° fn={cfg.dot_fn} "
            f"coverage={100*np.mean(bitmap>0):.1f}%"
        )
        return bitmap

    # ─── Screen Matrix ────────────────────────────────────────────────────────

    def _build_screen_matrix(
        self,
        shape: tuple,
        dpi: int,
        lpi: int,
        angle: float,
        dot_fn: DotFunction,
    ) -> np.ndarray:
        """
        Build a periodic threshold matrix for AM screening.

        Each cell has one dot; the threshold varies from 0 (centre) to 255
        (edge), so pixels with high ink density (low gray value) exceed
        the threshold first -> larger dots.
        """
        h, w = shape[:2]
        dot_spacing = dpi / lpi       # pixels per half-tone cell

        angle_rad = math.radians(angle)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)

        # Build coordinate grid
        cx, cy = w / 2.0, h / 2.0
        xs = np.arange(w, dtype=np.float32) - cx
        ys = np.arange(h, dtype=np.float32) - cy
        XX, YY = np.meshgrid(xs, ys)

        # Rotate coordinates to screen angle
        Xr =  XX * cos_a + YY * sin_a
        Yr = -XX * sin_a + YY * cos_a

        # Normalised position within each cell  [-1, 1]
        Xc = (Xr % dot_spacing) / dot_spacing * 2 - 1   # [-1, 1]
        Yc = (Yr % dot_spacing) / dot_spacing * 2 - 1   # [-1, 1]

        # Dot function -> continuous threshold 0–1 (0=always ink, 1=never ink)
        screen = self._dot_function(Xc, Yc, dot_fn)

        # Scale to uint8 (0–255)
        screen_u8 = np.clip(screen * 255, 0, 255).astype(np.uint8)
        return screen_u8

    @staticmethod
    def _dot_function(Xc: np.ndarray, Yc: np.ndarray, fn: DotFunction) -> np.ndarray:
        """Compute dot threshold value [0,1] for each grid position."""
        if fn == "round":
            # Euclidean distance from cell centre -> circular dots
            r = np.sqrt(Xc**2 + Yc**2) / math.sqrt(2)   # max=1 at corners
            return np.clip(r, 0, 1)

        elif fn == "ellipse":
            # Elliptical dot: wider in X than Y (good for midtone rendition)
            r = np.sqrt((Xc * 0.7)**2 + (Yc * 1.3)**2) / math.sqrt(2)
            return np.clip(r, 0, 1)

        elif fn == "euclidean":
            # Classic Euclidean clustered dot (Dürrer screen)
            r = np.sqrt(Xc**2 + Yc**2) / math.sqrt(2)
            # Shadow endpoint: merge dots at extreme density
            return np.clip(r * 1.15, 0, 1)

        elif fn == "line":
            # Horizontal line screen (good for fine detail reproduction)
            return np.abs(Yc)

        else:
            # Fallback: round
            return np.clip(np.sqrt(Xc**2 + Yc**2) / math.sqrt(2), 0, 1)

    # ─── Gamma LUT ────────────────────────────────────────────────────────────

    @staticmethod
    def _gamma_lut(gamma: float) -> np.ndarray:
        """Pre-computed uint8 gamma LUT: output = input^(1/gamma) * 255."""
        inv = 1.0 / gamma
        return np.array(
            [min(255, int((i / 255.0)**inv * 255 + 0.5)) for i in range(256)],
            dtype=np.uint8,
        )


# ─── Convenience ─────────────────────────────────────────────────────────────

def generate_raster_halftone(
    grayscale: np.ndarray,
    lpi: int = 55,
    dpi: int = 1200,
    angle: float = 45.0,
    dot_fn: DotFunction = "round",
    gamma: float = 1.6,
) -> np.ndarray:
    """
    Quick helper to generate a raster halftone bitmap.

    Args:
        grayscale: uint8 grayscale channel (NOT binary)
        lpi:       Lines Per Inch
        dpi:       Output device DPI (600/1200/2400)
        angle:     Screen angle in degrees
        dot_fn:    Dot shape function
        gamma:     Dot gain compensation factor

    Returns:
        uint8 1-bit bitmap (0=paper, 255=ink)
    """
    cfg = RasterHalftoneConfig(
        lpi=lpi, dpi=dpi, angle=angle, dot_fn=dot_fn, gamma=gamma
    )
    return RasterHalftoneEngine(cfg).generate(grayscale)
