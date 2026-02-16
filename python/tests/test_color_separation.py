"""
Tests for color separation module
"""

import numpy as np
import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.binarizer import Binarizer
from core.stroke_validator import StrokeValidator
from core.halftone_generator import HalftoneGenerator
from utils.validators import Validators


class TestValidators:
    """Test input validators"""
    
    def test_validate_color_count_valid(self):
        valid, msg = Validators.validate_color_count(4)
        assert valid is True
        assert msg is None
    
    def test_validate_color_count_too_low(self):
        valid, msg = Validators.validate_color_count(0)
        assert valid is False
        assert msg is not None
    
    def test_validate_color_count_too_high(self):
        valid, msg = Validators.validate_color_count(20)
        assert valid is False
        assert msg is not None
    
    def test_validate_dpi_valid(self):
        valid, msg = Validators.validate_dpi(300)
        assert valid is True
        assert msg is None
    
    def test_validate_dpi_too_low(self):
        valid, msg = Validators.validate_dpi(50)
        assert valid is False
    
    def test_validate_dpi_warning(self):
        valid, msg = Validators.validate_dpi(150)
        assert valid is True
        assert msg is not None  # Warning message
    
    def test_validate_stroke_width_valid(self):
        valid, msg = Validators.validate_stroke_width(0.5)
        assert valid is True
        assert msg is None
    
    def test_validate_stroke_width_too_small(self):
        valid, msg = Validators.validate_stroke_width(0.05)
        assert valid is False
    
    def test_validate_lpi_valid(self):
        valid, msg = Validators.validate_lpi(55)
        assert valid is True
        assert msg is None
    
    def test_validate_lpi_too_low(self):
        valid, msg = Validators.validate_lpi(10)
        assert valid is False


class TestBinarizer:
    """Test binarizer"""
    
    def test_binarize_simple(self):
        binarizer = Binarizer()
        # Create test grayscale image
        img = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = binarizer.binarize(img, method='simple')
        assert result.shape == img.shape
        assert set(np.unique(result)).issubset({0, 255})
    
    def test_binarize_otsu(self):
        binarizer = Binarizer()
        img = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = binarizer.binarize(img, method='otsu')
        assert result.shape == img.shape
        assert set(np.unique(result)).issubset({0, 255})
    
    def test_auto_binarize(self):
        binarizer = Binarizer()
        img = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result, method, threshold = binarizer.auto_binarize(img)
        assert result.shape == img.shape
        assert method in ['otsu', 'adaptive_gaussian']
    
    def test_remove_noise(self):
        binarizer = Binarizer()
        img = np.zeros((100, 100), dtype=np.uint8)
        img[50, 50] = 255  # Single noise pixel
        result = binarizer.remove_noise(img)
        assert result.shape == img.shape


class TestStrokeValidator:
    """Test stroke validator"""
    
    def test_mm_to_pixels(self):
        validator = StrokeValidator(min_stroke_mm=0.5, dpi=300)
        pixels = validator._mm_to_pixels(25.4)  # 1 inch in mm
        assert pixels == 300
    
    def test_pixels_to_mm(self):
        validator = StrokeValidator(min_stroke_mm=0.5, dpi=300)
        mm = validator._pixels_to_mm(300)
        assert mm == 25.4
    
    def test_validate_empty_mask(self):
        validator = StrokeValidator()
        mask = np.zeros((100, 100), dtype=np.uint8)
        result = validator.validate_mask(mask)
        assert result['valid'] is False
        assert 'No objects found' in result['warnings'][0]


class TestHalftoneGenerator:
    """Test halftone generator"""
    
    def test_generate_round(self):
        gen = HalftoneGenerator(dpi=300)
        img = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = gen.generate(img, lpi=55, dot_shape='round')
        assert result.shape == img.shape
    
    def test_generate_square(self):
        gen = HalftoneGenerator(dpi=300)
        img = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = gen.generate(img, lpi=55, dot_shape='square')
        assert result.shape == img.shape


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
