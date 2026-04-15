"""
anti_alias_preserve.py — Phase 2: Feature Preservation Preprocessing
Applies ONLY edge-preserving smoothing.
NO binarization here — that is deferred to the individual pipeline stages.

Pipeline:
    1. Convert to grayscale (if not already)
    2. Subpixel Gaussian smoothing (σ=0.8–1.2)
    3. Bilateral filtering  (optional, edge-preserving)
    4. Optional gamma pre-correction

Output is always uint8 grayscale (or BGR if colour preservation requested).
"""

from __future__ import annotations
import cv2
import numpy as np
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


# ─── Config ──────────────────────────────────────────────────────────────────

@dataclass
class AntiAliasConfig:
    """Tunable parameters for anti-alias preservation."""

    # Gaussian smoothing (subpixel)
    gaussian_sigma: float = 1.0          # σ=0.8 (sharp) … 1.2 (smooth)
    gaussian_ksize: int   = 3            # Must be odd; 3 is sufficient for σ≤1.2

    # Bilateral filter (edge-preserving denoise)
    use_bilateral:  bool  = True
    bilateral_d:    int   = 5            # Neighbourhood diameter
    bilateral_sigma_color: float = 50.0  # Colour range σ
    bilateral_sigma_space: float = 50.0  # Spatial σ

    # Gamma pre-correction
    use_gamma:    bool  = False
    gamma:        float = 1.0            # >1 brightens midtones before threshold

    # Output mode
    keep_color: bool = False             # True -> return BGR; False -> grayscale


# ─── Preprocessor ────────────────────────────────────────────────────────────

class AntiAliasPreserver:
    """
    Edge-preserving, anti-alias–safe preprocessing stage.

    DESIGN RULE:
        This class NEVER binarizes the image.
        It only smooths and optionally gamma-corrects
        so that downstream stages receive clean gradients.
    """

    def __init__(self, config: Optional[AntiAliasConfig] = None):
        self.config = config or AntiAliasConfig()

    # ─── Public API ────────────────────────────────────────────────────────────

    def process(self, image: np.ndarray) -> np.ndarray:
        """
        Apply edge-preserving preprocessing.

        Args:
            image: uint8 BGR or grayscale image

        Returns:
            Preprocessed image (uint8, same or reduced channels per config)
        """
        cfg = self.config

        # 1. Ensure uint8
        img = image.astype(np.uint8) if image.dtype != np.uint8 else image.copy()

        is_gray = (len(img.shape) == 2)

        # 2. Gamma correction (always in grayscale space for predictability)
        if cfg.use_gamma and cfg.gamma != 1.0:
            lut = self._make_gamma_lut(cfg.gamma)
            if is_gray:
                img = lut[img]
            else:
                # Apply gamma only to the luminance channel to avoid hue shift
                lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
                lab[:, :, 0] = lut[lab[:, :, 0]]
                img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        # 3. Edge-preserving smoothing
        if cfg.use_bilateral:
            # FIX A-01: Use actual bilateralFilter for moderate images.
            # Avoid the double-Gaussian stack which destroys strokes < 4px.
            if max(img.shape[:2]) <= 1500:
                img = cv2.bilateralFilter(
                    img,
                    cfg.bilateral_d,
                    cfg.bilateral_sigma_color,
                    cfg.bilateral_sigma_space
                )
            else:
                # For high-res, bilateral is too slow. Skip the extra blur
                # here because the main GaussianBlur below is sufficient.
                pass

        # 4. Subpixel Gaussian smoothing
        ksize = cfg.gaussian_ksize
        ksize = ksize if ksize % 2 == 1 else ksize + 1   # Ensure odd
        img = cv2.GaussianBlur(img, (ksize, ksize), cfg.gaussian_sigma)

        # 5. Output channel selection
        if cfg.keep_color and is_gray:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        elif not cfg.keep_color and not is_gray:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        logger.debug(
            f"[AntiAliasPreserver] shape={img.shape} "
            f"σ={cfg.gaussian_sigma} bilateral={cfg.use_bilateral} "
            f"gamma={cfg.gamma if cfg.use_gamma else 'off'}"
        )
        return img

    # ─── Named Presets ────────────────────────────────────────────────────────

    @classmethod
    def for_logo(cls) -> "AntiAliasPreserver":
        """Minimal smoothing to preserve sharp logo geometry."""
        return cls(AntiAliasConfig(
            gaussian_sigma=0.8,
            gaussian_ksize=3,
            use_bilateral=True,
            bilateral_d=5,
            bilateral_sigma_color=35.0,
            bilateral_sigma_space=35.0,
            use_gamma=False,
            keep_color=False,
        ))

    @classmethod
    def for_photo(cls) -> "AntiAliasPreserver":
        """Stronger smoothing + gamma for photographic gradients."""
        return cls(AntiAliasConfig(
            gaussian_sigma=1.2,
            gaussian_ksize=3,
            use_bilateral=True,
            bilateral_d=7,
            bilateral_sigma_color=75.0,
            bilateral_sigma_space=75.0,
            use_gamma=True,
            gamma=0.85,   # Slightly darken midtones for halftone contrast
            keep_color=False,
        ))

    @classmethod
    def for_mixed(cls) -> "AntiAliasPreserver":
        """Balanced preset for mixed artwork."""
        return cls(AntiAliasConfig(
            gaussian_sigma=1.0,
            gaussian_ksize=3,
            use_bilateral=True,
            bilateral_d=5,
            bilateral_sigma_color=50.0,
            bilateral_sigma_space=50.0,
            use_gamma=False,
            keep_color=True,  # Mixed keeps colour for later colour separation
        ))

    # ─── Helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _make_gamma_lut(gamma: float) -> np.ndarray:
        """Build uint8 LUT for gamma correction: out = in^(1/gamma) * 255."""
        inv_gamma = 1.0 / gamma
        table = np.array([
            min(255, int((i / 255.0) ** inv_gamma * 255 + 0.5))
            for i in range(256)
        ], dtype=np.uint8)
        return table


# ─── Convenience function ────────────────────────────────────────────────────

def preserve_anti_alias(
    image: np.ndarray,
    image_type: str = "mixed",   # "logo" | "photo" | "mixed"
) -> np.ndarray:
    """
    Quick helper: select the right preset based on classified image type
    and apply edge-preserving preprocessing.

    IMPORTANT: does NOT binarize. Use this BEFORE any threshold stage.
    """
    presets = {
        "logo":  AntiAliasPreserver.for_logo,
        "photo": AntiAliasPreserver.for_photo,
        "mixed": AntiAliasPreserver.for_mixed,
    }
    factory = presets.get(image_type, AntiAliasPreserver.for_mixed)
    return factory().process(image)
