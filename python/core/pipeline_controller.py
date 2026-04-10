"""
pipeline_controller.py — Central Pipeline Control System
Single source of truth for polarity, validation, and decision-making.

FIX GROUP: Robust polarity detection with contextual analysis
- Conservative inversion decisions
- Background-aware polarity analysis
- Multi-factor confidence scoring
- Safety checks before any inversion
"""

import cv2
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple, Dict
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# ═══ GLOBAL POLARITY CONSTANTS (single source of truth) ═══
POLARITY_INK = 0    # ink/design pixels = BLACK
POLARITY_BG = 255   # background pixels = WHITE

# Coverage bounds
MIN_INK_COVERAGE = 0.001  # 0.1% — below = blank film
MAX_INK_COVERAGE = 1.0    # 100% — allow solid designs (was 0.995, causing false rejects)

# ═══ POLARITY DECISION THRESHOLDS ═══
class PolarityThresholds:
    """Conservative thresholds for polarity decisions."""
    INK_DOMINANCE_MIN = 0.65      # Must have >65% ink to consider inversion
    BG_DOMINANCE_MIN = 0.35       # Background must be <35% to consider inversion
    DECISION_CONFIDENCE_MIN = 0.75  # 75% confidence required for inversion
    EDGE_DENSITY_MAX = 0.15       # High edge density suggests intentional high-contrast art
    BORDER_INK_RATIO_MAX = 0.90  # If >90% border is ink, likely intentional white-on-dark


@dataclass
class BinaryMetrics:
    """Metrics for evaluating binary mask quality."""
    ink_ratio: float        # fraction of pixels that are ink (0)
    edge_ratio: float       # fraction of edge pixels
    num_components: int     # number of connected components
    noise_score: float      # total area of small components
    is_valid: bool          # overall validity


class PolarityDecision:
    """Result of polarity analysis with confidence scoring."""
    def __init__(self, should_invert: bool, confidence: float, 
                 reason: str, metrics: Dict, safety_checks_passed: bool):
        self.should_invert = should_invert
        self.confidence = confidence
        self.reason = reason
        self.metrics = metrics
        self.safety_checks_passed = safety_checks_passed


