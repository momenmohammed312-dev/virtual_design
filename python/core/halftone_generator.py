import cv2
import math
import numpy as np
import logging
from typing import List, Literal, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class HalftoneDot:
    cx: float
    cy: float
    radius: float
    shape: str  # 'circle' | 'square'


class HalftoneGenerator:
    """Generate halftone patterns for screen printing
    FIX GROUP 10.1: Merged dot-gain compensation curves from root-level halftone_generator.py
    """

    def __init__(self, dpi: int = 300, radius_gain: float = 1.0, curve_type: str = "linear"):
        """Initialize halftone generator
        Args:
            dpi: Output DPI
            radius_gain: Dot gain radius multiplier (1.0 = no gain, >1.0 = gain)
            curve_type: Gain curve type - "linear", "exponential", "logarithmic", "sigmoid"
        """
        self.dpi = dpi
        self.radius_gain = radius_gain
        self.curve_type = curve_type

    def _apply_dot_gain_curve(self, intensity: float) -> float:
        """
        FIX GROUP 10.1: RIP-grade dot gain compensation with midtone weighting.
        Merged from root-level halftone_generator.py.

        Args:
            intensity: 0.0 (black) to 1.0 (white)

        Returns:
            calibrated intensity for print production
        """
        # Base curve compensation
        if self.curve_type == "linear":
            base_compensation = intensity
        elif self.curve_type == "exponential":
            # More gain in shadows
            base_compensation = intensity ** (1.0 / self.radius_gain)
        elif self.curve_type == "logarithmic":
            # More gain in highlights
            if intensity <= 0.01:
                base_compensation = 0.01
            else:
                base_compensation = 1.0 - math.log(intensity) / math.log(0.01) * (self.radius_gain - 1.0)
        elif self.curve_type == "sigmoid":
            # S-curve for smooth transitions
            steepness = 6.0 / self.radius_gain
            center = 0.5
            base_compensation = 1.0 / (1.0 + math.exp(-steepness * (intensity - center)))
        else:
            base_compensation = intensity

        # RIP-grade midtone weighting (critical insight)
        # Dot gain is highest in midtones (40-60%), apply stronger correction there
        midtone_center = 0.5
        midtone_range = 0.3  # 30% range around center (35%-65%)

        # Calculate distance from midtone center
        distance_from_midtone = abs(intensity - midtone_center)

        # Midtone weighting: stronger correction closer to 50%
        if distance_from_midtone <= midtone_range:
            # Weight increases as we get closer to midtone
            midtone_weight = 1.0 - (distance_from_midtone / midtone_range)
            # Apply midtone boost based on radius_gain
            midtone_boost = 1.0 + midtone_weight * (self.radius_gain - 1.0) * 0.5

            # Blend base compensation with midtone-boosted version
            if intensity < 0.5:
                # Shadows: push darker (smaller intensity)
                final_intensity = base_compensation * (2.0 - midtone_boost) / 2.0
            else:
                # Highlights: push lighter (larger intensity)
                final_intensity = base_compensation * midtone_boost
        else:
            # Outside midtone range: use base compensation
            final_intensity = base_compensation

        # Clamp to valid range
        return max(0.0, min(1.0, final_intensity))

    # ─── VECTOR OUTPUT ───────────────────────────────────────────────────────

    def generate_vector_dots(
        self,
        image: np.ndarray,
        lpi: int = 45,  # FIX GROUP 5.1: Changed default from 85 to 45 (safe for 160-200 mesh)
        angle: float = 45.0,
        dot_shape: str = "circle",
        gamma: float = 1.6,
        dpi_override: Optional[int] = None,
    ) -> List[HalftoneDot]:
        """Vectorized Halftone Dot generation with gamma correction for professional screen printing."""
        gray = self._to_gray(image)
        h, w = gray.shape
        
        # FIX A-02: Use effective DPI (if downscaled) to calculate pixel-space spacing.
        dpi_to_use = dpi_override if dpi_override is not None else self.dpi
        dot_spacing = dpi_to_use / lpi
        
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

        if gamma != 1.0:
            intensities = np.power(intensities, 1.0 / gamma)

        # LPI-adaptive shadow gap (unchanged)
        shadow_gap = 0.90 - (lpi / 1000.0)
        shadow_gap = max(0.75, min(0.92, shadow_gap))
        
        # FIX A-14: Clamp radii to [0, dot_spacing*0.5] to prevent dot coalescence
        radii = np.clip(intensities, 0.0, 1.0) * dot_spacing * 0.5 * shadow_gap

        # 5. Build dot list
        # FIX A-15: Allow dots smaller than 1.0px to preserve highlight detail.
        # They will be handled (or skipped if too small) during rasterization.
        dots = [
            HalftoneDot(cx=float(px[i]), cy=float(py[i]), radius=float(radii[i]), shape=dot_shape)
            for i in range(len(px))
            if radii[i] > 0.1  # Only skip almost-invisible dots
        ]
        
        return dots

    # ─── RASTER OUTPUT ───────────────────────────────────────────────────────

    def generate(
        self,
        image: np.ndarray,
        lpi: int = 45,  
        angle: float = 45.0,
        dot_shape: Literal["round", "square", "ellipse", "dither"] = "round",
        dpi: Optional[int] = None,
        gamma: float = 1.6,
        apply_clahe: bool = True,
        image_class: str = 'auto'  
    ) -> np.ndarray:
        """Generate halftone as binary numpy array."""
        gray = self._to_gray(image)
        
        # ⚡ 1. PERFORMANCE: Safety downscale for large images (>2400px)
        max_res = 2400
        effective_dpi = dpi if dpi is not None else self.dpi
        
        if max(gray.shape) > max_res:
            scale = max_res / max(gray.shape)
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
            # FIX A-02: Track effective DPI to maintain correct dot scaling.
            effective_dpi = int(effective_dpi * scale)
            logger.info(f"[Halftone] Downscaled: scale={scale:.3f}, effective_dpi={effective_dpi}")

        # FIX GROUP 5.4: Only apply CLAHE for photos
        if apply_clahe and image_class == 'photo':
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            gray = clahe.apply(gray)
            
        if dot_shape == "dither":
            return self.floyd_steinberg_dithering(gray)
            
        shape_map = {"round": "circle", "square": "square", "ellipse": "circle"}
        
        # Pass effective_dpi to generate_vector_dots
        dots = self.generate_vector_dots(gray, lpi=lpi, angle=angle,
                                         dot_shape=shape_map.get(dot_shape, "circle"),
                                         gamma=gamma,
                                         dpi_override=effective_dpi)
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
        """Correct pixel-by-pixel Floyd-Steinberg error diffusion."""
        img = gray.astype(np.float32) / 255.0
        h, w = img.shape

        for y in range(h - 1):
            for x in range(w):
                old_val = img[y, x]
                new_val = 1.0 if old_val >= 0.5 else 0.0
                img[y, x] = new_val
                err = old_val - new_val

                if x + 1 < w:
                    img[y,     x + 1] += err * 7 / 16
                if y + 1 < h:
                    if x - 1 >= 0:
                        img[y + 1, x - 1] += err * 3 / 16
                    img[y + 1, x    ] += err * 5 / 16
                    if x + 1 < w:
                        img[y + 1, x + 1] += err * 1 / 16

        img[-1] = np.clip(img[-1], 0.0, 1.0)
        img[-1] = (img[-1] >= 0.5).astype(np.float32)

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
            
            # FIX A-10: Remove minimum radius floor to allow small dots in highlights.
            r = int(round(dot.radius * scale))
            if r < 1:
                continue   # dot too small to render — correct behavior
                
            if dot.shape == "square":
                x1, y1 = max(0, cx - r), max(0, cy - r)
                x2, y2 = min(big.shape[1] - 1, cx + r), min(big.shape[0] - 1, cy + r)
                big[y1:y2 + 1, x1:x2 + 1] = 255
            else:
                cv2.circle(big, (cx, cy), r, 255, -1, cv2.LINE_AA)
        
        out = cv2.resize(big, (w, h), interpolation=cv2.INTER_AREA)
        _, out = cv2.threshold(out, 127, 255, cv2.THRESH_BINARY)
        return out
