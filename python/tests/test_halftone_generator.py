import sys
from pathlib import Path
import numpy as np

# Ensure core modules are importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.halftone_generator import HalftoneGenerator


def test_generate_vector_dots_basic():
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    gen = HalftoneGenerator(dpi=300)
    dots = gen.generate_vector_dots(image, lpi=20, angle=45.0, dot_shape="circle")
    assert isinstance(dots, list)
    assert len(dots) > 0
    for d in dots[:5]:
        assert isinstance(d.cx, float) and isinstance(d.cy, float)
        assert isinstance(d.radius, float)
        assert d.shape in ("circle", "square")
        assert 0 <= d.cx <= 100
        assert 0 <= d.cy <= 100


def test_generate_raster_output_shape():
    image = np.zeros((80, 120, 3), dtype=np.uint8)
    gen = HalftoneGenerator(dpi=300)
    raster = gen.generate(image, lpi=20, angle=0.0, dot_shape="circle")
    assert isinstance(raster, np.ndarray)
    assert raster.shape == (80, 120)
    assert raster.dtype == np.uint8
