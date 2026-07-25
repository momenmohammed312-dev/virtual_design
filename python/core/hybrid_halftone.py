"""
hybrid_halftone.py — Hybrid Vector + Raster Halftone Engine
Virtual Design Silk Screen Studio

Combines the precision of vector halftone for sharp edges with the smoothness
of raster halftone for gradients. This is optimal for screen printing artwork
that contains both fine details and photographic areas.

Pipeline:
    1. Edge Detection — Identify sharp edges and corners
    2. Region Segmentation — Separate edge regions from smooth regions
    3. Vector Halftone — Small precise dots (0.1-0.3mm) for edge areas
    4. Raster Halftone — Variable dots for smooth gradient areas
    5. Compositing — Merge both with proper anti-aliasing
"""

from __future__ import annotations
import cv2
import numpy as np
import math
import logging
from dataclasses import dataclass
from typing import List, Tuple, Optional, Literal
from core.raster_halftone import RasterHalftoneEngine, RasterHalftoneConfig
from core.vector_halftone import VectorHalftoneEngine, VectorHalftoneConfig

logger = logging.getLogger(__name__)


@dataclass
class HybridHalftoneConfig:
    """Configuration for hybrid halftone processing."""
    # Common settings
    lpi: int = 85
    dpi: int = 1200
    angle: float = 45.0
    dot_shape: str = "round"
    gamma: float = 1.6
    
    # Edge detection parameters
    edge_threshold_low: int = 50
    edge_threshold_high: int = 150
    edge_dilation_radius: int = 3  # Pixels to expand edge region
    
    # Vector halftone settings (for edges)
    vector_dot_min_radius: float = 0.1  # mm
    vector_dot_max_radius: float = 0.3  # mm
    vector_shadow_gap: float = 0.95
    
    # Raster halftone settings (for gradients)
    raster_oversample: int = 2
    
    # Blending
    blend_feather: int = 2  # Pixels of feather at region boundaries
    
    # Greyscale output for preview (dots are greyscale 0-255, not binary)
    greyscale_output: bool = False  # True = greyscale dots, False = binary (for films)
    
    # FIX: [DPI Scaling] Source DPI for upsampling
    source_dpi: Optional[int] = None

    # Dot sizing (matches RasterHalftoneConfig behavior)
    dot_size_multiplier: float = 1.0


