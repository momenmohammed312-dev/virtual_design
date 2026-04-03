"""
image_classifier.py — Phase 1: Smart Image Classification Layer
Provides intent classification BEFORE any destructive preprocessing.

Outputs:
    {
        "type": "logo" | "photo" | "mixed",
        "confidence": float,
        "metrics": { ... }
    }

Routing rules:
    logo  → vector pipeline   (no early binarization)
    photo → halftone pipeline
    mixed → hybrid            (vector for shapes + halftone overlay)
"""

from __future__ import annotations
import cv2
import numpy as np
import logging
from dataclasses import dataclass, field
from typing import Literal, Dict

logger = logging.getLogger(__name__)

# ─── Data Types ──────────────────────────────────────────────────────────────

ImageType = Literal["logo", "photo", "mixed"]


@dataclass
class ClassificationResult:
    """Structured output from ImageClassifier."""
    type: ImageType
    confidence: float                  # 0.0–1.0  (winner – runner_up gap)
    metrics: Dict[str, float] = field(default_factory=dict)

    # Raw scores for routing transparency
    score_logo: float = 0.0
    score_photo: float = 0.0
    score_mixed: float = 0.0

    def is_logo(self) -> bool:
        return self.type == "logo"

    def is_photo(self) -> bool:
        return self.type == "photo"

    def is_mixed(self) -> bool:
        return self.type == "mixed"

    def route(self) -> str:
        """Return pipeline name for routing."""
        return {
            "logo":  "vector",
            "photo": "halftone",
            "mixed": "hybrid",
        }[self.type]


# ─── Classifier ──────────────────────────────────────────────────────────────

