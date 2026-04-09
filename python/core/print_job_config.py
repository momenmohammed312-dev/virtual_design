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

    def validate_lpi(self, requested_lpi: int, auto_fix: bool = False) -> int:
        """Clamps the requested LPI to a safe value based on current mesh count."""
        # Find nearest standard mesh in table (if custom mesh used)
        available_meshes = sorted(self.MESH_LPI_TABLE.keys())
        nearest_mesh = min(available_meshes, key=lambda x: abs(x - self.mesh_count))
        
        limit = self.MESH_LPI_TABLE.get(nearest_mesh, 45)

        effective_lpi = int(requested_lpi)
        
        # Warn if LPI exceeds traditional mesh limit, but don't clamp (DPI priority)
        if effective_lpi > limit:
            logger.info(f"[JobConfig] LPI {effective_lpi} exceeds traditional mesh limit ({limit}) for {self.mesh_count} mesh. "
                       f"Allowing due to high DPI capability.")
        
        mesh = max(1, int(self.mesh_count))
        ratio = float(mesh) / float(max(1, effective_lpi))

        # Relaxed ratios: prioritize DPI-based LPI for finer dots
        # High DPI (1200+) can support LPI up to 150 regardless of mesh ratio
        min_ratio = 2.0   # Very permissive - only fix when definitely flooding
        max_ratio = 8.0   # Allow very high ratios for coarse meshes

        lpi_min = int(math.ceil(mesh / max_ratio))
        lpi_max = int(math.floor(mesh / min_ratio))

        # Only force adjustment when dangerously out of range
        if ratio < 2.0:  # Definitely flooding risk
            suggested = int(round(mesh / 4.5))
            suggested = max(lpi_min, min(lpi_max, suggested))
            # Use absolute max LPI of 150 instead of mesh limit
            suggested = min(suggested, 150)
            logger.warning(
                f"[JobConfig] CRITICAL: Mesh/LPI ratio too low (mesh={mesh}, lpi={effective_lpi}, ratio={ratio:.2f}). "
                f"Forced adjustment to LPI={suggested} to prevent flooding."
            )
            effective_lpi = suggested
        elif ratio > max_ratio:  # Very inefficient
            suggested = int(round(mesh / 4.5))
            suggested = max(lpi_min, min(lpi_max, suggested))
            logger.info(
                f"[JobConfig] Mesh/LPI ratio high (mesh={mesh}, lpi={effective_lpi}, ratio={ratio:.2f}). "
                f"Consider LPI={suggested} for better screen usage."
            )
            # Don't auto-fix high ratios - user may want coarse halftone
        else:
            # Acceptable range - prioritize DPI-based LPI for finer dots
            logger.info(f"[JobConfig] LPI {effective_lpi} accepted (mesh={mesh}, ratio={ratio:.2f}). DPI priority active.")

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