class HybridHalftoneEngine:
    """
    Hybrid halftone engine combining vector and raster approaches.
    
    Strategy:
    - Sharp edges → Vector dots (precise, no pixelation)
    - Smooth gradients → Raster dots (continuous tone)
    - Transition zones → Blended composite
    """
    
    def __init__(self, config: Optional[HybridHalftoneConfig] = None):
        self.cfg = config or HybridHalftoneConfig()
        self.raster_engine = None
        self.vector_engine = None
    
    def generate(self, grayscale: np.ndarray) -> np.ndarray:
        """
        Generate hybrid halftone from grayscale image.
        
        Args:
            grayscale: uint8 grayscale image (0-255)
            
        Returns:
            uint8 binary bitmap (0=ink, 255=background)
        """
        try:
            h, w = grayscale.shape[:2]
            logger.info(f"[HybridHalftone] Starting: {w}x{h} @ {self.cfg.dpi} DPI, {self.cfg.lpi} LPI")
            
            # FIX A-04: Upscale input image to target DPI if needed
            current_dpi = self.cfg.source_dpi if self.cfg.source_dpi is not None and self.cfg.source_dpi > 0 else 300
            if current_dpi < self.cfg.dpi:
                scale = self.cfg.dpi / current_dpi
                new_w = max(1, int(grayscale.shape[1] * scale))
                new_h = max(1, int(grayscale.shape[0] * scale))
                grayscale = cv2.resize(grayscale, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
                h, w = grayscale.shape[:2]
                logger.info(f"[HybridHalftone] Upsampled {grayscale.shape[1] // int(scale)}x{grayscale.shape[0] // int(scale)} @ {current_dpi} DPI -> {w}x{h} @ {self.cfg.dpi} DPI")
            
            # Step 1: Edge Detection
            edge_mask = self._detect_edges(grayscale)
            edge_ratio = np.mean(edge_mask > 0)
            logger.info(f"[HybridHalftone] Edge ratio: {edge_ratio:.1%}")
            
            # Step 2: Region Segmentation
            smooth_mask = 255 - edge_mask
            
            # Step 3: Raster Halftone (for smooth areas)
            raster_result = self._generate_raster(grayscale, smooth_mask)
            
            # Step 4: Vector Halftone (for edge areas)  
            vector_dots = self._generate_vector_dots(grayscale, edge_mask)
            vector_result = self._rasterize_dots(vector_dots, (h, w))
            
            # Step 5: Composite with feathering
            final_result = self._composite(
                raster_result, vector_result, 
                smooth_mask, edge_mask
            )
            
            # Calculate coverage based on output type
            if self.cfg.greyscale_output:
                coverage = 100 * np.mean((255 - final_result) / 255.0)
            else:
                coverage = 100 * np.mean(final_result < 128)
            
            output_type = "GREYSCALE" if self.cfg.greyscale_output else "BINARY"
            logger.info(f"[HybridHalftone] {output_type} Final coverage: {coverage:.1f}%")
            
            return final_result
        except Exception as e:
            logger.error(f"[HybridHalftone] ❌ ERROR in generate: {e}")
            import traceback
            logger.error(f"[HybridHalftone] Traceback: {traceback.format_exc()}")
            # Fallback: return grayscale as-is (will be handled by caller)
            raise  # Re-raise to let caller handle it
    
    def _detect_edges(self, gray: np.ndarray) -> np.ndarray:
        """
        Detect sharp edges using Canny + dilation.
        Returns binary mask (255=edge, 0=smooth)
        """
        # Canny edge detection
        edges = cv2.Canny(
            gray, 
            self.cfg.edge_threshold_low,
            self.cfg.edge_threshold_high
        )
        
        # Dilate to create edge region
        if self.cfg.edge_dilation_radius > 0:
            kernel = cv2.getStructuringElement(
                cv2.MORPH_ELLIPSE, 
                (self.cfg.edge_dilation_radius * 2 + 1,) * 2
            )
            edges = cv2.dilate(edges, kernel, iterations=1)
        
        return edges
    
    def _generate_raster(self, gray: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Generate raster halftone for smooth regions."""
        dot_mult = getattr(self.cfg, 'dot_size_multiplier', None)
        if dot_mult is None:
            dot_mult = 1.0
        cfg = RasterHalftoneConfig(
            lpi=self.cfg.lpi,
            dpi=self.cfg.dpi,
            angle=self.cfg.angle,
            dot_fn=self.cfg.dot_shape,
            gamma=self.cfg.gamma,
            oversample=self.cfg.raster_oversample,
            greyscale_output=self.cfg.greyscale_output,
            source_dpi=self.cfg.dpi,  # Image is already upsampled to target DPI
            dot_size_multiplier=float(dot_mult),
        )
        
        engine = RasterHalftoneEngine(cfg)
        
        # Apply mask to grayscale (set masked areas to white/background)
        masked_gray = gray.copy()
        masked_gray[mask < 128] = 255  # Non-smooth areas = white
        
        result = engine.generate(masked_gray)
        
        # Force non-smooth areas to white in result
        result[mask < 128] = 255
        
        return result
    
    def _generate_vector_dots(
        self, 
        gray: np.ndarray, 
        edge_mask: np.ndarray
    ) -> List[Tuple[float, float, float]]:
        """
        Generate vector dots for edge regions.
        Returns list of (x, y, radius) tuples.
        """
        h, w = gray.shape
        dots = []
        
        # Calculate dot spacing from LPI
        dot_spacing = self.cfg.dpi / self.cfg.lpi
        r_max = dot_spacing * 0.5 * self.cfg.vector_shadow_gap
        r_min = self.cfg.vector_dot_min_radius * self.cfg.dpi / 25.4  # mm to px
        
        # Grid sampling at edge regions
        angle_rad = math.radians(self.cfg.angle)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        
        # Sample points on rotated grid
        diag = math.sqrt(w * w + h * h)
        n = int(math.ceil(diag / dot_spacing)) + 2
        
        cx0, cy0 = w / 2.0, h / 2.0
        
        for i in range(-n, n + 1):
            for j in range(-n, n + 1):
                # Grid position
                gx = i * dot_spacing
                gy = j * dot_spacing
                
                # Rotate to image space
                px = cx0 + gx * cos_a - gy * sin_a
                py = cy0 + gx * sin_a + gy * cos_a
                
                # Skip if outside image
                if px < 0 or px >= w or py < 0 or py >= h:
                    continue
                
                # Check if in edge region
                px_i, py_i = int(px), int(py)
                if edge_mask[py_i, px_i] < 128:
                    continue  # Not in edge region
                
                # Sample intensity
                intensity = gray[py_i, px_i] / 255.0
                ink = 1.0 - intensity
                
                # Apply gamma
                if self.cfg.gamma != 1.0:
                    ink = math.pow(ink, 1.0 / self.cfg.gamma)
                
                # Calculate radius (clamped)
                radius = max(r_min, min(r_max * math.sqrt(ink), r_max))
                
                if radius > r_min:
                    dots.append((float(px), float(py), float(radius)))
        
        logger.info(f"[HybridHalftone] Vector dots: {len(dots)}")
        return dots
    
    def _rasterize_dots(
        self, 
        dots: List[Tuple[float, float, float]], 
        shape: Tuple[int, int]
    ) -> np.ndarray:
        """Rasterize vector dots to bitmap."""
        h, w = shape
        
        # Upsample for anti-aliasing
        scale = 2
        big = np.zeros((h * scale, w * scale), dtype=np.uint8)
        
        # Calculate max radius for normalization
        if dots:
            max_r = max(d[2] for d in dots) if self.cfg.greyscale_output else 0
        else:
            max_r = 0
        
        for x, y, r in dots:
            cx = int(x * scale)
            cy = int(y * scale)
            radius = int(r * scale)
            
            if radius < 1:
                continue
            
            # GREYSCALE: Dot intensity based on radius (larger dot = darker)
            if self.cfg.greyscale_output and max_r > 0:
                intensity = min(255, int(50 + (r / max_r) * 205))  # 50-255 range
            else:
                intensity = 255  # Binary: full intensity
            
            if self.cfg.dot_shape == "square":
                x1 = max(0, cx - radius)
                y1 = max(0, cy - radius)
                x2 = min(big.shape[1] - 1, cx + radius)
                y2 = min(big.shape[0] - 1, cy + radius)
                big[y1:y2 + 1, x1:x2 + 1] = intensity
            else:
                cv2.circle(big, (cx, cy), radius, intensity, -1, cv2.LINE_AA)
        
        # Downsample
        result = cv2.resize(big, (w, h), interpolation=cv2.INTER_AREA)
        
        if self.cfg.greyscale_output:
            # GREYSCALE: Keep anti-aliased result (0-255)
            return result
        else:
            # BINARY: Threshold to 0/255 for films
            _, binary = cv2.threshold(result, 127, 255, cv2.THRESH_BINARY)
            return binary
    
    def _composite(
        self,
        raster: np.ndarray,
        vector: np.ndarray,
        smooth_mask: np.ndarray,
        edge_mask: np.ndarray
    ) -> np.ndarray:
        """
        Composite raster and vector results with feathering.
        """
        # Create feathered blend mask
        if self.cfg.blend_feather > 0:
            # Blur the masks for smooth transition
            smooth_blur = cv2.GaussianBlur(
                smooth_mask.astype(np.float32) / 255.0,
                (self.cfg.blend_feather * 2 + 1,) * 2,
                0
            )
            edge_blur = cv2.GaussianBlur(
                edge_mask.astype(np.float32) / 255.0,
                (self.cfg.blend_feather * 2 + 1,) * 2,
                0
            )
            
            # Normalize weights
            total = smooth_blur + edge_blur + 1e-6
            smooth_weight = smooth_blur / total
            edge_weight = edge_blur / total
            
            # Blend
            result = (
                raster.astype(np.float32) * smooth_weight +
                vector.astype(np.float32) * edge_weight
            ).astype(np.uint8)
            
            if not self.cfg.greyscale_output:
                # BINARY: Threshold to 0/255 for films
                _, result = cv2.threshold(result, 127, 255, cv2.THRESH_BINARY)
            # GREYSCALE: Keep blended result (0-255)
        else:
            # Hard composite (no feathering)
            result = raster.copy()
            result[edge_mask > 128] = vector[edge_mask > 128]
        
        return result


def apply_hybrid_halftone(
    grayscale: np.ndarray,
    lpi: int = 85,
    dpi: int = 1200,
    angle: float = 45.0,
    dot_shape: str = "round",
    gamma: float = 1.6
) -> np.ndarray:
    """
    Convenience function for hybrid halftone generation.
    """
    cfg = HybridHalftoneConfig(
        lpi=lpi,
        dpi=dpi,
        angle=angle,
        dot_shape=dot_shape,
        gamma=gamma
    )
    engine = HybridHalftoneEngine(cfg)
    return engine.generate(grayscale)