class ImageClassifier:
    """
    Feature-first image classifier.

    Analyzes three independent signal types and combines them via soft scoring:

    1. Edge Density     — Canny edge map + HoG histogram spread
    2. Color Variance   — per-channel std-dev + LAB saturation spread
    3. Shannon Entropy  — pixel-level information density

    No binarization is applied here.  The classifier only READS the image.
    """

    # Analysis resolution cap (speed + stability)
    _ANA_W: int = 384
    _ANA_H: int = 384

    def classify(self, image: np.ndarray) -> ClassificationResult:
        """
        Classify image intent without any destructive preprocessing.

        Args:
            image: Input image in BGR uint8 (H×W×3 or H×W grayscale)

        Returns:
            ClassificationResult with type, confidence, and raw metrics
        """
        metrics = self._extract_metrics(image)
        scores  = self._score(metrics)

        types     = ["logo", "photo", "mixed"]
        score_vec = [scores["logo"], scores["photo"], scores["mixed"]]

        best_idx    = int(np.argmax(score_vec))
        winner_type = types[best_idx]

        sorted_scores = sorted(score_vec, reverse=True)
        confidence = float(sorted_scores[0] - sorted_scores[1])

        result = ClassificationResult(
            type=winner_type,
            confidence=round(confidence, 4),
            metrics=metrics,
            score_logo=round(scores["logo"],  4),
            score_photo=round(scores["photo"], 4),
            score_mixed=round(scores["mixed"], 4),
        )

        logger.info(
            f"[ImageClassifier] → {winner_type.upper()} "
            f"(conf={confidence:.3f}  "
            f"logo={scores['logo']:.3f} "
            f"photo={scores['photo']:.3f} "
            f"mixed={scores['mixed']:.3f})"
        )
        logger.debug(f"[ImageClassifier] metrics={metrics}")

        return result

    # ─── Feature Extraction ───────────────────────────────────────────────────

    def _extract_metrics(self, image: np.ndarray) -> Dict[str, float]:
        """Compute all features on a downscaled analysis copy."""
        ana = self._downscale(image)

        if len(ana.shape) == 2:
            gray = ana
            bgr  = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        else:
            bgr  = ana
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

        h, w = gray.shape
        N    = float(h * w)

        # ── 1. Edge Density (Canny) ───────────────────────────────────────────
        # Apply gentle Gaussian pre-blur to stabilise Canny on noisy inputs
        blurred   = cv2.GaussianBlur(gray, (3, 3), 0.8)
        edges     = cv2.Canny(blurred, 50, 150)
        edge_px   = float(np.count_nonzero(edges))
        edge_density = edge_px / N

        # ── 2. HoG Gradient Spread ────────────────────────────────────────────
        # High spread → many different edge directions → photo/mixed
        # Low spread  → few dominant directions      → logo
        sobelx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        angles = np.arctan2(sobely, sobelx)          # [-π, π]
        angle_hist, _ = np.histogram(angles[edges > 0], bins=18, range=(-np.pi, np.pi))
        angle_hist    = angle_hist.astype(np.float32)
        if angle_hist.sum() > 0:
            angle_hist /= angle_hist.sum()
        gradient_spread = float(np.std(angle_hist))   # Low → uniform → logo

        # ── 3. Color Variance ─────────────────────────────────────────────────
        b, g, r = cv2.split(bgr.astype(np.float32))
        color_variance = float(np.mean([np.std(b), np.std(g), np.std(r)]))

        # ── 4. LAB Saturation Spread ──────────────────────────────────────────
        lab   = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
        a_ch  = lab[:, :, 1].astype(np.float32) - 128.0
        b_ch  = lab[:, :, 2].astype(np.float32) - 128.0
        chroma = np.sqrt(a_ch**2 + b_ch**2)
        sat_mean  = float(np.mean(chroma))
        sat_std   = float(np.std(chroma))

        # ── 5. Shannon Entropy ────────────────────────────────────────────────
        # High entropy → complex texture → photo
        # Low entropy  → flat regions   → logo
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
        hist = hist / (hist.sum() + 1e-9)
        hist = hist[hist > 0]
        entropy = float(-np.sum(hist * np.log2(hist)))   # bits, max ~8

        # ── 6. Bimodality Index (logo heuristic) ─────────────────────────────
        # A strong bimodal histogram (near-black + near-white) is the hallmark
        # of a logo / text artwork.
        dark_px  = float(np.sum(gray < 64))  / N
        light_px = float(np.sum(gray > 192)) / N
        mid_px   = 1.0 - dark_px - light_px
        bimodal  = dark_px + light_px          # High → logo

        # ── 7. Unique color count estimate (fast) ────────────────────────────
        tiny = cv2.resize(bgr, (64, 64), interpolation=cv2.INTER_AREA)
        unique_colors = float(len(np.unique(tiny.reshape(-1, 3), axis=0)))
        unique_norm   = min(1.0, unique_colors / 512.0)   # 512 arbitrary ceiling

        return {
            "edge_density":     round(edge_density,    5),
            "gradient_spread":  round(gradient_spread, 5),
            "color_variance":   round(color_variance,  3),
            "sat_mean":         round(sat_mean,         3),
            "sat_std":          round(sat_std,           3),
            "entropy":          round(entropy,           4),
            "bimodal":          round(bimodal,           4),
            "mid_px":           round(mid_px,            4),
            "unique_norm":      round(unique_norm,       4),
        }

    # ─── Soft Scoring ─────────────────────────────────────────────────────────

    @staticmethod
    def _ramp(value: float, lo: float, hi: float, invert: bool = False) -> float:
        """Linear ramp in [lo, hi] → [0, 1]."""
        t = float(np.clip((value - lo) / (hi - lo + 1e-9), 0.0, 1.0))
        return (1.0 - t) if invert else t

    def _score(self, m: Dict[str, float]) -> Dict[str, float]:
        """Compute soft class scores from metrics."""
        R = self._ramp

        # ── LOGO score ────────────────────────────────────────────────────────
        # Low entropy, high bimodal, low color variance, low sat spread,
        # low gradient spread (few edge directions), moderate-high edge density
        s_logo = (
            R(m["entropy"],         2.0, 5.5, invert=True) * 0.30 +
            R(m["bimodal"],         0.5, 0.9             ) * 0.25 +
            R(m["color_variance"],  0.0, 40.0, invert=True) * 0.15 +
            R(m["gradient_spread"], 0.0, 0.12, invert=True) * 0.15 +
            R(m["edge_density"],    0.02, 0.15            ) * 0.10 +
            R(m["unique_norm"],     0.0, 0.15, invert=True) * 0.05
        )

        # ── PHOTO score ───────────────────────────────────────────────────────
        # High entropy, high color variance, high saturation spread,
        # many unique colors, low bimodal
        s_photo = (
            R(m["entropy"],         5.5, 7.5             ) * 0.30 +
            R(m["color_variance"],  30.0, 90.0            ) * 0.25 +
            R(m["sat_std"],         10.0, 40.0            ) * 0.20 +
            R(m["unique_norm"],     0.4, 1.0              ) * 0.15 +
            R(m["bimodal"],         0.0, 0.5, invert=True) * 0.10
        )

        # ── MIXED score ───────────────────────────────────────────────────────
        # Moderate entropy, moderate bimodal, some gradient spread
        # (neither flat logo nor complex photo)
        s_mixed = (
            R(m["entropy"],         4.0, 6.5             ) * 0.30 +
            R(m["mid_px"],          0.2, 0.6             ) * 0.25 +
            R(m["gradient_spread"], 0.06, 0.15           ) * 0.20 +
            R(m["sat_mean"],        5.0, 30.0             ) * 0.15 +
            R(m["color_variance"],  15.0, 60.0            ) * 0.10
        )

        total = s_logo + s_photo + s_mixed + 1e-9
        return {
            "logo":  s_logo  / total,
            "photo": s_photo / total,
            "mixed": s_mixed / total,
        }

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _downscale(self, image: np.ndarray) -> np.ndarray:
        """Downscale image to analysis resolution for speed + stability."""
        if len(image.shape) == 2:
            h, w = image.shape
        else:
            h, w = image.shape[:2]

        scale = min(1.0, self._ANA_W / max(w, 1), self._ANA_H / max(h, 1))
        if scale >= 1.0:
            return image.copy()

        return cv2.resize(image, None, fx=scale, fy=scale,
                          interpolation=cv2.INTER_AREA)
