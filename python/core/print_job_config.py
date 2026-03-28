"""
print_job_config.py — Screen Print Parameters & Mesh Constraints
Virtual Design Silk Screen Studio
"""

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

    def validate_lpi(self, requested_lpi: int) -> int:
        """Clamps the requested LPI to a safe value based on current mesh count."""
        # Find nearest standard mesh in table (if custom mesh used)
        available_meshes = sorted(self.MESH_LPI_TABLE.keys())
        nearest_mesh = min(available_meshes, key=lambda x: abs(x - self.mesh_count))
        
        limit = self.MESH_LPI_TABLE.get(nearest_mesh, 45)
        
        if requested_lpi > limit:
            logger.warning(f"[JobConfig] LPI {requested_lpi} exceeds safe limit for {self.mesh_count} mesh. Clamping to {limit}.")
            return limit
        return requested_lpi

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
