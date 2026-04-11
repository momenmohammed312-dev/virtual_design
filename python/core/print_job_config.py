"""
print_job_config.py — Screen Print Parameters & Mesh Constraints
Virtual Design Silk Screen Studio
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
import math
import logging

logger = logging.getLogger(__name__)

@dataclass
class PrintJobConfig:
    """
    Manages mesh-count constraints, LPI limits, and dot physics
    for screen printing based on standard screen mesh tables.
    """
    mesh_count: int = 160  # Threads per inch (e.g. 86, 110, 160, 200, 305)
    dpi: int = 600
    ink_type: str = "plastisol"
    substrate_color: str = "white"
    
    # CRITICAL FIX: Dot gain compensation curves for professional press accuracy
    # Values represent tone reproduction curves (input -> output after dot gain)
    DOT_GAIN_CURVES: Dict[str, Dict[float, float]] = field(default_factory=lambda: {
        'plastisol_white': {0.0: 0.0, 0.25: 0.19, 0.5: 0.40, 0.75: 0.64, 1.0: 1.0},
        'water_based': {0.0: 0.0, 0.25: 0.21, 0.5: 0.42, 0.75: 0.67, 1.0: 1.0},
        'discharge': {0.0: 0.0, 0.25: 0.23, 0.5: 0.45, 0.75: 0.70, 1.0: 1.0},
        'uv_curable': {0.0: 0.0, 0.25: 0.18, 0.5: 0.38, 0.75: 0.62, 1.0: 1.0},
    })
    
    # Standard Mesh-to-LPI limit table (Rule of Thumb: LPI <= Mesh / 3 or 3.5)
    # Using conservative LPI limits to prevent dot bridge failure/ink flooding.
    MESH_LPI_TABLE: Dict[int, int] = field(default_factory=lambda: {
        86: 33,   # Course mesh (Athletic/Block designs)
        110: 42,  # Standard mesh (Simple logos)
        160: 55,  # Medium-fine (General halftone)
        200: 65,  # Fine (Detailed halftone)
        230: 75,  # Very fine (High detail)
        280: 85,  # Super fine
        305: 95,  # Process fine
        355: 110  # Ultra fine
    })

    # ── Single-source LPI ceiling constants (FIX: unified with router_utils) ─
    # Industry standard: mesh/3.5 is the hard ceiling for halftone LPI.
    # Below this ratio, dots begin to bridge threads and cause ink flooding.
    # DPI-based ceiling: need ≥4 pixels per dot for ≥16 tone levels.
    # Re-tuned for Professional High-Density output. 
    # mesh/2.2 allows for ultra-fine dots (e.g. 150-160 LPI on 355 mesh).
    MESH_RATIO_DIVISOR: float = 2.2   # mesh / 2.2  → aggressive detail ceiling
    DPI_RATIO_DIVISOR:  float = 4.0   # dpi  / 4.0  → hard DPI  ceiling
    LPI_ABSOLUTE_MIN:   int   = 25    
    LPI_ABSOLUTE_MAX:   int   = 400   # Allow ultra-fine halftone for high-end systems

    def max_safe_lpi(self, output_dpi: Optional[int] = None) -> int:
        """
        Return the hard LPI ceiling for current mesh + DPI combination.
        This is the SINGLE SOURCE OF TRUTH — router_utils and all other
        callers must delegate here instead of re-implementing the formula.

        Args:
            output_dpi: actual output device DPI (defaults to self.dpi)

        Returns:
            Maximum safe LPI (integer, always >= LPI_ABSOLUTE_MIN)
        """
        dpi = output_dpi if output_dpi is not None else self.dpi
        mesh = max(1, int(self.mesh_count))

        mesh_ceiling = int(mesh / self.MESH_RATIO_DIVISOR)    # e.g. 355/3.5 = 101
        dpi_ceiling  = int(dpi  / self.DPI_RATIO_DIVISOR)     # e.g. 1200/4  = 300

        ceiling = max(self.LPI_ABSOLUTE_MIN, min(mesh_ceiling, dpi_ceiling))
        ceiling = min(ceiling, self.LPI_ABSOLUTE_MAX)

        logger.debug(
            f"[JobConfig] max_safe_lpi: mesh={mesh}, dpi={dpi} → "
            f"mesh_ceil={mesh_ceiling}, dpi_ceil={dpi_ceiling}, result={ceiling}"
        )
        return ceiling

    def validate_lpi(self, requested_lpi: int, output_dpi: Optional[int] = None,
                     auto_fix: bool = True) -> int:
        """
        Validate and clamp requested LPI to a safe value.

        Uses the unified mesh/3.5 + dpi/4 formula (FIX: single source of
        truth — previously used inconsistent min_ratio=2.0 which allowed
        flooding-risk configurations to pass through silently).

        Args:
            requested_lpi: LPI value from user or upstream caller
            output_dpi:    actual output DPI (defaults to self.dpi)
            auto_fix:      if True, clamp silently; if False, raise ValueError

        Returns:
            Safe effective LPI (may be lower than requested_lpi)
        """
        effective_lpi = max(self.LPI_ABSOLUTE_MIN, int(requested_lpi))
        ceiling = self.max_safe_lpi(output_dpi)

        # Also check traditional mesh table for informational logging
        available_meshes = sorted(self.MESH_LPI_TABLE.keys())
        nearest_mesh = min(available_meshes, key=lambda x: abs(x - self.mesh_count))
        traditional_limit = self.MESH_LPI_TABLE.get(nearest_mesh, 45)

        if effective_lpi > ceiling:
            msg = (
                f"[JobConfig] LPI {effective_lpi} exceeds max_safe_lpi={ceiling} "
                f"(mesh={self.mesh_count}, dpi={output_dpi or self.dpi}, "
                f"traditional_table_limit={traditional_limit}). "
                f"Clamping to {ceiling} to prevent dot bridging / ink flooding."
            )
            if auto_fix:
                logger.warning(msg)
                effective_lpi = ceiling
            else:
                raise ValueError(msg)
        elif effective_lpi > traditional_limit:
            # Above traditional table limit but within physics-based ceiling — allow,
            # but inform the operator.
            logger.info(
                f"[JobConfig] LPI {effective_lpi} exceeds traditional mesh table limit "
                f"({traditional_limit} for {nearest_mesh}-mesh) but is within the "
                f"physics-based ceiling ({ceiling}). Proceeding — verify on press."
            )
        else:
            logger.info(
                f"[JobConfig] LPI {effective_lpi} accepted "
                f"(mesh={self.mesh_count}, ceiling={ceiling})."
            )

        return effective_lpi

    def calculate_dot_radius_max(self, lpi: int) -> float:
        """
        Calculates max dot radius in pixels to ensure 15% shadow relief 
        (prevent dots from touching and flooding screens).
        """
        dot_spacing_px = self.dpi / lpi
        # Standard: spacing/2 * 0.85 (Task 16 audit)
        return (dot_spacing_px / 2.0) * 0.85

    def requires_underbase(self) -> bool:
        """Heuristic for automatically triggering white underbase."""
        # Simple rule: if substrate is dark (not white/gray), we need underbase
        dark_substrates = ["black", "navy", "dark_gray", "red", "royal_blue"]
        return self.substrate_color.lower() in dark_substrates

    def get_dot_gain_curve(self, ink_type: str = None) -> Optional[Dict[float, float]]:
        """Get the dot gain compensation curve for the specified ink type."""
        ink_type = ink_type or self.ink_type
        return self.DOT_GAIN_CURVES.get(ink_type.lower(), None)

    def apply_dot_gain_compensation(self, intensities: np.ndarray, ink_type: str = None) -> np.ndarray:
        """
        Apply dot gain compensation to intensity values.
        Reduces dot sizes to compensate for expected ink spread on press.
        """
        curve = self.get_dot_gain_curve(ink_type)
        if curve is None:
            return intensities
        
        # Interpolate the compensation curve
        input_values = np.array(list(curve.keys()))
        output_values = np.array(list(curve.values()))
        
        # Clip intensities to [0, 1] range
        intensities_clipped = np.clip(intensities, 0.0, 1.0)
        
        # Apply compensation curve
        compensated = np.interp(intensities_clipped, input_values, output_values)
        
        return compensated
