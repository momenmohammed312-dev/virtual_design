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

from core.smart_analyzer import SmartAnalyzer, ImageClass

logger = logging.getLogger(__name__)

class DecisionSource(Enum):
    USER_EXPLICIT = "USER_EXPLICIT"  # User deliberately set this
    USER_DEFAULT = "USER_DEFAULT"    # Default value from UI/CLI
    AI = "AI"                        # Adaptive AI recommendation
    PHYS_CONSTRAINT = "PHYS"         # Guaranteed physical print safety
    HEURISTIC = "HEURISTIC"          # Fallback rule-based logic

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
    explicit_user_overrides: set = field(default_factory=set)

class DecisionOracle:
    """
    Unified Decision Engine for the Silk Screen Pipeline.
    Implements a 4-level hierarchy of authority to resolve conflicts.
    """
    def __init__(self):
        self.decision = PipelineDecision()

    def update_param(self, param: str, value: Any, source: DecisionSource, reason: str):
        prev = self.decision.parameters.get(param)
        self.decision.parameters[param] = value
        # Sync image_class to the direct attribute as well
        if param == 'image_class':
            self.decision.image_class = value
        self.decision.audit_trail.append(ParameterAudit(
            parameter=param,
            value=value,
            previous_value=prev,
            source=source,
            reason=reason
        ))
        if source == DecisionSource.USER_EXPLICIT:
            self.decision.explicit_user_overrides.add(param)

    def solve(self, image: np.ndarray, args: Any, ai_module: Any, ppm_module: Any) -> PipelineDecision:
        """
        Synthesizes the final execution plan by merging AI brilliance with user authority.
        """
        params_to_track = [
            'dpi', 'lpi', 'colors', 'halftone', 'smoothing_factor', 
            'corner_threshold', 'upscale_factor', 'denoise_strength',
            'contour_min_area', 'simplification_epsilon', 'page_size',
            'page_width', 'page_height', 'margin_pt', 'image_type'
        ]

        # 1. INITIALIZATION: Identify Explicit User Intent
        # We compare args with defaults (hardcoded or extracted)
        defaults = {
            'dpi': 300, 'lpi': 85, 'colors': 0, 'halftone': False, 
            'smoothing_factor': 0.25, 'image_type': 'auto',
            'corner_threshold': -1.0, 'upscale_factor': 1.0,
            'denoise_strength': 3, 'contour_min_area': 50,
            'simplification_epsilon': 1.2, 'page_size': 'A4'
        }

        for p in params_to_track:
            val = getattr(args, p, None)
            if val is not None:
                is_default = (val == defaults.get(p))
                source = DecisionSource.USER_DEFAULT if is_default else DecisionSource.USER_EXPLICIT
                self.update_param(p, val, source, "Initial Input Analysis")
                if p == 'halftone':
                    logger.info(f"[DecisionEngine] Loaded halftone={val} from args (source={source})")

        # Special Case: --skip-halftone flag is always EXPLICIT
        if getattr(args, 'skip_halftone', False):
            self.update_param('halftone', False, DecisionSource.USER_EXPLICIT, "User forced --skip-halftone")

        # Special Case: --halftone flag is always EXPLICIT user intent
        halftone_flag = getattr(args, 'halftone', False)
        logger.info(f"[DecisionEngine] args.halftone = {halftone_flag} (type: {type(halftone_flag)})")
        if halftone_flag:
            self.update_param('halftone', True, DecisionSource.USER_EXPLICIT, "User explicitly requested halftone")
            logger.info("[DecisionEngine] Set halftone to True with USER_EXPLICIT")

        # 2. HEURISTICS: Smart Analyzer (proper image classification)
        if self.decision.parameters.get('image_type') == 'auto':
            analyzer = SmartAnalyzer()
            dpi = self.decision.parameters.get('dpi', 300)
            smart_result = analyzer.analyze(image, dpi=dpi)
            detected_class = smart_result.image_class.value
            self.update_param('image_class', detected_class, DecisionSource.HEURISTIC, 
                            f"SmartAnalyzer classification with confidence {smart_result.confidence:.0%}")
            logger.info(f"[DecisionEngine] SmartAnalyzer detected: {detected_class} ({smart_result.confidence:.0%} confidence)")
        else:
            self.decision.image_class = self.decision.parameters.get('image_type', 'artwork')

        # INTENT PRESERVATION (Phase 2.5): Upgrade image_class BEFORE AI if user wants halftone
        halftone_val = self.decision.parameters.get('halftone')
        user_wants_halftone = bool(halftone_val) and 'halftone' in self.decision.explicit_user_overrides
        logger.info(f"[DecisionEngine] user_wants_halftone={user_wants_halftone}, image_class={self.decision.image_class}, halftone_val={halftone_val}, overrides={self.decision.explicit_user_overrides}")
        if user_wants_halftone and self.decision.image_class == 'text_logo':
            self.decision.reasoning.append("User forced halftone on Logo: Pre-upgrading to artwork_halftone pipeline")
            self.decision.image_class = 'artwork'  # Upgrade to artwork BEFORE AI runs
            self.decision.parameters['image_class'] = 'artwork'  # Sync to parameters
            self.decision.explicit_user_overrides.add('image_class')  # Mark as override
            logger.info("[DecisionEngine] UPGRADED: text_logo -> artwork for halftone")
        elif user_wants_halftone:
            logger.info(f"[DecisionEngine] User wants halftone but image_class is {self.decision.image_class} (not text_logo), no upgrade needed")

        # 3. AI VISION: The Brain Module
        # We only let AI override if the parameter is NOT an explicit user override
        if self.decision.parameters.get('image_type') == 'auto':
            ai_result = ai_module.analyze_image(image)
            if ai_result:
                ai_class = ai_result.get('image_class')
                if ai_class:
                    # If user wants halftone, NEVER let AI change image_class (always keep artwork)
                    if user_wants_halftone:
                        if ai_class != 'artwork':
                            self.decision.reasoning.append(f"AI suggested {ai_class} but user forced halftone - forcing artwork")
                        # Keep/force artwork regardless of AI suggestion
                        self.decision.image_class = 'artwork'
                        self.decision.confidence = 1.0  # High confidence because user forced it
                    else:
                        self.decision.image_class = ai_class
                        self.decision.confidence = ai_result.get('confidence', 0.8)

                for p, val in ai_result.items():
                    if p in params_to_track:
                        if p not in self.decision.explicit_user_overrides:
                            self.update_param(p, val, DecisionSource.AI, ai_result.get('reason', 'AI Optimization'))
                        else:
                            self.decision.reasoning.append(f"AI suggested {p}={val} but respect User explicit setting")

        # 4. PHYSICAL SAFETY: Levels 0 (The Guardian)
        # These rules override EVERYBODY (User & AI)
        max_safe_lpi = ppm_module.get_max_safe_lpi()
        current_lpi = self.decision.parameters.get('lpi', 0)
        if current_lpi > max_safe_lpi:
            self.update_param('lpi', max_safe_lpi, DecisionSource.PHYS_CONSTRAINT, 
                             f"Physical Limit: Mesh {ppm_module.mesh_count} cannot hold {current_lpi} LPI")

        return self.decision

    def _get_image_stats(self, image: np.ndarray) -> Dict:
        if image is None: return {'is_binary': False}
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
            "overrides": list(self.decision.explicit_user_overrides),
            "reasoning": self.decision.reasoning,
            "trace": [
                {
                    "param": a.parameter, 
                    "value": a.value, 
                    "source": a.source.value, 
                    "reason": a.reason
                } for a in self.decision.audit_trail
            ]
        }

