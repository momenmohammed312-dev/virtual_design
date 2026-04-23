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
from core.router_utils import safe_float, safe_int

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
    is_locked: bool = False  # Prevents low-prio overrides (e.g. from MobileHints)

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
        Unified decision logic with strict priority and safety guardrails.
        PRIORITY: 
        1. User Explicit Override (UI selection)
        2. Fast Classifier (Confidence >= 0.9)
        3. AI Vision Bridge
        4. SmartAnalyzer (Heuristic fallback)
        """
        params_to_track = [
            'dpi', 'lpi', 'colors', 'halftone', 'smoothing_factor', 
            'corner_threshold', 'upscale_factor', 'denoise_strength',
            'contour_min_area', 'simplification_epsilon', 'page_size',
            'page_width', 'page_height', 'margin_pt', 'image_type',
            'dot_size', 'dot_sizes'
        ]

        defaults = {
            'dpi': 300, 'lpi': 85, 'colors': 0, 'halftone': False, 
            'smoothing_factor': 0.25, 'image_type': 'auto',
            'corner_threshold': 120.0, 'upscale_factor': 1.0,
            'denoise_strength': 3, 'contour_min_area': 50,
            'simplification_epsilon': 1.2, 'page_size': 'A4',
            'dot_size': 1.0, 'dot_sizes': None
        }

        # 1. INITIALIZATION & TYPE SANITIZATION
        for p in params_to_track:
            val = getattr(args, p, None)
            
            # CRITICAL FIX: Direct parameter casting to prevent TypeError: '>' not supported between str and float
            if p in ['smoothing_factor', 'corner_threshold', 'upscale_factor', 'simplification_epsilon', 'dot_size', 'margin_pt', 'page_width', 'page_height']:
                val = safe_float(val, defaults.get(p))
            elif p in ['dpi', 'lpi', 'colors', 'contour_min_area', 'denoise_strength']:
                val = safe_int(val, defaults.get(p))

            if val is not None:
                is_default = (val == defaults.get(p))
                source = DecisionSource.USER_DEFAULT if is_default else DecisionSource.USER_EXPLICIT
                self.update_param(p, val, source, "Input Setup")
                if source == DecisionSource.USER_EXPLICIT:
                    self.decision.explicit_user_overrides.add(p)

        # 2. PRIORITY-BASED CLASSIFICATION
        is_class_locked = False
        final_class = "artwork"
        
        # A. USER OVERRIDE (Tier 1)
        user_choice = self.decision.parameters.get('image_type', 'auto')
        if user_choice != 'auto':
            final_class = user_choice
            is_class_locked = True
            self.decision.is_locked = True
            logger.info(f"[DecisionEngine] Class LOCKED by User: {final_class}")

        # B. AI VISION & FAST CLASSIFIER (Tier 2)
        if not is_class_locked:
            logger.info("[DecisionEngine] 🧠 AI VISION: Analyzing...")
            ai_result = ai_module.analyze_image(image)
            if ai_result:
                ai_class = ai_result.get('image_class')
                ai_conf = ai_result.get('confidence', 0.0)
                
                # Lock if confidence is high or from fast classifier
                if ai_conf >= 0.9:
                    final_class = ai_class
                    is_class_locked = True
                    self.decision.is_locked = True
                    logger.info(f"[DecisionEngine] Class LOCKED by high-conf AI: {final_class} ({ai_conf:.2%})")
                elif ai_conf > 0.6:
                    final_class = ai_class
                
                # Propagate AI parameters if not user-set
                for p, val in ai_result.items():
                    if p in params_to_track and p not in self.decision.explicit_user_overrides:
                        # Sanitize AI internal types
                        if p in ['smoothing_factor', 'corner_threshold', 'upscale_factor', 'simplification_epsilon']:
                            val = safe_float(val)
                        self.update_param(p, val, DecisionSource.AI, "AI Optimization")

        # C. SMART ANALYZER (Tier 3 - Fallback)
        if not is_class_locked:
            analyzer = SmartAnalyzer()
            dpi = self.decision.parameters.get('dpi', 300)
            smart_result = analyzer.analyze(image, dpi=dpi)
            if self.decision.image_class == 'artwork' or self.decision.confidence < 0.4:
                final_class = smart_result.image_class.value
                self.decision.confidence = smart_result.confidence
                logger.info(f"[DecisionEngine] Heuristic fallback: {final_class}")

        self.decision.image_class = final_class
        
        # 3. SAFETY & LOGIC VALIDATION
        
        # HALFTONE VS LOGO SAFETY
        is_halftone = bool(self.decision.parameters.get('halftone', False))
        user_forced_halftone = 'halftone' in self.decision.explicit_user_overrides
        
        if self.decision.image_class == 'text_logo' and is_halftone:
            if not user_forced_halftone:
                logger.info("[DecisionEngine] 🛡️ AUTO-DISABLE: Halftone disabled for text_logo class.")
                self.update_param('halftone', False, DecisionSource.HEURISTIC, "Logos should be solid for clean edges")
                is_halftone = False
            else:
                logger.warning("[DecisionEngine] ⚠️ Warning: User forced halftone on logo. Routing to artwork pipeline.")
                self.decision.image_class = 'artwork' # Upgrade for halftone support

        # AUTO-SMOOTHING
        smooth = self.decision.parameters.get('smoothing_factor', 0.25)
        if smooth < 0: # Handle -1.0 sentinel
            if self.decision.image_class == 'text_logo': smooth = 0.05
            elif self.decision.image_class == 'photo': smooth = 0.65
            else: smooth = 0.35
            self.update_param('smoothing_factor', smooth, DecisionSource.HEURISTIC, "Class-based auto-smoothing")
            args.smoothing_factor = smooth  # Sync back to args so pipeline uses it

        # 4. PHYSICAL CONSTRAINTS & LPI/DPI MAPPING
        mesh = safe_int(getattr(ppm_module, 'mesh_count', 160), 160)
        max_safe_lpi = int(mesh / 4.5)
        current_lpi = self.decision.parameters.get('lpi', 45)
        
        if current_lpi > max_safe_lpi:
            logger.warning(f"[DecisionEngine] LPI {current_lpi} clamped to {max_safe_lpi} for mesh {mesh}")
            self.update_param('lpi', max_safe_lpi, DecisionSource.PHYS_CONSTRAINT, f"Mesh {mesh} limit")
            current_lpi = max_safe_lpi

        # IDEAL DPI
        if is_halftone:
            ideal_dpi = current_lpi * 16
            max_dpi = current_lpi * 20
            current_dpi = self.decision.parameters.get('dpi', 300)
            
            if current_dpi > max_dpi:
                self.update_param('dpi', max_dpi, DecisionSource.PHYS_CONSTRAINT, f"Clamped to LPI*20 for detail limits")
            elif current_dpi < ideal_dpi and 'dpi' not in self.decision.explicit_user_overrides:
                self.update_param('dpi', ideal_dpi, DecisionSource.PHYS_CONSTRAINT, f"Auto-optimized for LPI {current_lpi}")

        # Feedback metadata for UI
        self.decision.parameters['_final_lpi'] = self.decision.parameters.get('lpi')
        self.decision.parameters['_final_dpi'] = self.decision.parameters.get('dpi')
        self.decision.parameters['_mesh_limit'] = max_safe_lpi

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

