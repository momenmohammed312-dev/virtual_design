"""
pipeline_controller.py — Central Pipeline Control System
Single source of truth for polarity, validation, and decision-making.
"""

import cv2
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# ═══ GLOBAL POLARITY CONSTANTS (single source of truth) ═══
POLARITY_INK = 0    # ink/design pixels = BLACK
POLARITY_BG = 255   # background pixels = WHITE

# Coverage bounds
MIN_INK_COVERAGE = 0.005  # 0.5% — below = blank film
MAX_INK_COVERAGE = 0.97   # 97%  — above = inverted mask


@dataclass
class BinaryMetrics:
    """Metrics for evaluating binary mask quality."""
    ink_ratio: float        # fraction of pixels that are ink (0)
    edge_ratio: float       # fraction of edge pixels
    num_components: int     # number of connected components
    noise_score: float      # total area of small components
    is_valid: bool          # overall validity


class PipelineController:
    """
    Central controller for the silk screen pipeline.
    Enforces polarity, validates masks, and audits processing.
    """

    def __init__(self):
        self._audit_log = []

    def enforce_polarity(self, mask: np.ndarray, stage: str = "unknown") -> np.ndarray:
        """
        The ONLY function allowed to do inversion.
        Ensures: ink=BLACK(0), background=WHITE(255)
        
        Decision: if mean(mask) <= 127 → polarity is wrong → invert
        """
        if mask.dtype != np.uint8:
            mask = mask.astype(np.uint8)

        mean_val = np.mean(mask)
        
        # If most pixels are dark (mean <= 127), the mask is inverted
        # Design should be black (0), background should be white (255)
        if mean_val <= 127:
            logger.info(f"  [Polarity] {stage}: mean={mean_val:.1f} ≤ 127 → inverting")
            mask = cv2.bitwise_not(mask)
        else:
            logger.debug(f"  [Polarity] {stage}: mean={mean_val:.1f} > 127 → OK")
        
        return mask

    def evaluate_binary(self, mask: np.ndarray, stage: str = "unknown") -> BinaryMetrics:
        """
        Evaluate binary mask quality.
        Returns metrics for decision-making.
        """
        if mask.dtype != np.uint8:
            mask = mask.astype(np.uint8)

        total_px = mask.size
        ink_px = int(np.sum(mask == POLARITY_INK))
        ink_ratio = ink_px / total_px

        # Edge detection
        edges = cv2.Canny(mask, 50, 150)
        edge_ratio = np.sum(edges > 0) / total_px

        # Connected components
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
        num_components = num_labels - 1  # exclude background

        # Noise score: total area of small components (< 50 pixels)
        noise_score = 0
        for lbl in range(1, num_labels):
            area = stats[lbl, cv2.CC_STAT_AREA]
            if area < 50:
                noise_score += area

        # Validity check
        is_valid = (MIN_INK_COVERAGE <= ink_ratio <= MAX_INK_COVERAGE)

        metrics = BinaryMetrics(
            ink_ratio=ink_ratio,
            edge_ratio=edge_ratio,
            num_components=num_components,
            noise_score=float(noise_score),
            is_valid=is_valid,
        )

        # Audit log
        status = "✓" if is_valid else "✗"
        logger.info(f"  [Evaluate] {stage}: ink={ink_ratio:.1%} edges={edge_ratio:.3f} "
                    f"components={num_components} noise={noise_score} {status}")

        return metrics

    def validate_mask(self, mask: np.ndarray, mask_id: int = 0) -> np.ndarray:
        """
        Hard gate before export. Tries to fix invalid masks.
        Raises ValueError if mask cannot be fixed.
        """
        if mask.dtype != np.uint8:
            mask = mask.astype(np.uint8)

        # First, enforce polarity
        mask = self.enforce_polarity(mask, stage=f"validate/{mask_id}")

        # Evaluate
        metrics = self.evaluate_binary(mask, stage=f"validate/{mask_id}")

        if metrics.is_valid:
            return mask

        # Try to fix: flip polarity and re-evaluate
        flipped = cv2.bitwise_not(mask)
        flipped_metrics = self.evaluate_binary(flipped, stage=f"validate/{mask_id}/flip")

        if flipped_metrics.is_valid:
            logger.warning(f"  [Validate] Mask {mask_id}: fixed by flipping polarity")
            return flipped

        # Cannot fix
        raise ValueError(
            f"Mask {mask_id} is invalid: ink_ratio={metrics:.1%}, "
            f"flipped={flipped_metrics:.1%}. Cannot export."
        )

    def audit(self, mask: np.ndarray, stage: str) -> None:
        """
        Log audit info without raising exceptions.
        Call after every step that modifies a mask.
        """
        if mask.dtype != np.uint8:
            mask = mask.astype(np.uint8)

        ink_ratio = np.sum(mask == POLARITY_INK) / mask.size
        mean_val = np.mean(mask)
        
        status = "OK" if MIN_INK_COVERAGE <= ink_ratio <= MAX_INK_COVERAGE else "WARN"
        
        self._audit_log.append({
            'stage': stage,
            'ink_ratio': ink_ratio,
            'mean': mean_val,
            'status': status,
        })
        
        if status == "WARN":
            logger.warning(f"  [Audit] {stage}: ink={ink_ratio:.1%} mean={mean_val:.1f} ⚠️")
        else:
            logger.debug(f"  [Audit] {stage}: ink={ink_ratio:.1%} mean={mean_val:.1f} ✓")

    def get_audit_log(self) -> list:
        """Return the audit log for debugging."""
        return self._audit_log