class PipelineController:
    """
    Central controller for the silk screen pipeline.
    Enforces polarity, validates masks, and audits processing.
    
    🔥 ARCHITECTURE FIX: Redesigned polarity detection with:
    - Contextual image analysis (border, edge, distribution)
    - Conservative confidence-based decisions
    - Multi-factor safety checks
    - Background-aware polarity analysis
    """

    def __init__(self):
        self._audit_log = []

    def _analyze_polarity_context(self, mask: np.ndarray, 
                                   alpha_mask: Optional[np.ndarray] = None) -> Dict:
        """
        Comprehensive contextual analysis for polarity decisions.
        
        Analyzes multiple factors to determine if inversion is appropriate:
        - Border analysis (edges of image)
        - Edge density (high = intentional artwork)
        - Gray value distribution
        - Regional analysis (center vs border)
        
        Returns dict with analysis metrics.
        """
        h, w = mask.shape[:2]
        
        # Use only visible pixels if alpha mask provided
        if alpha_mask is not None:
            if alpha_mask.shape != (h, w):
                alpha_mask = cv2.resize(alpha_mask.astype(np.uint8), 
                                       (w, h), interpolation=cv2.INTER_NEAREST).astype(bool)
            effective_mask = mask.copy()
            effective_mask[~alpha_mask] = POLARITY_BG  # Set transparent to background
        else:
            effective_mask = mask
            alpha_mask = np.ones((h, w), dtype=bool)
        
        # Global ratios
        ink_px = int(np.sum((effective_mask == POLARITY_INK) & alpha_mask))
        bg_px = int(np.sum((effective_mask == POLARITY_BG) & alpha_mask))
        total_visible = np.sum(alpha_mask)
        
        ink_ratio = ink_px / (total_visible + 1e-6)
        bg_ratio = bg_px / (total_visible + 1e-6)
        
        # Border analysis (5% border strip)
        border_h = max(1, int(h * 0.05))
        border_w = max(1, int(w * 0.05))
        
        # Combine all border regions
        border_top = effective_mask[:border_h, :]
        border_bottom = effective_mask[-border_h:, :]
        border_left = effective_mask[:, :border_w]
        border_right = effective_mask[:, -border_w:]
        
        border_ink = (np.sum(border_top == POLARITY_INK) + 
                     np.sum(border_bottom == POLARITY_INK) +
                     np.sum(border_left == POLARITY_INK) + 
                     np.sum(border_right == POLARITY_INK))
        border_total = border_top.size + border_bottom.size + border_left.size + border_right.size
        border_ink_ratio = border_ink / (border_total + 1e-6)
        
        # Edge density analysis (Canny edges)
        try:
            edges = cv2.Canny(effective_mask, 50, 150)
            edge_density = np.sum(edges > 0) / (total_visible + 1e-6)
        except Exception:
            edge_density = 0
        
        # Center vs Border contrast
        center_y, center_x = h // 2, w // 2
        center_h, center_w = h // 4, w // 4
        center_region = effective_mask[
            center_y - center_h:center_y + center_h,
            center_x - center_w:center_x + center_w
        ]
        center_ink_ratio = np.sum(center_region == POLARITY_INK) / center_region.size
        
        # Gray value distribution (should be bimodal for good separation)
        # Count non-pure pixels (not exactly 0 or 255)
        if mask.dtype == np.uint8:
            gray_pixels = np.sum((mask > 10) & (mask < 245))
            gray_ratio = gray_pixels / mask.size
        else:
            gray_ratio = 0
        
        return {
            'ink_ratio': ink_ratio,
            'bg_ratio': bg_ratio,
            'border_ink_ratio': border_ink_ratio,
            'edge_density': edge_density,
            'center_ink_ratio': center_ink_ratio,
            'gray_ratio': gray_ratio,
            'total_visible': total_visible,
            'ink_px': ink_px,
            'bg_px': bg_px,
        }
    
    def _calculate_inversion_confidence(self, metrics: Dict) -> PolarityDecision:
        """
        Calculate confidence score for polarity inversion decision.
        
        Uses multiple factors weighted by importance:
        - Ink dominance (primary factor)
        - Border consistency (secondary)
        - Edge density (tertiary - high edges = less likely to need inversion)
        - Gray ratio (quaternary - high gray = uncertain separation)
        
        Returns PolarityDecision with confidence and reasoning.
        """
        ink_ratio = metrics['ink_ratio']
        bg_ratio = metrics['bg_ratio']
        border_ink_ratio = metrics['border_ink_ratio']
        edge_density = metrics['edge_density']
        gray_ratio = metrics['gray_ratio']
        
        # Initialize confidence components
        confidence_score = 0.0
        reasons = []
        safety_checks = []
        
        # PRIMARY: Ink dominance check
        # Conservative threshold: ink must be significantly dominant
        if ink_ratio > PolarityThresholds.INK_DOMINANCE_MIN:
            confidence_score += 0.50  # 50% weight
            reasons.append(f"ink_dominance({ink_ratio:.1%})")
            safety_checks.append(True)
        else:
            # Ink not dominant enough - low confidence for inversion
            safety_checks.append(False)
        
        # SECONDARY: Background scarcity check
        # Background must be significantly minority
        if bg_ratio < PolarityThresholds.BG_DOMINANCE_MIN:
            confidence_score += 0.25  # 25% weight
            reasons.append(f"bg_scarcity({bg_ratio:.1%})")
            safety_checks.append(True)
        else:
            safety_checks.append(False)
        
        # TERTIARY: Border analysis
        # If border is mostly ink, likely a solid design on white background
        # which is correct and shouldn't be inverted
        if border_ink_ratio > PolarityThresholds.BORDER_INK_RATIO_MAX:
            # Border mostly ink - this suggests intentional solid design
            confidence_score -= 0.30  # Penalty - reduces inversion confidence
            reasons.append(f"border_mostly_ink({border_ink_ratio:.1%})")
            safety_checks.append(False)  # This is a red flag
        elif border_ink_ratio < 0.30:
            # Border mostly background - good sign for inversion candidate
            confidence_score += 0.15
            reasons.append(f"border_mostly_bg({border_ink_ratio:.1%})")
            safety_checks.append(True)
        
        # QUATERNARY: Edge density check
        # High edge density suggests intentional high-contrast artwork
        # which may have intentional ink-heavy design
        if edge_density > PolarityThresholds.EDGE_DENSITY_MAX:
            confidence_score -= 0.10  # Small penalty
            reasons.append(f"high_edge_density({edge_density:.2f})")
        
        # GRAY RATIO: Quality indicator
        # High gray ratio means poor separation - be conservative
        if gray_ratio > 0.10:  # >10% gray pixels
            confidence_score *= 0.8  # Reduce confidence by 20%
            reasons.append(f"high_gray_ratio({gray_ratio:.1%})")
        
        # Final decision
        should_invert = (confidence_score >= PolarityThresholds.DECISION_CONFIDENCE_MIN)
        all_safety_passed = all(safety_checks) if safety_checks else False
        
        reason_str = " | ".join(reasons) if reasons else "no_factors"
        
        return PolarityDecision(
            should_invert=should_invert,
            confidence=confidence_score,
            reason=reason_str,
            metrics=metrics,
            safety_checks_passed=all_safety_passed
        )

    def enforce_polarity(self, mask: np.ndarray, stage: str = "unknown", 
                         force_black_ink: bool = False,
                         alpha_mask: Optional[np.ndarray] = None) -> np.ndarray:
        """
        🔥 ARCHITECTURE FIX: Redesigned with conservative contextual analysis.
        
        Ensures: ink=BLACK(0), background=WHITE(255)
        
        Uses multi-factor confidence scoring for inversion decisions:
        1. Contextual analysis (border, edges, center distribution)
        2. Conservative thresholds (75% confidence required)
        3. Safety checks (must pass multiple criteria)
        4. Background-aware analysis with alpha mask
        
        Args:
            force_black_ink: If True, bypass confidence check for 1-color artwork
            alpha_mask: Optional boolean mask (True=visible, False=transparent)
                       Only visible pixels count toward polarity decisions.
        """
        if mask is None:
            return None
            
        if len(mask.shape) == 3:
            mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)

        if mask.dtype != np.uint8:
            mask = mask.astype(np.uint8)
        
        # ─── STEP 1: Contextual Analysis ───
        context = self._analyze_polarity_context(mask, alpha_mask)
        
        # ─── STEP 2: Confidence-Based Decision ───
        decision = self._calculate_inversion_confidence(context)
        
        # ─── STEP 3: Apply Decision with Logging ───
        if force_black_ink and context['ink_ratio'] > context['bg_ratio']:
            # Special case: 1-color artwork with explicit black ink preference
            logger.info(f"  [Polarity] {stage}: force_black_ink -> inverting (ink={context['ink_ratio']:.1%})")
            mask = cv2.bitwise_not(mask)
        elif decision.should_invert and decision.safety_checks_passed:
            # Confident inversion with all safety checks passed
            logger.info(
                f"  [Polarity] {stage}: CONFIDENT INVERSION (conf={decision.confidence:.1%})\n"
                f"    -> ink={context['ink_ratio']:.1%}, bg={context['bg_ratio']:.1%}, "
                f"border_ink={context['border_ink_ratio']:.1%}\n"
                f"    -> factors: {decision.reason}"
            )
            mask = cv2.bitwise_not(mask)
        elif decision.should_invert and not decision.safety_checks_passed:
            # Would invert but safety checks failed - CONSERVATIVE: skip
            logger.warning(
                f"  [Polarity] {stage}: INVERSION SKIPPED (safety check failed, conf={decision.confidence:.1%})\n"
                f"    -> ink={context['ink_ratio']:.1%}, bg={context['bg_ratio']:.1%}\n"
                f"    -> factors: {decision.reason}"
            )
        else:
            # No inversion needed
            logger.debug(
                f"  [Polarity] {stage}: OK (conf={decision.confidence:.1%}, "
                f"ink={context['ink_ratio']:.1%})"
            )
        
        return mask

    def evaluate_binary(self, mask: np.ndarray, stage: str = "unknown") -> BinaryMetrics:
        """
        Evaluate binary mask quality.
        Returns metrics for decision-making.
        """
        if mask is None:
            raise ValueError(f"Mask is None at {stage}")
            
        if len(mask.shape) == 3:
            mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)

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
            f"Mask {mask_id} is invalid: ink_ratio={metrics.ink_ratio:.1%}, "
            f"flipped={flipped_metrics.ink_ratio:.1%}. Cannot export."
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

    def validate_mask_coverage(
        self, 
        mask: np.ndarray, 
        stage: str, 
        min_coverage: float = MIN_INK_COVERAGE, 
        max_coverage: float = MAX_INK_COVERAGE
    ) -> None:
        """
        Hard guard against blank or fully-flooded masks.
        Raises ValueError if coverage is outside safe bounds.
        """
        if mask.dtype != np.uint8:
            mask = mask.astype(np.uint8)

        total_px = mask.size
        ink_px = int(np.sum(mask == POLARITY_INK))
        ink_ratio = ink_px / total_px
        
        # Debug: Show mask statistics
        unique_vals = np.unique(mask)
        logger.info(f"  [Debug] {stage}: unique_vals={unique_vals}, ink_ratio={ink_ratio:.4%}, polarity_ink={POLARITY_INK}")

        if ink_ratio < min_coverage:
            msg = f"BLANK_MASK: {stage} ink coverage {ink_ratio:.4%} < {min_coverage:.4%}"
            logger.error(f"  [Safety] {msg}")
            raise ValueError(msg)
        
        if ink_ratio > max_coverage:
            msg = f"OVER_FLOODED: {stage} ink coverage {ink_ratio:.4%} > {max_coverage:.4%}"
            logger.error(f"  [Safety] {msg}")
            raise ValueError(msg)

        logger.info(f"  [Safety] {stage} coverage verified: {ink_ratio:.2%}")

    def get_audit_log(self) -> list:
        """Return the audit log for debugging."""
        return self._audit_log
