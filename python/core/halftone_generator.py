import cv2
import math
import numpy as np
from typing import List, Literal, Optional
from dataclasses import dataclass


@dataclass
class HalftoneDot:
    cx: float
    cy: float
    radius: float
    shape: str  # 'circle' | 'square'


class HalftoneGenerator:
    """Generate halftone patterns for screen printing"""

    def __init__(self, dpi: int = 300):
        """Initialize halftone generator"""
        self.dpi = dpi

    # ─── VECTOR OUTPUT ───────────────────────────────────────────────────────

    def generate_vector_dots(
        self,
        image: np.ndarray,
        lpi: int = 55,
        angle: float = 45.0,
        dot_shape: str = "circle",
        gamma: float = 1.6,
    ) -> List[HalftoneDot]:
        """Vectorized Halftone Dot generation with gamma correction for professional screen printing."""
        gray = self._to_gray(image)
        h, w = gray.shape
        dot_spacing = self.dpi / lpi
        angle_rad = math.radians(angle)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        cx0, cy0 = w / 2.0, h / 2.0

        # Calculate bounding box in grid coordinate space
        diag = math.sqrt(w * w + h * h)
        n = int(math.ceil(diag / dot_spacing)) + 2

        # 1. Create a grid of points in rotated space
        mg_cols, mg_rows = np.meshgrid(np.arange(-n, n + 1), np.arange(-n, n + 1))
        gx = mg_cols.flatten() * dot_spacing
        gy = mg_rows.flatten() * dot_spacing

        # 2. Rotate grid points back to image space
        px = cx0 + gx * cos_a - gy * sin_a
        py = cy0 + gx * sin_a + gy * cos_a

        # 3. Filter points inside or near boundary
        mask = (px >= 0) & (px < w) & (py >= 0) & (py < h)
        px, py = px[mask], py[mask]

        if len(px) == 0:
            return []

        # 4. Map pixel intensities at these points (using nearest neighbor for speed)
        ix = np.round(px).astype(int)
        iy = np.round(py).astype(int)
        ix = np.clip(ix, 0, w - 1)
        iy = np.clip(iy, 0, h - 1)
        
        # Invert: dark areas (low gray) = big dots, light areas = small dots
        norm = gray[iy, ix] / 255.0
        intensities = 1.0 - norm
        
        # Gamma correction: controls dot growth curve
        if gamma != 1.0:
            intensities = np.power(intensities, 1.0 / gamma)

        # TASK 16: Shadow relief (15% gap)
        # 0.85 multiplier ensures dots do not touch neighbors at 100% intensity,
        # preventing ink bridging/flooding on the screen.
        radii = intensities * (dot_spacing / 2.0) * 0.85

        # 5. Build dot list
        dots = [
            HalftoneDot(cx=float(px[i]), cy=float(py[i]), radius=float(radii[i]), shape=dot_shape)
            for i in range(len(px))
            if radii[i] > 0.05  # Skip invisible dots
        ]
        
        return dots

    # ─── RASTER OUTPUT (backwards compat / PNG preview) ──────────────────────

    def generate(
        self,
        image: np.ndarray,
        lpi: int = 55,
        angle: float = 45.0,
        dot_shape: Literal["round", "square", "ellipse"] = "round",
        dpi: Optional[int] = None,
        gamma: float = 1.6,
    ) -> np.ndarray:
        """Generate halftone as binary numpy array. Gamma controls dot growth curve."""
        gray = self._to_gray(image)
        shape_map = {"round": "circle", "square": "square", "ellipse": "circle"}
        dots = self.generate_vector_dots(gray, lpi=lpi, angle=angle,
                                         dot_shape=shape_map.get(dot_shape, "circle"),
                                         gamma=gamma)
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
            if image.shape[2] == 3:
                return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            elif image.shape[2] == 4:
                # Handle RGBA images by converting to RGB first
                rgb = image[:, :, :3]
                return cv2.cvtColor(rgb, cv2.COLOR_BGR2GRAY)
        return image.copy() if len(image.shape) == 2 else image.mean(axis=2).astype(np.uint8)

    @staticmethod
    def _rasterize(dots: List[HalftoneDot], shape: tuple) -> np.ndarray:
        """Render dot list with super-sampling for smooth anti-aliased edges."""
        h, w = shape
        scale = 2  # 2x super-sampling
        
        # Draw on 2x canvas
        big = np.zeros((h * scale, w * scale), dtype=np.uint8)
        for dot in dots:
            cx = int(round(dot.cx * scale))
            cy = int(round(dot.cy * scale))
            r = max(scale, int(round(dot.radius * scale)))
            if dot.shape == "square":
                x1, y1 = max(0, cx - r), max(0, cy - r)
                x2, y2 = min(big.shape[1] - 1, cx + r), min(big.shape[0] - 1, cy + r)
                big[y1:y2 + 1, x1:x2 + 1] = 255
            else:
                cv2.circle(big, (cx, cy), r, 255, -1)  # LINE_8 on 2x canvas
        
        # Downscale with area averaging — produces natural anti-aliasing
        out = cv2.resize(big, (w, h), interpolation=cv2.INTER_AREA)
        return out
