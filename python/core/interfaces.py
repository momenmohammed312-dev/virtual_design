"""
interfaces.py — Phase 8: Clean Architecture Interfaces
Domain interfaces that decouple the pipeline layers.

Layer structure:
    domain/      -> Pure data types + interface definitions
    application/ -> Pipeline orchestration
    infrastructure/ -> Concrete implementations (cv2, reportlab, etc.)

Consumers should depend on THESE interfaces, not concrete classes.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
import numpy as np
from typing import List, Tuple, Dict, Optional, Any
from dataclasses import dataclass


# ═══════════════════════════════════════════════════════════════════════════════
# DOMAIN DATA TYPES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ImageIntent:
    """Classification result: what kind of image is this?"""
    type: str               # 'logo' | 'photo' | 'mixed'
    confidence: float       # 0.0–1.0
    route: str              # 'vector' | 'halftone' | 'hybrid'
    metrics: Dict[str, float]


@dataclass
class ColorLayer:
    """One separated color with its corresponding binary mask."""
    index: int
    rgb: Tuple[int, int, int]
    hex_color: str
    mask: np.ndarray          # uint8 binary (255=ink, 0=paper)
    coverage_pct: float


PathCommand = Tuple   # ('M', x, y) | ('L', x, y) | ('C', ...) | ('Z',)


@dataclass
class VectorPath:
    """One closed vector path as a list of path commands."""
    commands: List[PathCommand]
    area: float               # Approximate enclosed area (px²)
    is_hole: bool = False


# ═══════════════════════════════════════════════════════════════════════════════
# I. CLASSIFIER INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

class IClassifier(ABC):
    """
    Classifies an image and returns an ImageIntent.
    Must NOT modify the image.
    """

    @abstractmethod
    def classify(self, image: np.ndarray) -> ImageIntent:
        ...


# ═══════════════════════════════════════════════════════════════════════════════
# II. PREPROCESSOR INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

class IPreprocessor(ABC):
    """
    Applies non-destructive preprocessing (smoothing, gamma, etc.).
    Must NOT binarize the image.
    """

    @abstractmethod
    def process(self, image: np.ndarray, intent: Optional[ImageIntent] = None) -> np.ndarray:
        ...


# ═══════════════════════════════════════════════════════════════════════════════
# III. COLOR SEPARATOR INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

class IColorSeparator(ABC):
    """Separates image into color layers."""

    @abstractmethod
    def separate(
        self,
        image: np.ndarray,
        num_colors: Optional[int] = None,
    ) -> List[ColorLayer]:
        ...


# ═══════════════════════════════════════════════════════════════════════════════
# IV. VECTORIZER INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

class IVectorizer(ABC):
    """
    Converts a grayscale/binary image into smooth vector paths.

    CRITICAL RULE: Vectorizers must receive the GRAYSCALE image, not a
    pre-binarized version.  Binarization (if needed) happens inside.
    """

    @abstractmethod
    def vectorize(self, image: np.ndarray) -> List[VectorPath]:
        ...


# ═══════════════════════════════════════════════════════════════════════════════
# V. HALFTONE ENGINE INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

class IHalftoneEngine(ABC):
    """
    Generates a halftone representation from a grayscale channel.

    Both raster and vector halftone engines implement this interface.
    They accept the SAME grayscale input and LPI/angle config.
    """

    @abstractmethod
    def generate(
        self,
        grayscale: np.ndarray,
        lpi: int = 85,
        angle: float = 45.0,
    ) -> Any:
        """
        Returns:
            Raster engine  -> np.ndarray (uint8, 0/255 bitmap)
            Vector engine  -> List[VectorDot]
        """
        ...


# ═══════════════════════════════════════════════════════════════════════════════
# VI. EXPORTER INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

class IExporter(ABC):
    """Exports processed layers to a file (PDF, SVG, PNG, etc.)."""

    @abstractmethod
    def export(
        self,
        layers: List[ColorLayer],
        paths: Optional[List[List[VectorPath]]],
        output_path: str,
        **kwargs,
    ) -> str:
        ...


# ═══════════════════════════════════════════════════════════════════════════════
# VII. PIPELINE ORCHESTRATOR INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

class IPipeline(ABC):
    """
    Top-level pipeline that wires all stages together.
    Accepts an image and returns export path(s).
    """

    @abstractmethod
    def run(self, image: np.ndarray, output_dir: str, **kwargs) -> Dict[str, str]:
        """
        Returns dict of output paths:
            { 'pdf': '...', 'svg': '...', 'preview': '...' }
        """
        ...


# ═══════════════════════════════════════════════════════════════════════════════
# ADAPTER HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
# These thin adapters let us expose concrete classes through the interface layer
# without changing any existing code.

class ClassifierAdapter(IClassifier):
    """Wraps ImageClassifier (image_classifier.py) behind IClassifier."""

    def __init__(self):
        from core.image_classifier import ImageClassifier
        self._impl = ImageClassifier()

    def classify(self, image: np.ndarray) -> ImageIntent:
        result = self._impl.classify(image)
        return ImageIntent(
            type=result.type,
            confidence=result.confidence,
            route=result.route(),
            metrics=result.metrics,
        )


class PreprocessorAdapter(IPreprocessor):
    """Wraps AntiAliasPreserver behind IPreprocessor."""

    def process(self, image: np.ndarray, intent: Optional[ImageIntent] = None) -> np.ndarray:
        from core.anti_alias_preserve import preserve_anti_alias
        img_type = intent.type if intent else "mixed"
        return preserve_anti_alias(image, image_type=img_type)


class LABSeparatorAdapter(IColorSeparator):
    """Wraps LABColorSeparator behind IColorSeparator."""

    def separate(self, image: np.ndarray, num_colors: Optional[int] = None) -> List[ColorLayer]:
        from core.lab_separator import LABColorSeparator
        sep = LABColorSeparator()
        result = sep.separate(image, num_colors=num_colors)
        return [
            ColorLayer(
                index=c.index,
                rgb=c.rgb,
                hex_color=c.hex_color,
                mask=c.mask,
                coverage_pct=c.coverage_pct,
            )
            for c in result.clusters
        ]


class VectorizerAdapter(IVectorizer):
    """Wraps CurveFitter behind IVectorizer."""

    def vectorize(self, image: np.ndarray) -> List[VectorPath]:
        from core.curve_fitter import CurveFitter, CurveFitConfig
        fitter = CurveFitter(CurveFitConfig(use_canny=True))
        raw_paths = fitter.extract_paths(image)
        return [
            VectorPath(commands=cmds, area=self._path_area(cmds))
            for cmds in raw_paths
        ]

    @staticmethod
    def _path_area(commands) -> float:
        # Rough shoelace area estimate from M/L coordinates
        pts = [(cmd[1], cmd[2]) for cmd in commands if cmd[0] in ('M', 'L')]
        if len(pts) < 3:
            return 0.0
        n = len(pts)
        area = abs(sum(
            pts[i][0] * pts[(i+1) % n][1] - pts[(i+1) % n][0] * pts[i][1]
            for i in range(n)
        )) / 2.0
        return area


class RasterHalftoneAdapter(IHalftoneEngine):
    """Wraps RasterHalftoneEngine behind IHalftoneEngine."""

    def generate(self, grayscale: np.ndarray, lpi: int = 85, angle: float = 45.0) -> np.ndarray:
        from core.raster_halftone import RasterHalftoneConfig, RasterHalftoneEngine
        cfg = RasterHalftoneConfig(lpi=lpi, angle=angle)
        return RasterHalftoneEngine(cfg).generate(grayscale)


class VectorHalftoneAdapter(IHalftoneEngine):
    """Wraps VectorHalftoneEngine behind IHalftoneEngine."""

    def __init__(self, input_dpi: int = 300):
        self._dpi = input_dpi

    def generate(self, grayscale: np.ndarray, lpi: int = 85, angle: float = 45.0):
        from core.vector_halftone import VectorHalftoneConfig, VectorHalftoneEngine
        cfg = VectorHalftoneConfig(lpi=lpi, input_dpi=self._dpi, angle=angle)
        return VectorHalftoneEngine(cfg).generate(grayscale)
