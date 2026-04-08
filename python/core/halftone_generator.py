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
        lpi: int = 85,
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

        # 4. Map pixel intensities at these points
        ix = np.round(px).astype(int)
        iy = np.round(py).astype(int)
        ix = np.clip(ix, 0, w - 1)
        iy = np.clip(iy, 0, h - 1)
        
        norm = gray[iy, ix] / 255.0
        intensities = 1.0 - norm
        
        # Apply dot gain compensation
        try:
            from .print_job_config import PrintJobConfig
            job_config = PrintJobConfig()
            intensities = job_config.apply_dot_gain_compensation(intensities)
        except ImportError:
            pass 
        
        if gamma != 1.0:
            intensities = np.power(intensities, 1.0 / gamma)

        # TASK 16: LPI-adaptive shadow gap
        shadow_gap = 0.90 - (lpi / 1000.0)  
        shadow_gap = max(0.75, min(0.92, shadow_gap))
        radii = intensities * dot_spacing * 0.5 * shadow_gap

        # 5. Build dot list
        dots = [
            HalftoneDot(cx=float(px[i]), cy=float(py[i]), radius=float(radii[i]), shape=dot_shape)
            for i in range(len(px))
            if radii[i] >= 1.0  
        ]
        
        return dots

    # ─── RASTER OUTPUT ───────────────────────────────────────────────────────

    def generate(
        self,
        image: np.ndarray,
        lpi: int = 85,
        angle: float = 45.0,
        dot_shape: Literal["round", "square", "ellipse", "dither"] = "round",
        dpi: Optional[int] = None,
        gamma: float = 1.6,
        apply_clahe: bool = True
    ) -> np.ndarray:
        """Generate halftone as binary numpy array."""
        gray = self._to_gray(image)
        
        # ⚡ 1. PERFORMANCE: Safety downscale for large images (>2400px)
        # Prevents OOM while maintaining visual print quality (at 300dpi, 8" width = 2400px)
        max_res = 2400
        if max(gray.shape) > max_res:
            scale = max_res / max(gray.shape)
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
            logger.info(f"[Halftone] Downscaled large image to {gray.shape[1]}x{gray.shape[0]} for speed")

        if apply_clahe:
            # CLAHE helps photographs but can be noisy for artwork
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            gray = clahe.apply(gray)
            
        if dot_shape == "dither":
            return self.floyd_steinberg_dithering(gray)
            
        shape_map = {"round": "circle", "square": "square", "ellipse": "circle"}
        dots = self.generate_vector_dots(gray, lpi=lpi, angle=angle,
                                         dot_shape=shape_map.get(dot_shape, "circle"),
                                         gamma=gamma)
        return self._rasterize(dots, gray.shape)

    @staticmethod
    def evaluate_quality(img: np.ndarray) -> float:
        """🚀 Quality Score: Measures contrast and edge sharpness."""
        if len(img.shape) == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        contrast = img.std()
        edge_variance = cv2.Laplacian(img, cv2.CV_64F).var()
        score = (contrast * 0.4) + (edge_variance * 0.6)
        return score

    def floyd_steinberg_dithering(self, gray: np.ndarray) -> np.ndarray:
        """
        T05 FIX: Floyd-Steinberg error diffusion — numpy row-by-row.
        """
        img = gray.astype(np.float32) / 255.0
        h, w = img.shape
        for y in range(h - 1):
            row = img[y]
            quantized = (row > 0.5).astype(np.float32)
            err = row - quantized
            img[y] = quantized

            img[y,     1:]   += err[:-1] * (7 / 16)   
            img[y + 1, :-1]  += err[1:]  * (3 / 16)   
            img[y + 1, :]    += err      * (5 / 16)   
            img[y + 1, 1:]   += err[:-1] * (1 / 16)   

        img[-1] = (img[-1] > 0.5).astype(np.float32)
        return (np.clip(img, 0, 1) * 255).astype(np.uint8)

    @staticmethod
    def _to_gray(image: np.ndarray) -> np.ndarray:
        if len(image.shape) == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return image.copy()

    @staticmethod
    def _rasterize(dots: List[HalftoneDot], shape: tuple) -> np.ndarray:
        h, w = shape
        scale = 2  
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
                cv2.circle(big, (cx, cy), r, 255, -1, cv2.LINE_AA)
        
        out = cv2.resize(big, (w, h), interpolation=cv2.INTER_AREA)
        _, out = cv2.threshold(out, 127, 255, cv2.THRESH_BINARY)
        return out
