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
    lpi:        int   = 85          # Lines Per Inch (higher = smaller dots)
    dpi:        int   = 1200        # Output device resolution
    angle:      float = 45.0        # Screen angle (degrees)
    dot_fn:     DotFunction = "round"
    gamma:      float = 1.6         # Dot gain compensation
    threshold:  float = 0.5         # Hard threshold for final 1-bit output
    oversample: int   = 2           # Super-sampling factor (1=none, 2=2×)
    # FIX A-04: Explicit source DPI for scaling decisions.
    # None = unknown (do NOT auto-upsample); set to actual source DPI when known.
    source_dpi: Optional[int] = None


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

        # FIX A-04: Only upsample when source DPI is explicitly known AND
        # is lower than the target DPI.
        if cfg.source_dpi is not None and cfg.source_dpi < cfg.dpi:
            scale = cfg.dpi / cfg.source_dpi
            new_w = max(1, int(gray.shape[1] * scale))
            new_h = max(1, int(gray.shape[0] * scale))
            gray  = cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
            logger.info(
                f"[RasterHalftone] Upsampled {gray.shape[1] // int(scale)}x"
                f"{gray.shape[0] // int(scale)} "
                f"@ {cfg.source_dpi} DPI → {new_w}x{new_h} @ {cfg.dpi} DPI"
            )

        # Apply noise suppression and cleaning to input grayscale
        gray_clean = cv2.medianBlur(gray, 3)

        # Apply gamma compensation to input (controls dot growth curve)
        if cfg.gamma != 1.0:
            lut = self._gamma_lut(cfg.gamma)
            gray_g = lut[gray_clean]
        else:
            gray_g = gray_clean

        # For large images at high DPI, use chunked processing to save memory
        h, w = gray_g.shape
        total_pixels = h * w
        max_pixels_per_chunk = 4 * 1024 * 1024  # ~4M pixels per chunk (~16MB for float32)

        if total_pixels > max_pixels_per_chunk:
            # Process in chunks
            logger.info(f"[RasterHalftone] Large image {w}x{h}, using chunked processing")
            bitmap = self._generate_chunked(gray_g, cfg)
        else:
            # Standard processing for smaller images
            bitmap = self._generate_standard(gray_g, cfg)

        coverage = 100 * np.mean(bitmap == 0)
        logger.info(
            f"[RasterHalftone] lpi={cfg.lpi} dpi={cfg.dpi} "
            f"angle={cfg.angle}° fn={cfg.dot_fn} "
            f"coverage={coverage:.1f}%"
        )

        # FIX: [Task 2c] Auto-boost if coverage too low
        if coverage < 3.0 and cfg.gamma > 0.8:
            logger.warning(f"[RasterHalftone] Coverage {coverage:.1f}% critically low — auto-retry with gamma={cfg.gamma - 0.4:.1f}")
            cfg_retry = RasterHalftoneConfig(
                lpi=cfg.lpi, dpi=cfg.dpi, angle=cfg.angle, dot_fn=cfg.dot_fn,
                gamma=max(0.8, cfg.gamma - 0.4), oversample=cfg.oversample,
                threshold=cfg.threshold,
                source_dpi=cfg.source_dpi
            )
            return RasterHalftoneEngine(cfg_retry).generate(grayscale)

        return bitmap

    # ─── Processing Methods ───────────────────────────────────────────────────

    def _generate_standard(self, gray_g: np.ndarray, cfg: RasterHalftoneConfig) -> np.ndarray:
        """Standard processing for smaller images (fits in memory)."""
        # Build threshold matrix
        screen_matrix = self._build_screen_matrix(gray_g.shape, cfg.dpi, cfg.lpi,
                                                   cfg.angle, cfg.dot_fn)
        return self._apply_threshold(gray_g, screen_matrix)

    def _generate_chunked(self, gray_g: np.ndarray, cfg: RasterHalftoneConfig) -> np.ndarray:
        """Chunked processing for large images to save memory."""
        h, w = gray_g.shape
        chunk_height = max(1, (4 * 1024 * 1024) // w)  # ~4M pixels per chunk

        # Ensure chunk height accounts for dot pattern periodicity
        dot_spacing = cfg.dpi / cfg.lpi
        chunk_height = max(chunk_height, int(dot_spacing * 4))  # At least 4 cells

        bitmap = np.zeros((h, w), dtype=np.uint8)

        for y_start in range(0, h, chunk_height):
            y_end = min(y_start + chunk_height, h)
            # Small overlap to prevent seams
            overlap = int(dot_spacing * 2) if y_start > 0 else 0
            y_chunk_start = max(0, y_start - overlap)
            y_chunk_end = min(h, y_end + overlap) if y_end < h else y_end

            # Process chunk
            chunk = gray_g[y_chunk_start:y_chunk_end, :]
            screen_matrix = self._build_screen_matrix(chunk.shape, cfg.dpi, cfg.lpi,
                                                       cfg.angle, cfg.dot_fn)
            chunk_bitmap = self._apply_threshold(chunk, screen_matrix)

            # Copy back (excluding overlap)
            copy_start = overlap if y_start > 0 else 0
            copy_end = copy_start + (y_end - y_start)
            bitmap[y_start:y_end, :] = chunk_bitmap[copy_start:copy_end, :]

        return bitmap

    def _apply_threshold(self, gray_g: np.ndarray, screen_matrix: np.ndarray) -> np.ndarray:
        """Apply halftone thresholding to grayscale image."""
        # Intensity clamping: Task A-14 Fix (Prevent 'shredding' in typography)
        gray_f = gray_g.astype(np.float32) / 255.0

        # PRO-PRESS CLAMP: If area is nearly solid black (ink > 88%), force to 100% solid
        gray_f[gray_f < 0.12] = 0.0

        # Highlight Clamp: Ignore stray dots in very light areas
        gray_f[gray_f > 0.97] = 1.0

        # Threshold: ink where pixel < screen matrix threshold
        ink_float = 1.0 - gray_f
        screen_f = screen_matrix.astype(np.float32) / 255.0

        # Invert so ink=0 (black), background=255 (white/transparent)
        bitmap = (ink_float >= screen_f).astype(np.uint8) * 255
        bitmap = cv2.bitwise_not(bitmap)  # 255->0 (ink), 0->255 (bg)

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
        """
        h, w = shape[:2]
        dot_spacing = dpi / lpi       # pixels per half-tone cell

        angle_rad = math.radians(angle)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)

        # Build coordinate grid using float32 for memory efficiency at high DPI (4800+)
        # float32 provides sufficient precision and uses half the memory of float64
        cx, cy = w / 2.0, h / 2.0
        xs = np.arange(w, dtype=np.float32) - cx
        ys = np.arange(h, dtype=np.float32) - cy
        XX, YY = np.meshgrid(xs, ys, copy=False)

        # Rotate coordinates with safe offset to fix 'vertical aliasing' artifacts
        # Adding 1e-7 ensures our periodic signal doesn't jitter on exact floating point boundaries
        Xr = (XX * cos_a + YY * sin_a) + 1e-7
        Yr = (-XX * sin_a + YY * cos_a) + 1e-7

        # Normalised position within each cell [-1, 1]
        Xc = (Xr % dot_spacing) / dot_spacing * 2 - 1
        Yc = (Yr % dot_spacing) / dot_spacing * 2 - 1

        # Dot function -> continuous threshold 0–1 (0=always ink, 1=never ink)
        screen = self._dot_function(Xc, Yc, dot_fn)

        # Scale to uint8 (0–255)
        screen_u8 = np.clip(screen * 255, 0, 255).astype(np.uint8)
        return screen_u8

    @staticmethod
    def _dot_function(Xc: np.ndarray, Yc: np.ndarray, fn: DotFunction) -> np.ndarray:
        """Compute dot threshold value [0,1] for each grid position."""
        if fn == "round":
            r = np.sqrt(Xc**2 + Yc**2) / math.sqrt(2)
            return np.clip(r, 0, 1)

        elif fn == "ellipse":
            r = np.sqrt((Xc * 0.7)**2 + (Yc * 1.3)**2) / math.sqrt(2)
            return np.clip(r, 0, 1)

        elif fn == "euclidean":
            r = np.sqrt(Xc**2 + Yc**2) / math.sqrt(2)
            return np.clip(r * 1.15, 0, 1)

        elif fn == "line":
            return np.abs(Yc)

        else:
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
    lpi: int = 85,
    dpi: int = 1200,
    angle: float = 45.0,
    dot_fn: DotFunction = "round",
    gamma: float = 1.6,
) -> np.ndarray:
    """
    Quick helper to generate a raster halftone bitmap.
    """
    cfg = RasterHalftoneConfig(
        lpi=lpi, dpi=dpi, angle=angle, dot_fn=dot_fn, gamma=gamma
    )
    return RasterHalftoneEngine(cfg).generate(grayscale)
