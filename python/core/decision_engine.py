"""
decision_engine.py — Unified Decision Oracle for Silk Screen Pipeline
Centralizes all logic from main.py, pipeline_router.py, and ai_vision_bridge.py.
"""

import logging
import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class DecisionSource(Enum):
    USER = "USER"           # Explicit manual setting
    AI = "AI"               # Multimodal AI recommendation
    RULE = "RULE"           # Rule-based / Heuristic fallback
    PHYS_CONSTRAINT = "PHYS" # Forced by physics (DPI/Mesh limits)

@dataclass
class ParameterAudit:
    parameter: str
    value: Any
    previous_value: Any
    source: DecisionSource
    reason: str

@dataclass
class PipelineDecision:
    image_class: str = "artwork"
    parameters: Dict[str, Any] = field(default_factory=dict)
    audit_trail: List[ParameterAudit] = field(default_factory=list)
    confidence: float = 0.0
    reasoning: List[str] = field(default_factory=list)

class DecisionOracle:
    """
    The Single Source of Truth for pipeline configuration.
    It takes all inputs and synthesizes a final executable decision.
    """
    def __init__(self):
        self.decision = PipelineDecision()

    def update_param(self, param: str, value: Any, source: DecisionSource, reason: str):
        prev = self.decision.parameters.get(param)
        self.decision.parameters[param] = value
        self.decision.audit_trail.append(ParameterAudit(
            parameter=param,
            value=value,
            previous_value=prev,
            source=source,
            reason=reason
        ))

    def solve(self, image: np.ndarray, args: Any, ai_module: Any, ppm_module: Any) -> PipelineDecision:
        """
        Main entry point for decision synthesis.
        """
        # 0. Initialize from User Args (Lowest priority defaults)
        self.decision.image_class = getattr(args, 'image_type', 'artwork')
        params_to_track = [
            'dpi', 'lpi', 'colors', 'halftone', 'smoothing_factor', 
            'corner_threshold', 'upscale_factor', 'denoise_strength',
            'contour_min_area', 'simplification_epsilon', 'page_size',
            'page_width', 'page_height', 'margin_pt'
        ]
        for p in params_to_track:
            val = getattr(args, p, None)
            if val is not None and val != -1 and val != -1.0:
                self.update_param(p, val, DecisionSource.USER, "Initial input")

        # Handle explicit --skip-halftone flag
        if getattr(args, 'skip_halftone', False):
            self.update_param('halftone', False, DecisionSource.USER, "Forced skip via --skip-halftone")

        # 1. Physical Constraints (Apply calibration and safety rules)
        # These have HIGHEST priority as they prevent physical printing failure
        max_safe_lpi = ppm_module.get_max_safe_lpi()
        current_lpi = self.decision.parameters.get('lpi', 0)
        if current_lpi > max_safe_lpi:
            self.update_param('lpi', max_safe_lpi, DecisionSource.PHYS_CONSTRAINT, 
                             f"Mesh {ppm_module.mesh_count} ceiling reached (clamped from {current_lpi})")

        # 2. Heuristic Analysis (Fast Rule-based fallback)
        stats = self._get_image_stats(image)
        if stats['is_binary'] and getattr(args, 'image_type', 'auto') == 'auto':
            self.decision.image_class = 'text_logo'
            self.decision.reasoning.append("Heuristic: High-contrast binary content detected")

        # 3. AI Vision Analysis (The 'Brain')
        if getattr(args, 'image_type', 'auto') == 'auto':
            ai_result = ai_module.analyze_image(image)
            if ai_result:
                self.decision.image_class = ai_result.get('image_class', self.decision.image_class)
                self.decision.confidence = ai_result.get('confidence', 0.5)
                
                # Merge AI parameters if NOT explicitly 'locked' by user
                for p, val in ai_result.items():
                    if p in params_to_track:
                        # Policy: If User set it deliberately, don't let AI override unless it's a critical safety fix
                        current_source = self._get_last_source(p)
                        if current_source != DecisionSource.USER:
                             self.update_param(p, val, DecisionSource.AI, ai_result.get('auto_adjustment_reason', 'AI Optimization'))

        return self.decision

    def _get_last_source(self, param: str) -> Optional[DecisionSource]:
        for audit in reversed(self.decision.audit_trail):
            if audit.parameter == param:
                return audit.source
        return None

    def _get_image_stats(self, image: np.ndarray) -> Dict:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
        total = max(1, gray.size)
        dark_ratio = hist[:30].sum() / total
        light_ratio = hist[225:].sum() / total
        return {'is_binary': (dark_ratio + light_ratio) > 0.9}

    def get_summary_dict(self) -> Dict:
        return {
            "image_class": self.decision.image_class,
            "confidence": self.decision.confidence,
            "best_params": self.decision.parameters,
            "trace": [
                {
                    "param": a.parameter, 
                    "value": a.value, 
                    "source": a.source.value, 
                    "reason": a.reason
                } for a in self.decision.audit_trail
            ]
        }
