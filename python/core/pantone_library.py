import json
import os
from typing import Dict, Tuple, List
import numpy as np


class PantoneColor:
    """Represents a single Pantone color with its RGB values and metadata"""

    def __init__(self, name: str, rgb: Tuple[int, int, int], hex_code: str = None):
        self.name = name
        self.rgb = rgb
        self.hex_code = hex_code or f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'rgb': self.rgb,
            'hex': self.hex_code
        }

    def distance_to(self, other_rgb: Tuple[int, int, int]) -> float:
        """Calculate Euclidean distance in RGB space"""
        return np.sqrt(sum((a - b) ** 2 for a, b in zip(self.rgb, other_rgb)))


class PantoneLibrary:
    """Pantone color library for spot color matching"""

    def __init__(self):
        self.colors: Dict[str, PantoneColor] = {}
        self._load_pantone_colors()

    def _load_pantone_colors(self):
        """Load common Pantone colors used in screen printing"""
        # Core Pantone colors for textile/screen printing
        pantone_data = {
            # Process Colors (CMYK equivalents)
            'PMS 185 C': (0, 51, 160),      # Reflex Blue
            'PMS 186 C': (0, 94, 184),      # Process Blue
            'PMS 281 C': (0, 136, 206),     # Classic Blue
            'PMS 292 C': (0, 169, 224),     # Sky Blue
            'PMS 551 C': (0, 91, 150),      # Navy Blue
            'PMS 7454 C': (143, 211, 255),  # Light Blue

            # Reds and Warm Colors
            'PMS 185 C': (237, 28, 36),     # Red 032
            'PMS 186 C': (211, 33, 45),     # Fire Engine Red
            'PMS 200 C': (228, 0, 43),      # Bright Red
            'PMS 201 C': (255, 69, 0),      # Orange
            'PMS 165 C': (255, 102, 0),     # Bright Orange
            'PMS 021 C': (255, 153, 0),     # Golden Yellow

            # Yellows and Greens
            'PMS 123 C': (255, 209, 0),     # Process Yellow
            'PMS 398 C': (181, 211, 52),    # Lime Green
            'PMS 348 C': (0, 166, 81),      # Kelly Green
            'PMS 349 C': (0, 128, 55),      # Dark Green
            'PMS 555 C': (0, 106, 68),      # Forest Green

            # Purples and Pinks
            'PMS 259 C': (140, 30, 110),    # Purple
            'PMS 260 C': (102, 45, 145),    # Violet
            'PMS 261 C': (67, 60, 139),     # Dark Purple
            'PMS 242 C': (226, 0, 122),     # Hot Pink
            'PMS 238 C': (255, 102, 153),   # Pink

            # Neutrals and Special Colors
            'PMS Black C': (0, 0, 0),       # Black
            'PMS White': (255, 255, 255),   # White
            'PMS 877 C': (128, 128, 128),   # Gray
            'PMS 430 C': (112, 72, 42),     # Brown
            'PMS 465 C': (166, 125, 80),    # Tan
            'PMS 7494 C': (184, 178, 153),  # Warm Gray

            # Metallic Colors (simulated)
            'PMS 871 C': (143, 141, 141),   # Silver
            'PMS 876 C': (165, 165, 165),   # Light Silver
            'PMS 872 C': (96, 96, 96),      # Dark Silver
            'PMS 874 C': (197, 179, 88),    # Gold
            'PMS 875 C': (158, 145, 47),    # Dark Gold
        }

        for name, rgb in pantone_data.items():
            self.colors[name] = PantoneColor(name, rgb)

    def find_nearest_pantone(self, rgb: Tuple[int, int, int]) -> PantoneColor:
        """
        Find the nearest Pantone color to the given RGB value

        Args:
            rgb: RGB tuple (R, G, B)

        Returns:
            Nearest PantoneColor object
        """
        if not self.colors:
            # Return a default color if library is empty
            return PantoneColor("Unknown", rgb)

        min_distance = float('inf')
        nearest_color = None

        for color in self.colors.values():
            distance = color.distance_to(rgb)
            if distance < min_distance:
                min_distance = distance
                nearest_color = color

        return nearest_color

    def find_nearest_pantone(self, rgb: Tuple[int, int, int]) -> PantoneColor:
        """Find the nearest Pantone color to the given RGB value"""
        nearest_color = None
        min_distance = float('inf')

        for color in self.colors.values():
            distance = color.distance_to(rgb)
            if distance < min_distance:
                min_distance = distance
                nearest_color = color

        return nearest_color

    def find_nearest_colors(self, rgb: Tuple[int, int, int], count: int = 5) -> List[PantoneColor]:
        """Find the N nearest Pantone colors"""
        colors_with_distances = [
            (color, color.distance_to(rgb)) for color in self.colors.values()
        ]
        colors_with_distances.sort(key=lambda x: x[1])
        return [color for color, _ in colors_with_distances[:count]]

    def get_color_by_name(self, name: str) -> PantoneColor:
        """Get a Pantone color by name"""
        return self.colors.get(name)

    def get_all_colors(self) -> Dict[str, PantoneColor]:
        """Get all Pantone colors"""
        return self.colors.copy()

    def save_to_json(self, filepath: str):
        """Save the color library to JSON file"""
        data = {name: color.to_dict() for name, color in self.colors.items()}
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @classmethod
    def load_from_json(cls, filepath: str) -> 'PantoneLibrary':
        """Load color library from JSON file"""
        library = cls()
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                library.colors = {}
                for name, color_data in data.items():
                    rgb = tuple(color_data['rgb'])
                    library.colors[name] = PantoneColor(name, rgb, color_data.get('hex'))
        return library
