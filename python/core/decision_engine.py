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
            'dot_size', 'dot_sizes', 'dot_shape'
        ]

        SENTINELS = {'smoothing_factor': -1.0, 'corner_threshold': -1.0}

        defaults = {
            'dpi': 300, 'lpi': 85, 'colors': 0, 'halftone': False, 
            'smoothing_factor': 0.25, 'image_type': 'auto',
            'corner_threshold': 120.0, 'upscale_factor': 1.0,
            'denoise_strength': 3, 'contour_min_area': 50,
            'simplification_epsilon': 1.2, 'page_size': 'A4',
            'dot_size': 1.0, 'dot_sizes': None, 'dot_shape': 'round'
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
                is_sentinel = (p in SENTINELS and val == SENTINELS[p])
                is_default = is_sentinel or (val == defaults.get(p))
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
            # HIGH-CONFIDENCE HINT / NO-AI: Skip heavy AI vision if Flutter already decided.
            hint_class = getattr(args, 'image_class_hint', 'auto')
            hint_conf = float(getattr(args, 'ai_confidence', 0.0) or 0.0)
            force_no_ai = bool(getattr(args, 'no_ai', False))

            ai_result = None
            if force_no_ai or (hint_class != 'auto' and hint_conf >= 0.90):
                logger.info(f"[DecisionEngine] ⚡ Skipping AI Vision (hint={hint_class}, conf={hint_conf:.2f}, no_ai={force_no_ai})")
                ai_result = {'image_class': hint_class, 'confidence': hint_conf}
            else:
                logger.info("[DecisionEngine] 🧠 AI VISION: Analyzing...")
                ai_result = ai_module.analyze_image(
                    image,
                    hint_class=hint_class if hint_class != 'auto' else None,
                    hint_confidence=hint_conf,
                )

            if ai_result:
                ai_class = ai_result.get('image_class')
                ai_conf = ai_result.get('confidence', 0.0)
                
                # Lock if confidence is high or from fast classifier
                if ai_conf >= 0.9:
                    final_class = ai_class
                    is_class_locked = True
                    self.decision.is_locked = True
                    self.decision.confidence = ai_conf
                    logger.info(f"[DecisionEngine] Class LOCKED by high-conf AI: {final_class} ({ai_conf:.2%})")
                elif ai_conf > 0.1: # Store even low confidence for decision logic
                    final_class = ai_class
                    self.decision.confidence = ai_conf
                
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
            
            # SmartAnalyzer overrides only if AI confidence is low (< 0.7)
            # or if the current class is generic 'artwork' and smart analyzer found something more specific
            if self.decision.confidence < 0.7:
                final_class = smart_result.image_class.value
                self.decision.confidence = smart_result.confidence
                logger.info(f"[DecisionEngine] Heuristic fallback: {final_class} (AI conf was {self.decision.confidence:.2%})")

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

        # AUTO-SMOOTHING — always quality-adjust unless user explicitly set it
        smooth = self.decision.parameters.get('smoothing_factor', 0.25)
        user_set_smooth = 'smoothing_factor' in self.decision.explicit_user_overrides
        ai_set_smooth = any(
            a.parameter == 'smoothing_factor' and a.source in (DecisionSource.AI,)
            for a in self.decision.audit_trail
        )
        ai_confident = self.decision.confidence >= 0.7

        if not user_set_smooth:
            smooth_cfg = {
                'text_logo': (0.05, 0.3,  (0.03, 0.12)),
                'photo':     (0.65, 0.5,  (0.40, 0.65)),
            }
            base, dscale, (cmin, cmax) = smooth_cfg.get(
                self.decision.image_class, (0.35, 1.0, (0.15, 0.60))
            )

            res_q, blur_q, noise_q = self._compute_image_quality_factors(image)

            # If AI set a confident value, use it as base and apply quality delta
            # Otherwise, use the class base
            if ai_set_smooth and ai_confident:
                smooth = float(self.decision.parameters.get('smoothing_factor', base))
            else:
                smooth = base

            smooth_delta = (
                np.interp(res_q,  [0.0, 1.0], [0.08, -0.05]) +
                np.interp(blur_q, [0.0, 1.0], [0.10,  0.00]) +
                np.interp(noise_q,[0.0, 1.0], [0.08,  0.00])
            )
            smooth = float(np.clip(smooth + smooth_delta * dscale, cmin, cmax))

            self.update_param('smoothing_factor', smooth, DecisionSource.HEURISTIC,
                              f"Quality-adjusted (rd={res_q:.2f}, bd={blur_q:.2f}, nd={noise_q:.2f})")
            args.smoothing_factor = smooth

        # AUTO CORNER THRESHOLD — always quality-adjust unless user explicitly set it
        corner_thr = self.decision.parameters.get('corner_threshold', defaults.get('corner_threshold', 120.0))
        user_set_corner = 'corner_threshold' in self.decision.explicit_user_overrides
        ai_set_corner = any(
            a.parameter == 'corner_threshold' and a.source in (DecisionSource.AI,)
            for a in self.decision.audit_trail
        )

        if not user_set_corner:
            corner_cfg = {
                'text_logo': (45.0, 0.3,  (30.0, 60.0)),
                'photo':     (135.0, 0.5, (110.0, 170.0)),
            }
            base, dscale, (cmin, cmax) = corner_cfg.get(
                self.decision.image_class, (120.0, 1.0, (80.0, 160.0))
            )

            res_q, blur_q, noise_q = self._compute_image_quality_factors(image)

            # If AI set a confident value, use it as base and apply quality delta
            if ai_set_corner and ai_confident:
                corner_thr = float(self.decision.parameters.get('corner_threshold', base))
            else:
                corner_thr = base

            corner_delta = (
                np.interp(res_q,  [0.0, 1.0], [15.0, -10.0]) +
                np.interp(blur_q, [0.0, 1.0], [20.0,   0.0]) +
                np.interp(noise_q,[0.0, 1.0], [15.0,   0.0])
            )
            corner_thr = float(np.clip(corner_thr + corner_delta * dscale, cmin, cmax))

            self.update_param('corner_threshold', corner_thr, DecisionSource.HEURISTIC,
                              "Quality-adjusted corner threshold")
            args.corner_threshold = corner_thr

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

    def _compute_image_quality_factors(self, image: np.ndarray) -> tuple:
        """Compute quality factors 0.0-1.0 for resolution, blur, noise.
        Returns (res_q, blur_q, noise_q) where 1.0 = best quality.
        """
        if image is None or image.size == 0:
            return (0.5, 0.5, 0.5)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        h, w = gray.shape
        max_dim = max(h, w)

        # Resolution: 0.0 (صغير < 300px) → 1.0 (كبير > 4000px)
        res_q = np.clip((max_dim - 300) / (4000 - 300), 0.0, 1.0)

        # Blur (inverse Laplacian): 0.0 (باهت جداً) → 1.0 (حاد)
        lap_var = float(cv2.Laplacian(gray, cv2.CV_32F).var())
        blur_q = np.clip(lap_var / 500, 0.0, 1.0)

        # Noise (Gaussian diff std): 0.0 (شرشرة كتير) → 1.0 (نظيف)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        noise_std = float(np.std(gray.astype(float) - blurred.astype(float)))
        noise_q = np.clip(1.0 - noise_std / 30, 0.0, 1.0)

        return (res_q, blur_q, noise_q)



