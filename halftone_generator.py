import cv2
import math
import numpy as np
from typing import List, Literal, Tuple
from dataclasses import dataclass


@dataclass
class HalftoneDot:
    """Single halftone dot — pure data, no raster."""
    cx: float
    cy: float
    radius: float
    shape: str  # 'circle' | 'square'


class HalftoneGenerator:
    """Generate halftone patterns for screen printing."""

    def __init__(self, dpi: int = 300):
        self.dpi = dpi

    # ─── VECTOR OUTPUT ───────────────────────────────────────────────────────

    def generate_vector_dots(
        self,
        image: np.ndarray,
        lpi: int = 55,
        angle: float = 45.0,
        dot_shape: Literal["circle", "square"] = "circle",
    ) -> List[HalftoneDot]:
        """
        Generate halftone as list of HalftoneDot objects.
        NO raster intermediate — feed directly to PDFDocumentBuilder.
        Angle is ACTUALLY APPLIED via rotation matrix (was broken before).
        """
        gray = self._to_gray(image)
        h, w = gray.shape
        dot_spacing = self.dpi / lpi
        angle_rad = math.radians(angle)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        cx0, cy0 = w / 2.0, h / 2.0

        diag = math.ceil(math.sqrt(w * w + h * h))
        n = int(math.ceil(diag / dot_spacing)) + 2

        dots: List[HalftoneDot] = []
        for row in range(-n, n + 1):
            for col in range(-n, n + 1):
                gx = col * dot_spacing
                gy = row * dot_spacing
                px = cx0 + gx * cos_a - gy * sin_a
                py = cy0 + gx * sin_a + gy * cos_a

                if px < 0 or px >= w or py < 0 or py >= h:
                    continue

                ix = int(max(0, min(w - 1, round(px))))
                iy = int(max(0, min(h - 1, round(py))))
                intensity = gray[iy, ix] / 255.0
                radius = (1.0 - intensity) * (dot_spacing / 2.0) * 0.95
                if radius < 0.5:
                    continue

                dots.append(HalftoneDot(cx=px, cy=py, radius=radius, shape=dot_shape))

        return dots

    # ─── RASTER OUTPUT (backwards compat / PNG preview) ──────────────────────

    def generate(
        self,
        image: np.ndarray,
        lpi: int = 55,
        angle: float = 45.0,
        dot_shape: Literal["round", "square", "ellipse"] = "round",
    ) -> np.ndarray:
        """Generate halftone as binary numpy array. Angle is now properly applied."""
        print(f"      📊 Halftone raster (LPI:{lpi}, angle:{angle}°, {dot_shape})")
        gray = self._to_gray(image)
        shape_map = {"round": "circle", "square": "square", "ellipse": "circle"}
        dots = self.generate_vector_dots(gray, lpi=lpi, angle=angle,
                                         dot_shape=shape_map.get(dot_shape, "circle"))
        return self._rasterize(dots, gray.shape)

    def floyd_steinberg_dithering(self, gray: np.ndarray) -> np.ndarray:
        """Apply Floyd-Steinberg error diffusion dithering."""
        img = gray.astype(np.float32)
        h, w = img.shape
        for y in range(h):
            for x in range(w):
                old = img[y, x]
                new = 255.0 if old > 127.0 else 0.0
                img[y, x] = new
                err = old - new
                if x + 1 < w:
                    img[y, x + 1] += err * 7 / 16
                if y + 1 < h:
                    if x > 0:
                        img[y + 1, x - 1] += err * 3 / 16
                    img[y + 1, x] += err * 5 / 16
                    if x + 1 < w:
                        img[y + 1, x + 1] += err * 1 / 16
        return img.astype(np.uint8)

    # ─── HELPERS ─────────────────────────────────────────────────────────────

    @staticmethod
    def _to_gray(image: np.ndarray) -> np.ndarray:
        if len(image.shape) == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return image.copy()

    @staticmethod
    def _rasterize(dots: List[HalftoneDot], shape: Tuple[int, int]) -> np.ndarray:
        """Render dot list onto binary image — no anti-aliasing."""
        h, w = shape
        out = np.zeros((h, w), dtype=np.uint8)
        for dot in dots:
            cx = int(round(dot.cx))
            cy = int(round(dot.cy))
            r = max(1, int(round(dot.radius)))
            if dot.shape == "square":
                x1, y1 = max(0, cx - r), max(0, cy - r)
                x2, y2 = min(w - 1, cx + r), min(h - 1, cy + r)
                out[y1:y2 + 1, x1:x2 + 1] = 255
            else:
                cv2.circle(out, (cx, cy), r, 255, -1, lineType=cv2.LINE_8)
        return out
