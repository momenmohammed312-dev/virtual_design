"""
physical_print_model.py — Physical constraints and calibrated scaling logic.
Ensures that virtual pixels map correctly to physical film dimensions.
"""

import logging
from dataclasses import dataclass
from typing import Tuple

logger = logging.getLogger(__name__)

@dataclass
class PrintArea:
    width_mm: float
    height_mm: float
    dpi: int

class PhysicalPrintModel:
    """
    Validates and calculates physical constraints for screen printing.
    """
    # Industry standard mesh-to-LPI ceilings
    # Formula: mesh_count / 2.5 (safe) to mesh_count / 2.0 (aggressive)
    MESH_TO_LPI_RATIO = 2.5 

    def __init__(self, mesh_count: int = 280):
        self.mesh_count = mesh_count

    def get_max_safe_lpi(self) -> int:
        """Calculate maximum LPI to prevent dot gain/ink flooding on current mesh."""
        return int(self.mesh_count / self.MESH_TO_LPI_RATIO)

    def calculate_px_to_mm(self, dpi: int) -> float:
        """Returns pixels per millimeter at given DPI."""
        return dpi / 25.4

    def validate_lpi_vs_dpi(self, lpi: int, dpi: int) -> Tuple[int, str]:
        """
        Ensures LPI is safe for the selected DPI.
        Rule: DPI should be at least 10x LPI for high quality, 6x for minimum.
        """
        max_safe_lpi = self.get_max_safe_lpi()
        reason = ""
        
        if lpi > max_safe_lpi:
            reason = f"LPI {lpi} clamped to {max_safe_lpi} (Mesh constraint)"
            lpi = max_safe_lpi
            
        # Raster resolution check
        # Each halftone dot needs enough 'sub-pixels' to be shaped correctly
        if dpi / lpi < 8:
            potential_lpi = int(dpi / 8)
            if potential_lpi < lpi:
                reason += f" | LPI reduced to {potential_lpi} to maintain dot shape at {dpi} DPI"
                lpi = max(35, potential_lpi)
                
        return lpi, reason

    def get_page_size_mm(self, name: str) -> Tuple[float, float]:
        """Standard page sizes in mm."""
        sizes = {
            "A4": (210.0, 297.0),
            "A3": (297.0, 420.0),
            "Letter": (215.9, 279.4),
        }
        return sizes.get(name, (210.0, 297.0))
