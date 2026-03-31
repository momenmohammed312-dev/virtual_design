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

    def __init__(self, dpi: int = 300, radius_gain: float = 1.0, curve_type: str = "linear"):
        self.dpi = dpi
        self.radius_gain = radius_gain  # Dot gain radius multiplier (1.0 = no gain, >1.0 = gain)
        self.curve_type = curve_type    # Gain curve: "linear", "exponential", "logarithmic", "sigmoid"

    def _apply_dot_gain_curve(self, intensity: float) -> float:
        """
        RIP-grade dot gain compensation with midtone weighting.
        intensity: 0.0 (black) to 1.0 (white)
        Returns: calibrated intensity for print production
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
                
                # RIP-grade tone mapping (not radius scaling)
                compensated_intensity = self._apply_dot_gain_curve(intensity)
                
                # Calculate radius based on compensated tone (preserve shape)
                radius = (1.0 - compensated_intensity) * (dot_spacing / 2.0) * 0.95
                
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
        dpi: int = None,
        gamma: float = 1.6,
    ) -> np.ndarray:
        """Generate halftone as binary numpy array. Angle is now properly applied."""
        print(f"      📊 Halftone raster (LPI:{lpi}, angle:{angle}°, {dot_shape})")
        gray = self._to_gray(image)
        
        # Apply gamma correction if provided
        if gamma != 1.0:
            gray = np.power(gray.astype(np.float32) / 255.0, 1.0 / gamma) * 255.0
            gray = gray.astype(np.uint8)
        
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
                cv2.circle(out, (cx, cy), r, 255, -1, lineType=cv2.LINE_AA)
        return out
